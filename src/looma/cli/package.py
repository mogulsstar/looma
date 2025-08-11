"""Package management commands for Looma CLI."""

import sys
from pathlib import Path
from typing import Optional

import click
import structlog

logger = structlog.get_logger()


@click.group()
def package():
    """Manage application packages."""
    pass


@package.command()
@click.argument("package_file", type=click.Path(exists=True))
@click.pass_context
def info(ctx, package_file: str):
    """Show package information."""
    import json
    import zipfile
    import tarfile
    
    package_path = Path(package_file)
    
    try:
        # Determine package type
        if package_path.suffix == ".zip":
            with zipfile.ZipFile(package_path, "r") as zf:
                # Look for manifest
                if "looma.json" in zf.namelist():
                    manifest_data = zf.read("looma.json")
                    manifest = json.loads(manifest_data)
                else:
                    manifest = None
                
                # Get file list
                files = zf.namelist()
                total_size = sum(zf.getinfo(f).file_size for f in files)
                
        elif package_path.suffix in [".tar", ".gz", ".tgz"]:
            mode = "r:gz" if package_path.suffix in [".gz", ".tgz"] else "r"
            with tarfile.open(package_path, mode) as tf:
                # Look for manifest
                manifest = None
                try:
                    manifest_member = tf.getmember("looma.json")
                    manifest_data = tf.extractfile(manifest_member).read()
                    manifest = json.loads(manifest_data)
                except KeyError:
                    pass
                
                # Get file list
                files = [m.name for m in tf.getmembers()]
                total_size = sum(m.size for m in tf.getmembers())
        else:
            # Single file package
            manifest = None
            files = [package_path.name]
            total_size = package_path.stat().st_size
        
        # Display information
        click.echo(f"Package: {package_path}")
        click.echo(f"Size: {total_size:,} bytes")
        click.echo(f"Files: {len(files)}")
        
        if manifest:
            click.echo("\nManifest Information:")
            click.echo(f"  App: {manifest.get('app', {}).get('name', 'Unknown')}")
            click.echo(f"  Version: {manifest.get('app', {}).get('version', 'Unknown')}")
            click.echo(f"  Platform: {manifest.get('platform', 'Unknown')}")
            click.echo(f"  Architecture: {manifest.get('architecture', 'Unknown')}")
            click.echo(f"  Build Date: {manifest.get('build_date', 'Unknown')}")
            
            if "hash" in manifest:
                click.echo(f"  Hash: {manifest['hash'][:32]}...")
            if "signature" in manifest:
                click.echo(f"  Signed: Yes")
        
        # Show first few files
        if len(files) > 0:
            click.echo("\nContents (first 10 files):")
            for file in files[:10]:
                click.echo(f"  {file}")
            if len(files) > 10:
                click.echo(f"  ... and {len(files) - 10} more files")
        
    except Exception as e:
        click.echo(f"Failed to read package information: {e}", err=True)
        sys.exit(1)


@package.command()
@click.argument("package_file", type=click.Path(exists=True))
@click.argument("output_dir", type=click.Path())
@click.pass_context
def extract(ctx, package_file: str, output_dir: str):
    """Extract package contents."""
    import zipfile
    import tarfile
    
    package_path = Path(package_file)
    output_path = Path(output_dir)
    
    try:
        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Extract based on type
        if package_path.suffix == ".zip":
            with zipfile.ZipFile(package_path, "r") as zf:
                zf.extractall(output_path)
                extracted = len(zf.namelist())
                
        elif package_path.suffix in [".tar", ".gz", ".tgz"]:
            mode = "r:gz" if package_path.suffix in [".gz", ".tgz"] else "r"
            with tarfile.open(package_path, mode) as tf:
                tf.extractall(output_path)
                extracted = len(tf.getmembers())
        else:
            # Copy single file
            import shutil
            shutil.copy2(package_path, output_path / package_path.name)
            extracted = 1
        
        click.echo(f"Extracted {extracted} files to: {output_path}")
        
    except Exception as e:
        click.echo(f"Failed to extract package: {e}", err=True)
        sys.exit(1)


@package.command()
@click.argument("source_dir", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.option(
    "--format",
    "-f",
    type=click.Choice(["zip", "tar", "tar.gz"]),
    default="zip",
    help="Archive format",
)
@click.option(
    "--manifest",
    "-m",
    is_flag=True,
    help="Include manifest file",
)
@click.pass_context
def create(ctx, source_dir: str, output_file: str, format: str, manifest: bool):
    """Create package from directory."""
    import json
    import zipfile
    import tarfile
    import platform
    from datetime import datetime
    
    source_path = Path(source_dir)
    output_path = Path(output_file)
    
    # Add appropriate extension
    if not output_path.suffix:
        if format == "zip":
            output_path = output_path.with_suffix(".zip")
        elif format == "tar":
            output_path = output_path.with_suffix(".tar")
        elif format == "tar.gz":
            output_path = output_path.with_suffix(".tar.gz")
    
    try:
        # Create manifest if requested
        manifest_data = None
        if manifest:
            from looma.core.config import ConfigManager
            
            config_path = ctx.obj.get("config_path")
            config = {}
            
            if config_path.exists():
                config_manager = ConfigManager(config_path)
                config = config_manager.load()
            
            manifest_data = {
                "app": config.get("app", {}),
                "platform": platform.system().lower(),
                "architecture": platform.machine(),
                "build_date": datetime.utcnow().isoformat(),
                "format": format,
            }
        
        # Create archive
        files_added = 0
        
        if format == "zip":
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add manifest
                if manifest_data:
                    zf.writestr("looma.json", json.dumps(manifest_data, indent=2))
                
                # Add files
                for file_path in source_path.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(source_path)
                        zf.write(file_path, arcname)
                        files_added += 1
                        
        elif format in ["tar", "tar.gz"]:
            mode = "w:gz" if format == "tar.gz" else "w"
            with tarfile.open(output_path, mode) as tf:
                # Add manifest
                if manifest_data:
                    import io
                    manifest_bytes = json.dumps(manifest_data, indent=2).encode()
                    manifest_io = io.BytesIO(manifest_bytes)
                    manifest_info = tarfile.TarInfo("looma.json")
                    manifest_info.size = len(manifest_bytes)
                    tf.addfile(manifest_info, manifest_io)
                
                # Add files
                for file_path in source_path.rglob("*"):
                    if file_path.is_file():
                        arcname = str(file_path.relative_to(source_path))
                        tf.add(file_path, arcname)
                        files_added += 1
        
        click.echo(f"Package created: {output_path}")
        click.echo(f"Files added: {files_added}")
        
        if manifest:
            click.echo("Manifest included")
        
    except Exception as e:
        click.echo(f"Failed to create package: {e}", err=True)
        sys.exit(1)


@package.command()
@click.argument("package_file", type=click.Path(exists=True))
@click.pass_context
def hash(ctx, package_file: str):
    """Calculate package hash."""
    from looma.core.utils import calculate_hash
    
    package_path = Path(package_file)
    
    try:
        # Calculate hashes
        algorithms = ["sha256", "sha512", "md5"]
        
        for algo in algorithms:
            hash_value = calculate_hash(package_path, algo)
            click.echo(f"{algo.upper()}: {hash_value}")
        
        # File size
        size = package_path.stat().st_size
        click.echo(f"Size: {size:,} bytes")
        
    except Exception as e:
        click.echo(f"Failed to calculate hash: {e}", err=True)
        sys.exit(1)


@package.command()
@click.argument("old_package", type=click.Path(exists=True))
@click.argument("new_package", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.pass_context
def diff(ctx, old_package: str, new_package: str, output_file: str):
    """Create delta update package."""
    from looma.client.downloader import DeltaGenerator
    
    old_path = Path(old_package)
    new_path = Path(new_package)
    output_path = Path(output_file)
    
    try:
        # Create delta generator
        generator = DeltaGenerator()
        
        # Generate delta
        click.echo("Generating delta update...")
        delta_data = generator.generate_delta(old_path, new_path)
        
        # Save delta
        output_path.write_bytes(delta_data)
        
        # Calculate compression ratio
        old_size = old_path.stat().st_size
        new_size = new_path.stat().st_size
        delta_size = len(delta_data)
        ratio = 100 * (1 - delta_size / new_size)
        
        click.echo(f"Delta created: {output_path}")
        click.echo(f"Old package: {old_size:,} bytes")
        click.echo(f"New package: {new_size:,} bytes")
        click.echo(f"Delta size: {delta_size:,} bytes")
        click.echo(f"Compression: {ratio:.1f}%")
        
    except Exception as e:
        click.echo(f"Failed to create delta: {e}", err=True)
        sys.exit(1)