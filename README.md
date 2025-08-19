# Looma - Python Application Packaging and Auto-Update Platform

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/yourusername/looma)

A comprehensive Python packaging and auto-update platform with GUI and CLI support, featuring plugin architecture and dynamic configuration.

## ✨ Features

- 🎯 **Multi-Engine Support**: PyInstaller, Nuitka, cx_Freeze with plugin architecture
- 🔄 **Auto-Update System**: Built-in update client with multiple strategies (prompt/silent/force)
- 🖥️ **Dual Interface**: Both GUI (wxPython) and CLI modes
- 🔐 **Security First**: Ed25519 signatures for all packages
- 📦 **Multiple Sources**: GitHub, GitLab, S3, Artifactory, HTTP support
- 🚀 **CI/CD Ready**: Full automation support with non-interactive mode
- 🌍 **Cross-Platform**: Windows, macOS, and Linux support
- 🔧 **Plugin System**: Extensible architecture for custom engines and uploaders
- 📋 **Dynamic Configuration**: JSON Schema-based parameter validation with GUI auto-generation

## 🚀 Quick Start

### Installation

```bash
# Basic installation
pip install looma

# With GUI support
pip install looma[gui]

# With all packaging engines
pip install looma[all]

# Development installation
pip install -e ".[dev]"
```

### GUI Mode

Launch the configuration wizard for first-time setup:

```bash
# Wizard mode for new users
looma gui --wizard

# Edit existing configuration
looma gui --config looma.yml
```

### CLI Mode

Build your application with a single command:

```bash
# Basic build
looma build --config looma.yml

# Specify engine and platform
looma build --engine nuitka --platform windows

# Parallel multi-platform build
looma build --platform all --parallel
```

### Configuration

Initialize a new project:

```bash
# Interactive wizard
looma init --wizard

# From template
looma init --template gui --output myapp.yml
```

## 📖 Usage Examples

### Basic Packaging

```bash
# Build with PyInstaller
looma build --engine pyinstaller --config looma.yml

# Build with Nuitka
looma build --engine nuitka --source github --channel beta

# CI/CD mode (non-interactive)
looma build --config looma.yml --no-interactive
```

### Update Management

```bash
# Check for updates
looma check --channel stable

# Force update
looma check --force

# Upload to multiple targets
looma upload --target github --target s3 --channel stable
```

### Plugin Management

```bash
# List available engines
looma engines

# Show engine schema
looma schema pyinstaller

# Validate configuration
looma validate --schema
```

## 📋 Configuration

### Basic Configuration (`looma.yml`)

```yaml
version: "1.0"

app:
  name: "MyApp"
  version: "1.0.0"
  description: "My awesome application"
  author: "Your Name"

packaging:
  engine: "pyinstaller"
  entry_point: "main.py"
  one_file: true
  console: false

update:
  source:
    type: "github"
    repo: "owner/repo"
    token: "${GITHUB_TOKEN}"  # Environment variable substitution
  channel: "stable"
  strategy: "prompt"  # prompt, silent, or force

security:
  signing:
    enabled: true
    private_key_path: "keys/private.key"
    algorithm: "ed25519"
```

### Multi-Environment Support

Looma supports environment-specific configurations:

- `looma.yml` - Default configuration
- `looma-dev.yml` - Development environment
- `looma-test.yml` - Testing environment
- `looma-prod.yml` - Production environment
- `looma-win.yml` - Windows platform
- `looma-mac.yml` - macOS platform
- `looma-linux.yml` - Linux platform

### Update Strategies

#### Prompt Strategy
```yaml
update:
  strategy: prompt
  ui:
    show_release_notes: true
    allow_skip: true
    allow_remind_later: true
    remind_interval: 86400  # 24 hours
```

#### Force Strategy
```yaml
update:
  strategy: force
  ui:
    force_after_days: 3
    show_release_notes: true
```

#### Silent Strategy
```yaml
update:
  strategy: silent
  ui:
    show_progress: false
    notify_on_success: true
```

## 🏗️ Project Structure

### Your Application Structure
```
your-app/
├── src/               # Source code directory
│   └── your_app/     # Your application package
├── looma.yml         # Configuration file
├── main.py          # Application entry point
├── requirements.txt # Python dependencies
├── pyproject.toml   # Project metadata
└── keys/           # Signing keys (git-ignored)
    ├── private.key
    └── public.key
```

### Looma Source Structure
```
looma/
├── src/looma/
│   ├── core/         # Core functionality
│   ├── packager/     # Packaging engines
│   │   ├── base.py   # Base packager interface
│   │   ├── factory.py # Packager factory
│   │   ├── pyinstaller.py
│   │   ├── nuitka.py
│   │   └── cxfreeze.py
│   ├── client/       # Update client
│   ├── sources/      # Update sources
│   │   ├── base.py   # Base source interface
│   │   ├── factory.py # Source factory
│   │   ├── github.py
│   │   ├── gitlab.py
│   │   └── s3.py
│   ├── security/     # Security modules
│   ├── gui/          # GUI components
│   │   ├── wizard.py # Configuration wizard
│   │   ├── editor.py # Configuration editor
│   │   └── dynamic_config_page.py # Dynamic form generation
│   └── cli/          # CLI commands
│       └── main.py   # CLI entry point
├── tests/            # Test suite
├── docs/             # Documentation
└── examples/         # Example projects
```

## 🔧 Advanced Features

### Delta Updates

Looma supports incremental updates using binary diff:

```yaml
update:
  delta:
    enabled: true
    threshold: 5242880  # 5MB - use delta for files larger than this
    algorithm: "bsdiff"
```

### Custom Packager Implementation

Create your own packaging engine:

```python
from looma.packager.base import BasePackager

class CustomPackager(BasePackager):
    """Custom packaging engine."""

    def get_parameters_schema(self) -> Dict[str, Any]:
        """Return parameter schema for dynamic configuration."""
        return {
            "custom_option": {
                "type": "string",
                "description": "Custom option description",
                "default": "value"
            }
        }

    def build(self, entry_point: str, output_dir: Path, **options) -> Path:
        """Build the application."""
        # Implementation here
        pass
```

### Custom Update Source

Register your own update source:

```python
from looma.sources.base import BaseSource
from looma.sources.factory import SourceFactory

class CustomSource(BaseSource):
    """Custom update source."""

    async def get_versions(self, channel: str) -> List[Dict[str, Any]]:
        """Get available versions."""
        # Implementation here
        pass

    async def download_update(self, version: str, target_path: Path) -> Path:
        """Download update package."""
        # Implementation here
        pass

# Register the source
SourceFactory.register("custom", CustomSource)
```

### CI/CD Integration

GitHub Actions example:

```yaml
name: Build and Release
on:
  push:
    tags:
      - 'v*'
jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.8'
      - run: pip install looma
      - run: looma build --config looma.yml --no-interactive
      - run: looma upload --target github --channel stable
      - uses: actions/upload-artifact@v3
        with:
          name: builds
          path: dist/
```

### Build Hooks

Configure pre/post build hooks:

```yaml
build:
  hooks:
    pre_build:
      - "python scripts/prepare.py"
      - "npm run build"
    post_build:
      - "python scripts/cleanup.py"
    on_error:
      - "python scripts/notify.py"
```

## 🌐 Environment Variables

Looma supports environment variable substitution in configuration:

```yaml
update:
  source:
    token: "${GITHUB_TOKEN}"  # Will use GITHUB_TOKEN env var
```

Override configuration via environment variables:

```bash
export LOOMA_UPDATE_CHANNEL=beta
export LOOMA_SOURCE_TOKEN=your-token
looma build --config looma.yml
```

## 📚 Documentation

Comprehensive documentation is available:

- [Getting Started](docs/getting-started.md)
- [Configuration Guide](docs/configuration.md)
- [GUI Tutorial](docs/gui-tutorial.md)
- [CLI Reference](docs/cli-reference.md)
- [Plugin Development](docs/plugins.md)
- [Security Best Practices](docs/security.md)
- [API Documentation](docs/api.md)

## 💡 Examples

Check the `examples/` directory for complete examples:

- [Simple PyQt Application](examples/pyqt-app/)
- [CLI Tool with Updates](examples/cli-tool/)
- [Multi-Platform Build](examples/multi-platform/)
- [Custom Plugin](examples/custom-plugin/)

## 📋 Requirements

- Python 3.8 or higher
- wxPython 4.2+ (for GUI mode)
- One of the packaging engines:
  - PyInstaller 5.0+
  - Nuitka 1.8+
  - cx_Freeze 6.15+

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/looma.git
cd looma

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src/ tests/

# Format code
black src/ tests/
```

## 🆘 Support

- 📖 [Documentation](https://looma.readthedocs.io)
- 💬 [Discussions](https://github.com/yourusername/looma/discussions)
- 🐛 [Issue Tracker](https://github.com/yourusername/looma/issues)
- 📧 [Email Support](mailto:support@looma.dev)

## 📄 License

Looma is released under the MIT License. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- PyInstaller, Nuitka, and cx_Freeze teams for excellent packaging tools
- wxPython team for the GUI framework
- All contributors and users of Looma

---

**Looma** - Making Python application distribution simple and powerful 🚀
