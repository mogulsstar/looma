"""AWS S3 source for Looma."""

import json
from pathlib import Path
from typing import Any, Dict, List

import structlog

from looma.core.exceptions import NetworkError
from looma.sources.base import BaseSource

logger = structlog.get_logger()


class S3Source(BaseSource):
    """
    AWS S3 source implementation.
    
    Uses S3 to store and fetch release files.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize S3 source.
        
        Parameters
        ----------
        config : dict
            Source configuration
        """
        super().__init__(config)
        self.bucket = config.get("bucket")
        self.region = config.get("region", "us-east-1")
        self.access_key = config.get("access_key")
        self.secret_key = config.get("secret_key")
        self.prefix = config.get("prefix", "looma")
        
        if not self.bucket:
            raise NetworkError("S3 bucket not configured")
        
        # Initialize S3 client (would use boto3 in real implementation)
        self._init_client()
    
    def _init_client(self) -> None:
        """Initialize S3 client."""
        try:
            import boto3
            
            if self.access_key and self.secret_key:
                self.s3_client = boto3.client(
                    "s3",
                    region_name=self.region,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                )
            else:
                # Use default credentials
                self.s3_client = boto3.client("s3", region_name=self.region)
        except ImportError:
            logger.warning("boto3 not installed, S3 source will not work")
            self.s3_client = None
    
    async def get_versions(self, channel: str) -> Dict[str, Any]:
        """
        Fetch available versions from S3.
        
        Parameters
        ----------
        channel : str
            Update channel
            
        Returns
        -------
        dict
            Version information
        """
        if not self.s3_client:
            raise NetworkError("S3 client not initialized")
        
        try:
            # Get versions.json from S3
            key = f"{self.prefix}/versions.json"
            
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read()
            data = json.loads(content)
            
            # Return channel-specific data
            channels = data.get("channels", {})
            return channels.get(channel, {}).get("versions", {})
            
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"versions.json not found in S3 bucket {self.bucket}")
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch versions from S3: {e}")
            raise NetworkError(f"Failed to fetch versions: {e}")
    
    async def upload_release(
        self,
        version: str,
        files: List[str],
        channel: str = "stable",
        notes: str = "",
    ) -> None:
        """
        Upload release to S3.
        
        Parameters
        ----------
        version : str
            Version string
        files : List[str]
            Files to upload
        channel : str
            Release channel
        notes : str
            Release notes
        """
        if not self.s3_client:
            raise NetworkError("S3 client not initialized")
        
        try:
            # Upload each file to S3
            for file_path in files:
                await self._upload_file(version, file_path, channel)
            
            # Update versions.json
            await self._update_versions_json(version, files, channel, notes)
            
            logger.info(f"Successfully uploaded release {version} to S3")
            
        except Exception as e:
            logger.error(f"Failed to upload release: {e}")
            raise NetworkError(f"Failed to upload release: {e}")
    
    async def _upload_file(self, version: str, file_path: str, channel: str) -> str:
        """
        Upload file to S3.
        
        Parameters
        ----------
        version : str
            Version string
        file_path : str
            Path to file
        channel : str
            Release channel
            
        Returns
        -------
        str
            S3 URL of uploaded file
        """
        file_path = Path(file_path)
        key = f"{self.prefix}/{channel}/{version}/{file_path.name}"
        
        # Upload file
        with open(file_path, "rb") as f:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=f,
                ContentType="application/octet-stream",
            )
        
        # Return public URL (if bucket is public)
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
    
    async def _update_versions_json(
        self,
        version: str,
        files: List[str],
        channel: str,
        notes: str,
    ) -> None:
        """
        Update versions.json in S3.
        
        Parameters
        ----------
        version : str
            Version string
        files : List[str]
            Uploaded files
        channel : str
            Release channel
        notes : str
            Release notes
        """
        # Download existing versions.json
        existing_data = {"channels": {}}
        
        try:
            key = f"{self.prefix}/versions.json"
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read()
            existing_data = json.loads(content)
        except self.s3_client.exceptions.NoSuchKey:
            pass
        except Exception as e:
            logger.warning(f"Failed to read existing versions.json: {e}")
        
        # Update with new version
        if channel not in existing_data["channels"]:
            existing_data["channels"][channel] = {"latest": version, "versions": {}}
        
        channel_data = existing_data["channels"][channel]
        channel_data["latest"] = version
        
        # Add version info
        version_info = {
            "notes": notes,
            "pub_date": self._get_timestamp(),
            "platforms": {},
        }
        
        # Add platform files
        for file_path in files:
            platform_info = self._parse_platform_from_filename(file_path)
            if platform_info:
                platform, arch = platform_info
                platform_key = f"{platform}-{arch}"
                
                version_info["platforms"][platform_key] = {
                    "url": f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{self.prefix}/{channel}/{version}/{Path(file_path).name}",
                    "size": Path(file_path).stat().st_size,
                    "hash": self._calculate_hash(file_path),
                    "signature": "",  # Would be calculated separately
                }
        
        channel_data["versions"][version] = version_info
        
        # Upload updated versions.json
        key = f"{self.prefix}/versions.json"
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(existing_data, indent=2),
            ContentType="application/json",
        )
    
    def _parse_platform_from_filename(self, filename: str) -> tuple:
        """
        Parse platform from filename.
        
        Parameters
        ----------
        filename : str
            File name
            
        Returns
        -------
        tuple
            (platform, architecture) or None
        """
        filename_lower = Path(filename).name.lower()
        
        if "win" in filename_lower:
            return ("windows", "win64" if "64" in filename_lower else "win32")
        elif "mac" in filename_lower or "darwin" in filename_lower:
            return ("macos", "arm64" if "arm" in filename_lower else "x64")
        elif "linux" in filename_lower:
            return ("linux", "arm64" if "arm" in filename_lower else "x64")
        
        return None
    
    def _calculate_hash(self, file_path: str) -> str:
        """
        Calculate file hash.
        
        Parameters
        ----------
        file_path : str
            Path to file
            
        Returns
        -------
        str
            SHA256 hash
        """
        import hashlib
        
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        return f"sha256:{hasher.hexdigest()}"
    
    def _get_timestamp(self) -> str:
        """
        Get current timestamp.
        
        Returns
        -------
        str
            ISO format timestamp
        """
        from datetime import datetime, timezone
        
        return datetime.now(timezone.utc).isoformat()