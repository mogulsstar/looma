"""Main CLI entry point for Looma."""

import sys
from pathlib import Path
from typing import Optional

import click
import structlog

from looma.cli.build import build
from looma.cli.config import config
from looma.cli.keys import keys
from looma.cli.package import package
from looma.cli.upload import upload
from looma.cli.verify import verify
from looma.core.constants import DEFAULT_CONFIG_FILE, VERSION

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@click.group()
@click.version_option(version=VERSION, prog_name="looma")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=False),
    default=DEFAULT_CONFIG_FILE,
    help="Configuration file path",
    envvar="LOOMA_CONFIG",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
    envvar="LOOMA_VERBOSE",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress non-error output",
    envvar="LOOMA_QUIET",
)
@click.pass_context
def cli(ctx, config: str, verbose: bool, quiet: bool):
    """
    Looma - Python packaging and auto-update platform.
    
    Looma provides a comprehensive solution for packaging Python applications
    and enabling automatic updates. It supports multiple packaging engines
    and update sources.
    """
    # Store context
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = Path(config)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    
    # Configure logging level
    if quiet:
        structlog.configure(
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    elif verbose:
        import logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stderr,
            level=logging.DEBUG,
        )


# Add subcommands
cli.add_command(build)
cli.add_command(config)
cli.add_command(keys)
cli.add_command(package)
cli.add_command(upload)
cli.add_command(verify)


@cli.command()
@click.pass_context
def gui(ctx):
    """Launch the GUI configuration tool."""
    try:
        import wx
        from looma.gui.app import LoomaApp
        
        config_path = ctx.obj.get("config_path")
        
        # Check if configuration exists
        wizard_mode = not config_path.exists()
        
        # Create and run app
        app = LoomaApp(config_path, wizard_mode)
        app.MainLoop()
        
    except ImportError:
        click.echo("wxPython is not installed. Install with: pip install wxPython", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Failed to launch GUI: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["yaml", "json", "toml"]),
    default="yaml",
    help="Output format",
)
@click.pass_context
def init(ctx, format: str):
    """Initialize a new Looma configuration."""
    from looma.core.config import ConfigManager
    
    config_path = ctx.obj.get("config_path")
    
    if config_path.exists():
        if not click.confirm(f"Configuration file {config_path} already exists. Overwrite?"):
            return
    
    # Create default configuration
    default_config = {
        "version": "1.0",
        "app": {
            "name": "MyApp",
            "version": "1.0.0",
            "description": "My application",
            "author": "Your Name",
            "email": "you@example.com",
            "license": "MIT",
        },
        "packaging": {
            "engine": "pyinstaller",
            "entry_point": "main.py",
            "one_file": True,
            "console": False,
        },
        "update": {
            "enabled": True,
            "channel": "stable",
            "strategy": "prompt",
            "check_interval": 86400,  # 24 hours
            "source": {
                "type": "github",
                "repo": "owner/repository",
            },
        },
        "security": {
            "signing": {
                "enabled": False,
            },
            "verification": {
                "strict": True,
            },
            "ssl": {
                "verify": True,
            },
        },
    }
    
    try:
        # Save configuration
        config_manager = ConfigManager(config_path)
        config_manager.save(default_config, config_path, format=format)
        
        click.echo(f"Configuration initialized: {config_path}")
        click.echo("\nNext steps:")
        click.echo("1. Edit the configuration file to match your application")
        click.echo("2. Run 'looma build' to package your application")
        click.echo("3. Run 'looma upload' to publish the package")
        
    except Exception as e:
        click.echo(f"Failed to initialize configuration: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("version", required=False)
@click.pass_context
def check_update(ctx, version: Optional[str]):
    """Check for available updates."""
    import asyncio
    from looma.client.updater import UpdateClient
    from looma.core.config import ConfigManager
    
    config_path = ctx.obj.get("config_path")
    
    if not config_path.exists():
        click.echo(f"Configuration file not found: {config_path}", err=True)
        sys.exit(1)
    
    try:
        # Load configuration
        config_manager = ConfigManager(config_path)
        config = config_manager.load()
        
        # Create update client
        client = UpdateClient(config)
        
        # Check for updates
        async def check():
            current_version = version or config.get("app", {}).get("version", "1.0.0")
            update_info = await client.check_update(current_version)
            
            if update_info:
                click.echo(f"Update available: {update_info.version}")
                click.echo(f"Release date: {update_info.release_date}")
                click.echo(f"Download URL: {update_info.download_url}")
                
                if update_info.release_notes:
                    click.echo(f"\nRelease notes:\n{update_info.release_notes}")
            else:
                click.echo("No updates available")
        
        # Run async check
        asyncio.run(check())
        
    except Exception as e:
        click.echo(f"Failed to check for updates: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Automatically confirm update",
)
@click.pass_context
def update(ctx, yes: bool):
    """Download and install available updates."""
    import asyncio
    from looma.client.updater import UpdateClient
    from looma.core.config import ConfigManager
    
    config_path = ctx.obj.get("config_path")
    
    if not config_path.exists():
        click.echo(f"Configuration file not found: {config_path}", err=True)
        sys.exit(1)
    
    try:
        # Load configuration
        config_manager = ConfigManager(config_path)
        config = config_manager.load()
        
        # Create update client
        client = UpdateClient(config)
        
        # Perform update
        async def do_update():
            # Check for updates
            current_version = config.get("app", {}).get("version", "1.0.0")
            update_info = await client.check_update(current_version)
            
            if not update_info:
                click.echo("No updates available")
                return
            
            click.echo(f"Update available: {update_info.version}")
            
            if not yes and not click.confirm("Download and install update?"):
                return
            
            # Download update
            click.echo("Downloading update...")
            success = await client.download_update(update_info)
            
            if success:
                click.echo("Update downloaded successfully")
                
                # Apply update
                if click.confirm("Apply update now? (Application will restart)"):
                    await client.apply_update(update_info)
            else:
                click.echo("Failed to download update", err=True)
        
        # Run async update
        asyncio.run(do_update())
        
    except Exception as e:
        click.echo(f"Failed to update: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()