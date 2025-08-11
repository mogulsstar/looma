"""Upload commands for Looma CLI."""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional

import click
import structlog

logger = structlog.get_logger()


@click.command()
@click.argument("packages", nargs=-1, type=click.Path(exists=True))
@click.option(
    "--channel",
    "-c",
    type=click.Choice(["stable", "beta", "alpha", "nightly"]),
    help="Release channel",
)
@click.option(
    "--version",
    "-v",
    help="Version number",
)
@click.option(
    "--notes",
    "-n",
    help="Release notes",
)
@click.option(
    "--draft",
    is_flag=True,
    help="Create as draft release",
)
@click.option(
    "--prerelease",
    is_flag=True,
    help="Mark as prerelease",
)
@click.pass_context
def upload(
    ctx,
    packages: tuple,
    channel: Optional[str],
    version: Optional[str],
    notes: Optional[str],
    draft: bool,
    prerelease: bool,
):
    """Upload packages to update source."""
    from looma.core.config import ConfigManager
    
    config_path = ctx.obj.get("config_path")
    quiet = ctx.obj.get("quiet")
    
    if not config_path.exists():
        click.echo(f"Configuration file not found: {config_path}", err=True)
        sys.exit(1)
    
    if not packages:
        # Find packages in dist directory
        dist_dir = Path("dist")
        if dist_dir.exists():
            packages = list(dist_dir.glob("*.exe")) + \
                      list(dist_dir.glob("*.dmg")) + \
                      list(dist_dir.glob("*.AppImage")) + \
                      list(dist_dir.glob("*.zip")) + \
                      list(dist_dir.glob("*.tar.gz"))
            
            if not packages:
                click.echo("No packages found to upload", err=True)
                sys.exit(1)
        else:
            click.echo("No packages specified and dist directory not found", err=True)
            sys.exit(1)
    
    try:
        # Load configuration
        config_manager = ConfigManager(config_path)
        config = config_manager.load()
        
        # Convert package paths
        package_paths = [Path(p) for p in packages]
        
        # Upload packages
        upload_packages(
            config,
            package_paths,
            channel=channel,
            version=version,
            notes=notes,
            draft=draft,
            prerelease=prerelease,
            quiet=quiet,
        )
        
        if not quiet:
            click.echo("Upload completed successfully")
            
    except Exception as e:
        click.echo(f"Upload failed: {e}", err=True)
        sys.exit(1)


def upload_packages(
    config: Dict,
    packages: List[Path],
    channel: Optional[str] = None,
    version: Optional[str] = None,
    notes: Optional[str] = None,
    draft: bool = False,
    prerelease: bool = False,
    quiet: bool = False,
):
    """
    Upload packages to configured update source.
    
    Parameters
    ----------
    config : dict
        Configuration dictionary
    packages : List[Path]
        Package files to upload
    channel : Optional[str]
        Release channel
    version : Optional[str]
        Version number
    notes : Optional[str]
        Release notes
    draft : bool
        Create as draft
    prerelease : bool
        Mark as prerelease
    quiet : bool
        Suppress output
    """
    # Get update source configuration
    source_config = config.get("update", {}).get("source", {})
    source_type = source_config.get("type")
    
    if not source_type:
        raise ValueError("No update source configured")
    
    # Override channel if provided
    if not channel:
        channel = config.get("update", {}).get("channel", "stable")
    
    # Get version if not provided
    if not version:
        version = config.get("app", {}).get("version")
        if not version:
            raise ValueError("Version not specified")
    
    # Create appropriate uploader
    if source_type == "github":
        uploader = GitHubUploader(source_config, quiet)
    elif source_type == "gitlab":
        uploader = GitLabUploader(source_config, quiet)
    elif source_type == "s3":
        uploader = S3Uploader(source_config, quiet)
    elif source_type == "artifactory":
        uploader = ArtifactoryUploader(source_config, quiet)
    elif source_type == "http":
        uploader = HTTPUploader(source_config, quiet)
    else:
        raise ValueError(f"Unsupported source type: {source_type}")
    
    # Upload packages
    uploader.upload(
        packages,
        version=version,
        channel=channel,
        notes=notes,
        draft=draft,
        prerelease=prerelease,
    )


class BaseUploader:
    """Base class for package uploaders."""
    
    def __init__(self, config: Dict, quiet: bool = False):
        """
        Initialize uploader.
        
        Parameters
        ----------
        config : dict
            Source configuration
        quiet : bool
            Suppress output
        """
        self.config = config
        self.quiet = quiet
    
    def upload(
        self,
        packages: List[Path],
        version: str,
        channel: str,
        notes: Optional[str] = None,
        draft: bool = False,
        prerelease: bool = False,
    ):
        """Upload packages."""
        raise NotImplementedError


class GitHubUploader(BaseUploader):
    """GitHub release uploader."""
    
    def upload(
        self,
        packages: List[Path],
        version: str,
        channel: str,
        notes: Optional[str] = None,
        draft: bool = False,
        prerelease: bool = False,
    ):
        """Upload packages to GitHub release."""
        import httpx
        
        repo = self.config.get("repo")
        token = self.config.get("token")
        
        if not repo:
            raise ValueError("GitHub repository not configured")
        
        if not token:
            raise ValueError("GitHub token not configured")
        
        # Expand environment variables
        import os
        token = os.path.expandvars(token)
        
        # Create release
        api_url = f"https://api.github.com/repos/{repo}/releases"
        
        release_data = {
            "tag_name": f"v{version}",
            "name": f"Release {version}",
            "body": notes or f"Release {version}",
            "draft": draft,
            "prerelease": prerelease or channel != "stable",
        }
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        
        if not self.quiet:
            click.echo(f"Creating GitHub release {version}...")
        
        # Create release
        with httpx.Client() as client:
            response = client.post(api_url, json=release_data, headers=headers)
            
            if response.status_code == 422:
                # Release might already exist
                tag_url = f"{api_url}/tags/v{version}"
                response = client.get(tag_url, headers=headers)
            
            response.raise_for_status()
            release = response.json()
            upload_url = release["upload_url"].replace("{?name,label}", "")
        
        # Upload assets
        for package in packages:
            if not self.quiet:
                click.echo(f"  Uploading {package.name}...")
            
            with open(package, "rb") as f:
                file_data = f.read()
            
            asset_url = f"{upload_url}?name={package.name}"
            headers["Content-Type"] = "application/octet-stream"
            
            with httpx.Client() as client:
                response = client.post(
                    asset_url,
                    content=file_data,
                    headers=headers,
                )
                response.raise_for_status()
        
        if not self.quiet:
            click.echo(f"Release created: {release['html_url']}")


class GitLabUploader(BaseUploader):
    """GitLab release uploader."""
    
    def upload(
        self,
        packages: List[Path],
        version: str,
        channel: str,
        notes: Optional[str] = None,
        draft: bool = False,
        prerelease: bool = False,
    ):
        """Upload packages to GitLab release."""
        import httpx
        
        project_id = self.config.get("project_id")
        token = self.config.get("token")
        url = self.config.get("url", "https://gitlab.com")
        
        if not project_id:
            raise ValueError("GitLab project ID not configured")
        
        if not token:
            raise ValueError("GitLab token not configured")
        
        # Expand environment variables
        import os
        token = os.path.expandvars(token)
        
        # Upload packages first
        api_url = f"{url}/api/v4/projects/{project_id}"
        headers = {"PRIVATE-TOKEN": token}
        
        package_links = []
        
        for package in packages:
            if not self.quiet:
                click.echo(f"  Uploading {package.name}...")
            
            # Upload to project uploads
            with open(package, "rb") as f:
                files = {"file": (package.name, f)}
                
                with httpx.Client() as client:
                    response = client.post(
                        f"{api_url}/uploads",
                        files=files,
                        headers=headers,
                    )
                    response.raise_for_status()
                    upload_data = response.json()
            
            package_links.append({
                "name": package.name,
                "url": f"{url}/{upload_data['url']}",
            })
        
        # Create release
        if not self.quiet:
            click.echo(f"Creating GitLab release {version}...")
        
        release_data = {
            "tag_name": f"v{version}",
            "name": f"Release {version}",
            "description": notes or f"Release {version}",
            "assets": {"links": package_links},
        }
        
        with httpx.Client() as client:
            response = client.post(
                f"{api_url}/releases",
                json=release_data,
                headers=headers,
            )
            response.raise_for_status()
            release = response.json()
        
        if not self.quiet:
            click.echo(f"Release created: {release['_links']['self']}")


class S3Uploader(BaseUploader):
    """AWS S3 uploader."""
    
    def upload(
        self,
        packages: List[Path],
        version: str,
        channel: str,
        notes: Optional[str] = None,
        draft: bool = False,
        prerelease: bool = False,
    ):
        """Upload packages to S3."""
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 is required for S3 uploads. Install with: pip install boto3")
        
        bucket = self.config.get("bucket")
        region = self.config.get("region", "us-east-1")
        prefix = self.config.get("prefix", "")
        
        if not bucket:
            raise ValueError("S3 bucket not configured")
        
        # Create S3 client
        s3 = boto3.client("s3", region_name=region)
        
        # Upload packages
        for package in packages:
            key = f"{prefix}{channel}/{version}/{package.name}"
            
            if not self.quiet:
                click.echo(f"  Uploading {package.name} to s3://{bucket}/{key}...")
            
            with open(package, "rb") as f:
                s3.upload_fileobj(f, bucket, key)
        
        # Create manifest
        import json
        from datetime import datetime
        
        manifest = {
            "version": version,
            "channel": channel,
            "date": datetime.utcnow().isoformat(),
            "notes": notes,
            "files": [p.name for p in packages],
        }
        
        manifest_key = f"{prefix}{channel}/{version}/manifest.json"
        s3.put_object(
            Bucket=bucket,
            Key=manifest_key,
            Body=json.dumps(manifest, indent=2),
            ContentType="application/json",
        )
        
        if not self.quiet:
            click.echo(f"Upload completed to s3://{bucket}/{prefix}{channel}/{version}/")


class ArtifactoryUploader(BaseUploader):
    """JFrog Artifactory uploader."""
    
    def upload(
        self,
        packages: List[Path],
        version: str,
        channel: str,
        notes: Optional[str] = None,
        draft: bool = False,
        prerelease: bool = False,
    ):
        """Upload packages to Artifactory."""
        import httpx
        
        url = self.config.get("url")
        repository = self.config.get("repository")
        username = self.config.get("username")
        password = self.config.get("password")
        api_key = self.config.get("api_key")
        
        if not url:
            raise ValueError("Artifactory URL not configured")
        
        if not repository:
            raise ValueError("Artifactory repository not configured")
        
        # Prepare authentication
        auth = None
        headers = {}
        
        if api_key:
            headers["X-JFrog-Art-Api"] = api_key
        elif username and password:
            auth = (username, password)
        else:
            raise ValueError("Artifactory authentication not configured")
        
        # Upload packages
        for package in packages:
            upload_path = f"{channel}/{version}/{package.name}"
            upload_url = f"{url}/artifactory/{repository}/{upload_path}"
            
            if not self.quiet:
                click.echo(f"  Uploading {package.name} to {upload_url}...")
            
            with open(package, "rb") as f:
                with httpx.Client() as client:
                    response = client.put(
                        upload_url,
                        content=f,
                        headers=headers,
                        auth=auth,
                    )
                    response.raise_for_status()
        
        if not self.quiet:
            click.echo(f"Upload completed to {url}/artifactory/{repository}/{channel}/{version}/")


class HTTPUploader(BaseUploader):
    """Generic HTTP uploader."""
    
    def upload(
        self,
        packages: List[Path],
        version: str,
        channel: str,
        notes: Optional[str] = None,
        draft: bool = False,
        prerelease: bool = False,
    ):
        """Upload packages via HTTP."""
        import httpx
        
        base_url = self.config.get("base_url")
        upload_endpoint = self.config.get("upload_endpoint", "/upload")
        auth_token = self.config.get("auth_token")
        
        if not base_url:
            raise ValueError("HTTP base URL not configured")
        
        # Prepare headers
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        # Upload packages
        for package in packages:
            upload_url = f"{base_url}{upload_endpoint}"
            
            if not self.quiet:
                click.echo(f"  Uploading {package.name} to {upload_url}...")
            
            with open(package, "rb") as f:
                files = {"file": (package.name, f)}
                data = {
                    "version": version,
                    "channel": channel,
                    "notes": notes or "",
                }
                
                with httpx.Client() as client:
                    response = client.post(
                        upload_url,
                        files=files,
                        data=data,
                        headers=headers,
                    )
                    response.raise_for_status()
        
        if not self.quiet:
            click.echo(f"Upload completed to {base_url}")