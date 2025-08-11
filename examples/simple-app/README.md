# Simple App Example

This example demonstrates how to integrate Looma into a simple Python GUI application.

## Features

- Basic Tkinter GUI application
- Looma auto-update integration
- Configuration via `looma.yml`
- Version management

## Project Structure

```
simple-app/
├── main.py          # Application entry point
├── looma.yml        # Looma configuration
├── version.json     # Version information
└── README.md        # This file
```

## Running the Example

### Development Mode

Run the application directly:

```bash
python main.py
```

### Building with Looma

1. Install Looma:
```bash
pip install looma
```

2. Build the application:
```bash
looma build --config looma.yml
```

3. The packaged application will be in the `dist/` directory.

## Configuration

The `looma.yml` file contains all configuration for:
- Packaging settings
- Update source and strategy
- Security settings
- Platform-specific options

### Key Configuration Options

#### Update Strategy

```yaml
update:
  strategy: "prompt"  # Options: prompt, silent, force
```

- `prompt`: Ask user before updating
- `silent`: Download in background, prompt to install
- `force`: Automatically install updates

#### Packaging Engine

```yaml
packaging:
  engine: "pyinstaller"  # Options: pyinstaller, nuitka, cxfreeze
```

Choose the packaging engine based on your needs:
- `pyinstaller`: Fast, widely compatible
- `nuitka`: Better performance, smaller size
- `cxfreeze`: Cross-platform support

## Testing Updates

To test the update functionality:

1. Build version 1.0.0
2. Update `version.json` to 1.0.1
3. Build again
4. Upload to your configured update source
5. Run the 1.0.0 version - it should detect the update

## Environment Variables

The configuration uses environment variables for sensitive data:

- `GITHUB_TOKEN`: GitHub personal access token
- `HTTP_PROXY`: HTTP proxy URL
- `HTTPS_PROXY`: HTTPS proxy URL

## Customization

### Adding Features

Add new features to the `_setup_ui()` method in `main.py`:

```python
ttk.Button(
    features_frame,
    text="My Feature",
    command=self.my_feature_handler
).grid(row=0, column=3, padx=5, pady=5)
```

### Changing Update Behavior

Modify the update configuration in `looma.yml`:

```yaml
update:
  check_interval: 7200  # Check every 2 hours
  ui:
    show_release_notes: false
    allow_skip: false  # Force updates
```

## Troubleshooting

### Application doesn't start
- Check Python version (3.8+ required)
- Verify all dependencies are installed
- Check `looma.log` for errors

### Updates not detected
- Verify update source configuration
- Check network connectivity
- Ensure version numbers follow semantic versioning

### Build fails
- Verify packaging engine is installed
- Check file paths in configuration
- Review build logs in console output

## Support

For issues or questions:
- Check the main [Looma documentation](../../docs/)
- Open an issue on GitHub
- Contact support@looma.dev