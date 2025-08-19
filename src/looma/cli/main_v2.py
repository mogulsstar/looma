"""
Enhanced Looma CLI with V2 features.

This module provides the main command-line interface for Looma V2,
including plugin support, multi-engine configuration, and enhanced commands.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import click
import structlog
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from looma.core.config import ConfigManager
from looma.core.constants import DEFAULT_CONFIG_FILE
from looma.plugins.manager import plugin_manager

# Initialize console for rich output
console = Console()
logger = structlog.get_logger()


class Context:
    """CLI context for passing data between commands."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = {}
        self.output_format = "text"
        self.verbose = False
        self.quiet = False


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.option(
    '--config', '-c',
    type=click.Path(exists=False),
    help='Configuration file path (supports pattern: looma-{env}.yml)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
@click.option(
    '--quiet', '-q',
    is_flag=True,
    help='Suppress non-error output'
)
@click.option(
    '--output-format', '-f',
    type=click.Choice(['text', 'json', 'yaml']),
    default='text',
    help='Output format'
)
@click.version_option()
@pass_context
def cli(ctx, config, verbose, quiet, output_format):
    """
    Looma V2 - Python Application Packaging and Auto-Update Platform
    
    A comprehensive solution for packaging Python applications with
    multiple engines and built-in auto-update capabilities.
    """
    ctx.verbose = verbose
    ctx.quiet = quiet
    ctx.output_format = output_format
    
    # Configure logging
    log_level = "DEBUG" if verbose else "INFO"
    if quiet:
        log_level = "ERROR"
    
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog, log_level)
        ),
    )
    
    # Load configuration if specified
    if config:
        config_path = Path(config)
        
        # Support environment-specific configs
        if not config_path.exists() and "{env}" in str(config):
            env = os.getenv("LOOMA_ENV", "dev")
            config_path = Path(str(config).replace("{env}", env))
        
        if config_path.exists():
            try:
                ctx.config = ctx.config_manager.load(config_path)
                if not quiet:
                    console.print(f"[green]✓[/green] Loaded configuration from {config_path}")
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to load configuration: {e}")
                sys.exit(1)


@cli.command()
@click.option(
    '--template', '-t',
    type=click.Choice(['basic', 'gui', 'cli', 'library', 'web']),
    default='basic',
    help='Configuration template to use'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    default=DEFAULT_CONFIG_FILE,
    help='Output configuration file path'
)
@click.option(
    '--wizard',
    is_flag=True,
    help='Start interactive configuration wizard'
)
@pass_context
def init(ctx, template, output, wizard):
    """Initialize a new Looma configuration file."""
    if wizard:
        # Launch interactive wizard
        _run_config_wizard(output)
    else:
        # Create from template
        _create_config_from_template(template, output)
        
        if not ctx.quiet:
            console.print(f"[green]✓[/green] Created configuration file: {output}")
            console.print("\nNext steps:")
            console.print("1. Edit the configuration file to match your project")
            console.print("2. Run [cyan]looma validate[/cyan] to check your configuration")
            console.print("3. Run [cyan]looma build[/cyan] to package your application")


@cli.command()
@click.option(
    '--schema',
    is_flag=True,
    help='Validate against JSON schema'
)
@pass_context
def validate(ctx, schema):
    """Validate the configuration file."""
    if not ctx.config:
        console.print("[red]✗[/red] No configuration loaded")
        sys.exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Validating configuration...", total=None)
        
        # Validate basic structure
        if ctx.config_manager.validate(ctx.config):
            progress.update(task, description="[green]✓[/green] Basic validation passed")
        else:
            progress.update(task, description="[red]✗[/red] Basic validation failed")
            sys.exit(1)
        
        # Validate engine configuration if schema flag is set
        if schema:
            engine = ctx.config.get("build", {}).get("engine")
            if engine:
                plugin_manager.initialize()
                schema = plugin_manager.get_plugin_schema(engine)
                if schema:
                    engine_options = ctx.config.get("build", {}).get("engine_options", {})
                    if plugin_manager.validate_plugin_config(engine, engine_options):
                        progress.update(task, description=f"[green]✓[/green] {engine} configuration valid")
                    else:
                        progress.update(task, description=f"[red]✗[/red] {engine} configuration invalid")
                        sys.exit(1)


@cli.command()
@click.option(
    '--engine', '-e',
    help='Override packaging engine'
)
@click.option(
    '--platform', '-p',
    multiple=True,
    type=click.Choice(['windows', 'macos', 'linux', 'all']),
    help='Target platforms (can specify multiple)'
)
@click.option(
    '--no-interactive',
    is_flag=True,
    help='Non-interactive mode for CI/CD'
)
@click.option(
    '--parallel',
    is_flag=True,
    help='Build for multiple platforms in parallel'
)
@click.option(
    '--clean',
    is_flag=True,
    help='Clean build artifacts before building'
)
@pass_context
def build(ctx, engine, platform, no_interactive, parallel, clean):
    """Build the application package."""
    if not ctx.config:
        console.print("[red]✗[/red] No configuration loaded")
        sys.exit(1)
    
    # Initialize plugin manager
    plugin_manager.initialize()
    
    # Determine engine
    build_engine = engine or ctx.config.get("build", {}).get("engine", "pyinstaller")
    
    # Check if engine is available
    if build_engine not in plugin_manager.get_engine_plugins():
        console.print(f"[red]✗[/red] Engine '{build_engine}' not available")
        console.print("\nAvailable engines:")
        for eng in plugin_manager.get_engine_plugins():
            console.print(f"  - {eng}")
        sys.exit(1)
    
    # Get engine plugin
    engine_plugin = plugin_manager.get_plugin(
        build_engine,
        ctx.config.get("build", {})
    )
    
    # Determine platforms
    if not platform or 'all' in platform:
        platforms = ['windows', 'macos', 'linux']
    else:
        platforms = list(platform)
    
    # Filter to current platform if not cross-compiling
    current_platform = _get_current_platform()
    if current_platform in platforms:
        platforms = [current_platform]
        if not ctx.quiet:
            console.print(f"[yellow]![/yellow] Building for current platform only: {current_platform}")
    
    # Build for each platform
    results = {}
    for plat in platforms:
        if not ctx.quiet:
            console.print(f"\n[cyan]Building for {plat}...[/cyan]")
        
        # Merge platform-specific options
        build_config = ctx.config.get("build", {}).copy()
        platform_config = ctx.config.get("platforms", {}).get(plat, {})
        if platform_config.get("engine_options"):
            build_config["engine_options"].update(platform_config["engine_options"])
        
        # Execute build
        try:
            result = engine_plugin.execute({
                "entry_point": build_config.get("entry_point", "main.py"),
                "output_dir": build_config.get("output_dir", "dist"),
                "options": build_config.get("engine_options", {}),
                "platform": plat,
            })
            
            results[plat] = result
            
            if not ctx.quiet:
                if result.get("success"):
                    console.print(f"[green]✓[/green] Build successful for {plat}")
                    console.print(f"  Output: {result.get('output')}")
                    console.print(f"  Size: {_format_size(result.get('size', 0))}")
                else:
                    console.print(f"[red]✗[/red] Build failed for {plat}")
                    
        except Exception as e:
            console.print(f"[red]✗[/red] Build failed for {plat}: {e}")
            results[plat] = {"success": False, "error": str(e)}
    
    # Output results in requested format
    _output_results(ctx, results)


@cli.command()
@click.option(
    '--channel', '-c',
    type=click.Choice(['stable', 'beta', 'alpha']),
    help='Release channel'
)
@click.option(
    '--target', '-t',
    multiple=True,
    help='Upload targets (can specify multiple)'
)
@click.option(
    '--draft',
    is_flag=True,
    help='Create as draft release'
)
@click.option(
    '--prerelease',
    is_flag=True,
    help='Mark as pre-release'
)
@pass_context
def upload(ctx, channel, target, draft, prerelease):
    """Upload built packages to configured targets."""
    if not ctx.config:
        console.print("[red]✗[/red] No configuration loaded")
        sys.exit(1)
    
    # Initialize plugin manager
    plugin_manager.initialize()
    
    # Get upload targets
    upload_config = ctx.config.get("upload", {})
    targets = upload_config.get("targets", [])
    
    if target:
        # Filter to specified targets
        targets = [t for t in targets if t.get("name") in target]
    
    if not targets:
        console.print("[red]✗[/red] No upload targets configured or specified")
        sys.exit(1)
    
    # Upload to each target
    for target_config in targets:
        if not target_config.get("enabled", True):
            continue
        
        target_type = target_config.get("type")
        target_name = target_config.get("name", target_type)
        
        if not ctx.quiet:
            console.print(f"\n[cyan]Uploading to {target_name}...[/cyan]")
        
        try:
            # Get uploader plugin
            uploader = plugin_manager.get_plugin(
                f"{target_type}_uploader",
                target_config.get("config", {})
            )
            
            # Find files to upload
            dist_dir = Path(ctx.config.get("build", {}).get("output_dir", "dist"))
            files = list(dist_dir.glob("*"))
            
            for file in files:
                if file.is_file():
                    result = uploader.upload(
                        str(file),
                        {
                            "channel": channel or "stable",
                            "draft": draft,
                            "prerelease": prerelease,
                            "version": ctx.config.get("app", {}).get("version", "1.0.0"),
                        }
                    )
                    
                    if not ctx.quiet:
                        if result.get("success"):
                            console.print(f"[green]✓[/green] Uploaded {file.name}")
                        else:
                            console.print(f"[red]✗[/red] Failed to upload {file.name}")
                            
        except Exception as e:
            console.print(f"[red]✗[/red] Upload failed for {target_name}: {e}")


@cli.command()
@click.option(
    '--wizard',
    is_flag=True,
    help='Start GUI in wizard mode'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='Configuration file to edit'
)
@pass_context
def gui(ctx, wizard, config):
    """Launch the GUI configuration tool."""
    try:
        # Import GUI module
        from looma.gui.app import LoomaGUI
        
        # Create and run GUI
        app = LoomaGUI(
            config_path=config,
            wizard_mode=wizard
        )
        app.run()
        
    except ImportError:
        console.print("[red]✗[/red] GUI dependencies not installed")
        console.print("\nInstall GUI support with:")
        console.print("  pip install looma[gui]")
        sys.exit(1)


@cli.group()
def plugin():
    """Manage Looma plugins."""
    pass


@plugin.command(name='list')
@click.option(
    '--type', '-t',
    type=click.Choice(['engine', 'uploader', 'hook', 'all']),
    default='all',
    help='Filter by plugin type'
)
@pass_context
def plugin_list(ctx, type):
    """List available plugins."""
    plugin_manager.initialize()
    
    # Create table
    table = Table(title="Available Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Version")
    table.add_column("Description")
    
    # Get plugins
    plugins = plugin_manager.list_plugins(
        None if type == 'all' else type
    )
    
    for plugin_info in plugins:
        table.add_row(
            plugin_info["name"],
            plugin_info["type"],
            plugin_info["version"],
            plugin_info["description"]
        )
    
    console.print(table)


@plugin.command(name='install')
@click.argument('package')
@pass_context
def plugin_install(ctx, package):
    """Install a plugin package."""
    try:
        plugin_manager.install_plugin(package)
        console.print(f"[green]✓[/green] Installed plugin: {package}")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to install plugin: {e}")
        sys.exit(1)


@plugin.command(name='schema')
@click.argument('name')
@click.option(
    '--output', '-o',
    type=click.Path(),
    help='Output schema to file'
)
@pass_context
def plugin_schema(ctx, name, output):
    """Get plugin configuration schema."""
    plugin_manager.initialize()
    
    schema = plugin_manager.get_plugin_schema(name)
    
    if not schema:
        console.print(f"[red]✗[/red] No schema available for plugin: {name}")
        sys.exit(1)
    
    if output:
        with open(output, 'w') as f:
            json.dump(schema, f, indent=2)
        console.print(f"[green]✓[/green] Schema saved to: {output}")
    else:
        console.print_json(data=schema)


@cli.command()
@click.option(
    '--force',
    is_flag=True,
    help='Force check for updates'
)
@click.option(
    '--channel', '-c',
    type=click.Choice(['stable', 'beta', 'alpha']),
    help='Update channel'
)
@pass_context
def check(ctx, force, channel):
    """Check for application updates."""
    from looma.client.updater import UpdateClient
    
    if not ctx.config:
        console.print("[red]✗[/red] No configuration loaded")
        sys.exit(1)
    
    update_config = ctx.config.get("update", {})
    
    if not update_config.get("enabled", False):
        console.print("[yellow]![/yellow] Updates are disabled in configuration")
        sys.exit(0)
    
    # Create update client
    client = UpdateClient(update_config)
    
    # Check for updates
    with console.status("Checking for updates..."):
        update_info = client.check_update(
            force=force,
            channel=channel or update_config.get("current_channel", "stable")
        )
    
    if update_info:
        console.print(f"[green]✓[/green] Update available: v{update_info.version}")
        console.print(f"\nRelease notes:\n{update_info.notes}")
        
        if click.confirm("Do you want to update now?"):
            client.perform_update(update_info)
    else:
        console.print("[green]✓[/green] You are running the latest version")


# Helper functions

def _get_current_platform():
    """Get the current platform."""
    import platform
    system = platform.system().lower()
    
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    else:
        return "linux"


def _format_size(size_bytes):
    """Format size in bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def _output_results(ctx, results):
    """Output results in the requested format."""
    if ctx.output_format == "json":
        console.print_json(data=results)
    elif ctx.output_format == "yaml":
        console.print(yaml.dump(results, default_flow_style=False))
    else:
        # Text format is handled inline
        pass


def _run_config_wizard(output_path):
    """Run interactive configuration wizard."""
    console.print("\n[bold cyan]Looma Configuration Wizard[/bold cyan]\n")
    
    # Collect basic information
    config = {
        "version": "2.0",
        "app": {},
        "build": {},
        "update": {},
    }
    
    # App information
    console.print("[bold]Application Information[/bold]")
    config["app"]["name"] = click.prompt("Application name", default="myapp")
    config["app"]["version"] = click.prompt("Version", default="1.0.0")
    config["app"]["description"] = click.prompt("Description", default="")
    
    # Build configuration
    console.print("\n[bold]Build Configuration[/bold]")
    
    # Show available engines
    plugin_manager.initialize()
    engines = plugin_manager.get_engine_plugins()
    
    console.print("Available packaging engines:")
    for i, engine in enumerate(engines, 1):
        console.print(f"  {i}. {engine}")
    
    engine_choice = click.prompt(
        "Select engine",
        type=click.IntRange(1, len(engines)),
        default=1
    )
    config["build"]["engine"] = engines[engine_choice - 1]
    
    config["build"]["entry_point"] = click.prompt(
        "Entry point",
        default="main.py"
    )
    
    # Update configuration
    console.print("\n[bold]Update Configuration[/bold]")
    config["update"]["enabled"] = click.confirm(
        "Enable auto-update?",
        default=True
    )
    
    if config["update"]["enabled"]:
        strategies = ["prompt", "force", "silent"]
        console.print("Update strategies:")
        for i, strategy in enumerate(strategies, 1):
            console.print(f"  {i}. {strategy}")
        
        strategy_choice = click.prompt(
            "Select strategy",
            type=click.IntRange(1, len(strategies)),
            default=1
        )
        config["update"]["strategy"] = strategies[strategy_choice - 1]
    
    # Save configuration
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    console.print(f"\n[green]✓[/green] Configuration saved to: {output_path}")


def _create_config_from_template(template, output_path):
    """Create configuration from template."""
    templates = {
        "basic": {
            "version": "2.0",
            "app": {
                "name": "myapp",
                "version": "1.0.0",
            },
            "build": {
                "engine": "pyinstaller",
                "entry_point": "main.py",
                "engine_options": {
                    "onefile": True,
                },
            },
        },
        "gui": {
            "version": "2.0",
            "app": {
                "name": "myguiapp",
                "version": "1.0.0",
            },
            "build": {
                "engine": "pyinstaller",
                "entry_point": "main.py",
                "engine_options": {
                    "onefile": True,
                    "windowed": True,
                },
            },
            "update": {
                "enabled": True,
                "strategy": "prompt",
            },
        },
    }
    
    config = templates.get(template, templates["basic"])
    
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


if __name__ == "__main__":
    cli()