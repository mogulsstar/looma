"""Configuration commands for Looma CLI."""

import sys
from pathlib import Path
from typing import Optional

import click
import structlog

logger = structlog.get_logger()


@click.group()
def config():
    """Manage Looma configuration."""
    pass


@config.command()
@click.argument("key", required=False)
@click.pass_context
def get(ctx, key: Optional[str]):
    """Get configuration value."""
    from looma.core.config import ConfigManager
    
    config_path = ctx.obj.get("config_path")
    
    if not config_path.exists():
        click.echo(f"Configuration file not found: {config_path}", err=True)
        sys.exit(1)
    
    try:
        # Load configuration
        config_manager = ConfigManager(config_path)
        config_data = config_manager.load()
        
        if key:
            # Get specific value
            value = config_manager.get(key, config_data=config_data)
            
            if value is None:
                click.echo(f"Key not found: {key}", err=True)
                sys.exit(1)
            
            # Format output
            if isinstance(value, (dict, list)):
                import json
                click.echo(json.dumps(value, indent=2))
            else:
                click.echo(value)
        else:
            # Show entire configuration
            import yaml
            click.echo(yaml.dump(config_data, default_flow_style=False))
            
    except Exception as e:
        click.echo(f"Failed to get configuration: {e}", err=True)
        sys.exit(1)


@config.command()
@click.argument("key")
@click.argument("value")
@click.pass_context
def set(ctx, key: str, value: str):
    """Set configuration value."""
    from looma.core.config import ConfigManager
    
    config_path = ctx.obj.get("config_path")
    
    try:
        # Load or create configuration
        config_manager = ConfigManager(config_path)
        
        if config_path.exists():
            config_data = config_manager.load()
        else:
            config_data = {}
        
        # Parse value
        import json
        try:
            # Try to parse as JSON
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            # Use as string
            parsed_value = value
        
        # Set value
        keys = key.split(".")
        current = config_data
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = parsed_value
        
        # Save configuration
        config_manager.save(config_data, config_path)
        
        click.echo(f"Configuration updated: {key} = {parsed_value}")
        
    except Exception as e:
        click.echo(f"Failed to set configuration: {e}", err=True)
        sys.exit(1)


@config.command()
@click.argument("key")
@click.pass_context
def delete(ctx, key: str):
    """Delete configuration value."""
    from looma.core.config import ConfigManager
    
    config_path = ctx.obj.get("config_path")
    
    if not config_path.exists():
        click.echo(f"Configuration file not found: {config_path}", err=True)
        sys.exit(1)
    
    try:
        # Load configuration
        config_manager = ConfigManager(config_path)
        config_data = config_manager.load()
        
        # Delete value
        keys = key.split(".")
        current = config_data
        
        for k in keys[:-1]:
            if k not in current:
                click.echo(f"Key not found: {key}", err=True)
                sys.exit(1)
            current = current[k]
        
        if keys[-1] not in current:
            click.echo(f"Key not found: {key}", err=True)
            sys.exit(1)
        
        del current[keys[-1]]
        
        # Save configuration
        config_manager.save(config_data, config_path)
        
        click.echo(f"Configuration deleted: {key}")
        
    except Exception as e:
        click.echo(f"Failed to delete configuration: {e}", err=True)
        sys.exit(1)


@config.command()
@click.pass_context
def validate(ctx):
    """Validate configuration."""
    from looma.core.config import ConfigManager
    
    config_path = ctx.obj.get("config_path")
    verbose = ctx.obj.get("verbose")
    
    if not config_path.exists():
        click.echo(f"Configuration file not found: {config_path}", err=True)
        sys.exit(1)
    
    try:
        # Load and validate configuration
        config_manager = ConfigManager(config_path)
        config_data = config_manager.load()
        
        # Validate
        is_valid = config_manager.validate(config_data)
        
        if is_valid:
            click.echo("Configuration is valid")
        else:
            click.echo("Configuration validation failed", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Configuration validation error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@config.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["yaml", "json", "toml"]),
    default="yaml",
    help="Output format",
)
@click.argument("output", type=click.Path())
@click.pass_context
def export(ctx, format: str, output: str):
    """Export configuration to file."""
    from looma.core.config import ConfigManager
    
    config_path = ctx.obj.get("config_path")
    
    if not config_path.exists():
        click.echo(f"Configuration file not found: {config_path}", err=True)
        sys.exit(1)
    
    try:
        # Load configuration
        config_manager = ConfigManager(config_path)
        config_data = config_manager.load()
        
        # Export to file
        output_path = Path(output)
        config_manager.save(config_data, output_path, format=format)
        
        click.echo(f"Configuration exported to: {output_path}")
        
    except Exception as e:
        click.echo(f"Failed to export configuration: {e}", err=True)
        sys.exit(1)


@config.command()
@click.argument("input", type=click.Path(exists=True))
@click.pass_context
def import_(ctx, input: str):
    """Import configuration from file."""
    from looma.core.config import ConfigManager
    
    config_path = ctx.obj.get("config_path")
    
    if config_path.exists():
        if not click.confirm(f"Configuration file {config_path} already exists. Overwrite?"):
            return
    
    try:
        # Load input configuration
        input_path = Path(input)
        input_manager = ConfigManager(input_path)
        config_data = input_manager.load()
        
        # Save to target path
        config_manager = ConfigManager(config_path)
        config_manager.save(config_data, config_path)
        
        click.echo(f"Configuration imported from: {input_path}")
        
    except Exception as e:
        click.echo(f"Failed to import configuration: {e}", err=True)
        sys.exit(1)


@config.command()
@click.pass_context
def wizard(ctx):
    """Launch configuration wizard."""
    try:
        import wx
        from looma.gui.wizard import ConfigWizard
        
        config_path = ctx.obj.get("config_path")
        
        # Create wxPython app
        app = wx.App()
        
        # Show wizard
        wizard = ConfigWizard(None, config_path)
        
        if wizard.RunWizard(wizard.GetFirstPage()):
            click.echo(f"Configuration saved to: {config_path}")
        else:
            click.echo("Configuration wizard cancelled")
        
        wizard.Destroy()
        app.MainLoop()
        
    except ImportError:
        click.echo("wxPython is not installed. Install with: pip install wxPython", err=True)
        click.echo("Alternatively, use 'looma init' for a basic configuration", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Failed to launch wizard: {e}", err=True)
        sys.exit(1)