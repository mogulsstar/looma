"""Build command for Looma CLI."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
import structlog

logger = structlog.get_logger()


@click.command()
@click.option(
    "--engine",
    "-e",
    type=click.Choice(["pyinstaller", "nuitka", "cxfreeze"]),
    help="Packaging engine to use",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="dist",
    help="Output directory",
)
@click.option(
    "--entry-point",
    type=click.Path(exists=True),
    help="Entry point script",
)
@click.option(
    "--one-file",
    is_flag=True,
    default=None,
    help="Create single file executable",
)
@click.option(
    "--console/--no-console",
    default=None,
    help="Show console window",
)
@click.option(
    "--icon",
    type=click.Path(exists=True),
    help="Application icon",
)
@click.option(
    "--clean",
    is_flag=True,
    default=True,
    help="Clean before build",
)
@click.option(
    "--sign",
    is_flag=True,
    help="Sign the package",
)
@click.option(
    "--upload",
    is_flag=True,
    help="Upload after build",
)
@click.pass_context
def build(
    ctx,
    engine: Optional[str],
    output: str,
    entry_point: Optional[str],
    one_file: Optional[bool],
    console: Optional[bool],
    icon: Optional[str],
    clean: bool,
    sign: bool,
    upload: bool,
):
    """Build application package."""
    from looma.core.config import ConfigManager
    from looma.packager import PackagerFactory
    
    config_path = ctx.obj.get("config_path")
    verbose = ctx.obj.get("verbose")
    quiet = ctx.obj.get("quiet")
    
    if not config_path.exists():
        click.echo(f"Configuration file not found: {config_path}", err=True)
        sys.exit(1)
    
    try:
        # Load configuration
        config_manager = ConfigManager(config_path)
        config = config_manager.load()
        
        # Override configuration with command-line options
        packaging_config = config.get("packaging", {})
        
        if engine:
            packaging_config["engine"] = engine
        if entry_point:
            packaging_config["entry_point"] = entry_point
        if one_file is not None:
            packaging_config["one_file"] = one_file
        if console is not None:
            packaging_config["console"] = console
        if icon:
            packaging_config["icon"] = icon
        
        # Get engine
        engine_name = packaging_config.get("engine", "pyinstaller")
        
        if not quiet:
            click.echo(f"Building with {engine_name}...")
        
        # Create packager
        packager = PackagerFactory.create(engine_name, config)
        
        # Clean output directory
        output_dir = Path(output)
        if clean and output_dir.exists():
            if not quiet:
                click.echo(f"Cleaning {output_dir}...")
            
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
        
        # Build package
        async def run_build():
            return await packager.build(output_dir)
        
        # Run build
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success = loop.run_until_complete(run_build())
            
            if not success:
                click.echo("Build failed", err=True)
                sys.exit(1)
            
            if not quiet:
                click.echo(f"Build completed: {output_dir}")
            
            # Sign package if requested
            if sign or config.get("security", {}).get("signing", {}).get("enabled"):
                if not quiet:
                    click.echo("Signing package...")
                
                from looma.security.signing import Signer
                
                signer = Signer(config)
                
                # Find built packages
                packages = list(output_dir.glob("*.exe")) + \
                           list(output_dir.glob("*.dmg")) + \
                           list(output_dir.glob("*.AppImage")) + \
                           list(output_dir.glob("*.zip")) + \
                           list(output_dir.glob("*.tar.gz"))
                
                for package in packages:
                    try:
                        signature = signer.sign_package(package)
                        sig_path = package.with_suffix(package.suffix + ".sig")
                        sig_path.write_text(signature)
                        
                        if not quiet:
                            click.echo(f"  Signed: {package.name}")
                    except Exception as e:
                        click.echo(f"  Failed to sign {package.name}: {e}", err=True)
                        if config.get("security", {}).get("signing", {}).get("required"):
                            sys.exit(1)
            
            # Upload if requested
            if upload:
                if not quiet:
                    click.echo("Uploading package...")
                
                # Import upload module
                from looma.cli.upload import upload_packages
                
                try:
                    upload_packages(config, output_dir, quiet=quiet)
                    if not quiet:
                        click.echo("Upload completed")
                except Exception as e:
                    click.echo(f"Upload failed: {e}", err=True)
                    sys.exit(1)
            
        finally:
            loop.close()
        
    except Exception as e:
        click.echo(f"Build failed: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)