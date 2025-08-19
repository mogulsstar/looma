""" configuration wizard for Looma GUI with progress tracking and validation."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import wx
import wx.adv
import wx.lib.agw.aui as aui
from looma.core.config import ConfigManager
from looma.core.constants import DEFAULT_CONFIG_FILE
from looma.packager.factory import packager_factory
from looma.gui.engine_option_dialog import EngineOptionsDialog


class ConfigWizard(wx.adv.Wizard):
    """
    configuration wizard with progress tracking and validation.

    Features:
    - Progress indicator showing current step
    - Required field validation
    - Load/edit existing configurations
    - Engine-specific parameter customization
    - Interactive help tooltips
    """

    def __init__(self, parent, config_path: Optional[Path] = None, load_existing: bool = True):
        """
        Initialize  configuration wizard.

        Parameters
        ----------
        parent : wx.Window
            Parent window
        config_path : Optional[Path]
            Configuration file path
        load_existing : bool
            Whether to load existing configuration if found
        """
        super().__init__(
            parent,
            title="Looma Configuration Wizard",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        # Initialize configuration
        self.config_path = config_path or Path(DEFAULT_CONFIG_FILE)

        # Determine if we're editing an existing file
        self.is_editing = load_existing and self.config_path.exists()

        # Load configuration if editing, otherwise use defaults
        if self.is_editing:
            try:
                config_manager = ConfigManager(self.config_path)
                loaded_config = config_manager.load()
                self.config = self._merge_configs(self._initialize_config(False), loaded_config)
            except Exception:
                # If loading fails, start with defaults
                self.config = self._initialize_config(False)
                self.is_editing = False
        else:
            self.config = self._initialize_config(False)

        # Track pages for progress
        self.pages = []
        self.current_page_index = 0

        # Create pages with validation (ordered to match YAML structure)
        self.welcome_page = WelcomePage(self)
        self.build_settings_page = BuildSettingsPage(self)  # Build settings first
        self.app_page = ApplicationPage(self)
        self.packaging_page = PackagingPage(self)
        self.security_page = SecurityPage(self)
        self.source_page = SourcePage(self)  # Update source after security
        self.summary_page = SummaryPage(self)

        # Store pages for progress tracking
        self.pages = [
            self.welcome_page,
            self.build_settings_page,
            self.app_page,
            self.packaging_page,
            self.security_page,
            self.source_page,
            self.summary_page,
        ]

        # Chain pages to match YAML order (starting from Welcome page)
        wx.adv.WizardPageSimple.Chain(self.welcome_page, self.build_settings_page)
        wx.adv.WizardPageSimple.Chain(self.build_settings_page, self.app_page)
        wx.adv.WizardPageSimple.Chain(self.app_page, self.packaging_page)
        wx.adv.WizardPageSimple.Chain(self.packaging_page, self.security_page)
        wx.adv.WizardPageSimple.Chain(self.security_page, self.source_page)
        wx.adv.WizardPageSimple.Chain(self.source_page, self.summary_page)

        # Set initial size
        self.SetPageSize((650, 500))

        # Bind events
        self.Bind(wx.adv.EVT_WIZARD_PAGE_CHANGING, self.on_page_changing)
        self.Bind(wx.adv.EVT_WIZARD_PAGE_CHANGED, self.on_page_changed)
        self.Bind(wx.adv.EVT_WIZARD_FINISHED, self.on_finished)
        self.Bind(wx.adv.EVT_WIZARD_CANCEL, self.on_cancelled)

        # Create progress panel at the top
        self._create_progress_panel()

    def _initialize_config(self, load_existing: bool) -> Dict[str, Any]:
        """Initialize or load configuration."""
        default_config = {
            "build_settings": {
                "build": {
                    "output_dir": "dist",
                    "build_dir": "build",
                    "clean": True,
                },
                "logging": {
                    "level": "INFO",
                    "file": "",
                },
            },
            "app": {
                "name": "",
                "version": "1.0.0",
                "description": "",
                "author": "",
                "email": "",
                "license": "MIT",
            },
            "packaging": {
                "engine": "pyinstaller",
                "entry_point": "main.py",
                "one_file": True,
                "console": False,
                "icon": "",
                "additional_files": [],
                "hidden_imports": [],
                "exclude_modules": [],
            },
            "update": {
                "enabled": True,
                "channel": "stable",
                "strategy": "prompt",
                "check_interval": 86400,
                "source": {
                    "type": "github",
                    "repo": "",
                },
            },
            "security": {
                "signing": {
                    "enabled": False,
                    "private_key_path": "",
                },
                "verification": {
                    "strict": True,
                },
                "ssl": {
                    "verify": True,
                },
            },
            "version": "1.0",
        }

        if load_existing and self.config_path.exists():
            try:
                config_manager = ConfigManager(self.config_path)
                loaded_config = config_manager.load()
                self.is_editing = True
                # Merge with defaults to ensure all keys exist
                return self._merge_configs(default_config, loaded_config)
            except Exception:
                pass

        return default_config

    def _merge_configs(self, default: Dict, loaded: Dict) -> Dict:
        """Recursively merge loaded config with defaults."""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result

    def _create_progress_panel(self):
        """Create progress indicator panel."""
        # This will be added to each page
        pass

    def GetFirstPage(self):
        """Get first wizard page."""
        return self.welcome_page

    def on_page_changing(self, event):
        """Handle page changing event for validation."""
        if event.GetDirection():  # Moving forward
            page = event.GetPage()
            if hasattr(page, 'validate'):
                if not page.validate():
                    event.Veto()
                    return
            if hasattr(page, 'save_data'):
                page.save_data()

    def on_page_changed(self, event):
        """Handle page changed event for progress update."""
        page = event.GetPage()
        if hasattr(page, 'update_progress'):
            page.update_progress()

    def on_finished(self, event):
        """Handle wizard finished."""
        # Collect data from all pages
        for page in self.pages:
            if hasattr(page, 'save_data'):
                page.save_data()

        # Save configuration
        try:
            config_manager = ConfigManager(self.config_path)
            config_manager.save(self.config, self.config_path)

            wx.MessageBox(
                f"Configuration saved to {self.config_path}",
                "Success",
                wx.OK | wx.ICON_INFORMATION,
            )
        except Exception as e:
            wx.MessageBox(
                f"Failed to save configuration: {e}",
                "Error",
                wx.OK | wx.ICON_ERROR,
            )

    def on_cancelled(self, event):
        """Handle wizard cancelled."""
        if self.is_editing:
            result = wx.MessageBox(
                "Are you sure you want to cancel? Changes will not be saved.",
                "Confirm Cancel",
                wx.YES_NO | wx.ICON_QUESTION,
            )
            if result == wx.NO:
                event.Veto()


class WizardPageBase(wx.adv.WizardPageSimple):
    """Base class for wizard pages with common functionality."""

    def __init__(self, parent: ConfigWizard, title: str, step_number: int, total_steps: int):
        """
        Initialize wizard page base.

        Parameters
        ----------
        parent : ConfigWizard
            Parent wizard
        title : str
            Page title
        step_number : int
            Current step number
        total_steps : int
            Total number of steps
        """
        super().__init__(parent)
        self.wizard = parent
        self.title = title
        self.step_number = step_number
        self.total_steps = total_steps

        # Create main sizer
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Add progress indicator
        self._create_progress_indicator()

        # Add title
        title_text = wx.StaticText(self, label=title)
        title_font = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title_text.SetFont(title_font)
        self.main_sizer.Add(title_text, 0, wx.ALL | wx.CENTER, 10)

        # Add separator
        self.main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Content sizer for derived classes
        self.content_sizer = wx.BoxSizer(wx.VERTICAL)
        self.main_sizer.Add(self.content_sizer, 1, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(self.main_sizer)

    def _create_progress_indicator(self):
        """Create progress indicator at the top of the page."""
        progress_panel = wx.Panel(self)
        progress_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Step indicator
        step_text = wx.StaticText(
            progress_panel,
            label=f"Step {self.step_number} of {self.total_steps}"
        )
        step_font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        step_text.SetFont(step_font)
        progress_sizer.Add(step_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        # Progress bar
        progress_sizer.Add((20, -1))  # Spacer
        self.progress_bar = wx.Gauge(progress_panel, range=self.total_steps)
        self.progress_bar.SetValue(self.step_number)
        progress_sizer.Add(self.progress_bar, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        progress_panel.SetSizer(progress_sizer)
        self.main_sizer.Add(progress_panel, 0, wx.EXPAND | wx.ALL, 5)

    def add_required_field(self, label: str, control: wx.Control, tooltip: str = ""):
        """
        Add a required field with visual indicator.

        Parameters
        ----------
        label : str
            Field label
        control : wx.Control
            Input control
        tooltip : str
            Optional tooltip text
        """
        field_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Label with required indicator
        label_text = wx.StaticText(self, label=f"{label} *")
        label_text.SetForegroundColour(wx.Colour(0, 0, 128))
        field_sizer.Add(label_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        # Control
        field_sizer.Add(control, 1, wx.EXPAND)

        # Help icon if tooltip provided
        if tooltip:
            help_btn = wx.Button(self, label=" ? ")
            help_btn.SetMinSize((40, -1))  # Set minimum width, let height be automatic
            help_btn.SetToolTip(tooltip)
            field_sizer.Add(help_btn, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 5)

        self.content_sizer.Add(field_sizer, 0, wx.EXPAND | wx.ALL, 5)

        return control

    def add_optional_field(self, label: str, control: wx.Control, tooltip: str = ""):
        """
        Add an optional field.

        Parameters
        ----------
        label : str
            Field label
        control : wx.Control
            Input control
        tooltip : str
            Optional tooltip text
        """
        field_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Label
        label_text = wx.StaticText(self, label=label)
        field_sizer.Add(label_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        # Control
        field_sizer.Add(control, 1, wx.EXPAND)

        # Help icon if tooltip provided
        if tooltip:
            help_btn = wx.Button(self, label=" ? ")
            help_btn.SetMinSize((40, -1))  # Set minimum width, let height be automatic
            help_btn.SetToolTip(tooltip)
            field_sizer.Add(help_btn, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 5)

        self.content_sizer.Add(field_sizer, 0, wx.EXPAND | wx.ALL, 5)

        return control

    def validate(self) -> bool:
        """
        Validate page inputs.

        Returns
        -------
        bool
            True if validation passes
        """
        return True

    def save_data(self):
        """Save page data to configuration."""
        pass

    def update_progress(self):
        """Update progress indicator."""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.SetValue(self.step_number)
        # Load existing values when page is shown
        if hasattr(self, 'load_existing_values'):
            self.load_existing_values()


class WelcomePage(WizardPageBase):
    """ welcome page with better introduction."""

    def __init__(self, parent):
        super().__init__(parent, "Welcome to Looma Configuration Wizard", 1, 7)

        # Welcome message
        welcome_text = wx.StaticText(
            self,
            label="This wizard will guide you through configuring your Looma packaging and auto-update settings.\n\n"
                  "The configuration process includes:\n"
                  "• Build settings and logging options\n"
                  "• Application information\n"
                  "• Packaging engine selection and customization\n"
                  "• Security settings\n"
                  "• Update source configuration\n\n"
                  "Required fields are marked with an asterisk (*).\n"
                  "You can go back to previous steps at any time."
        )
        welcome_text.Wrap(600)
        self.content_sizer.Add(welcome_text, 0, wx.ALL, 10)

        # Mode indicator - will be updated dynamically
        self.mode_text = wx.StaticText(self, label="")
        self.content_sizer.Add(self.mode_text, 0, wx.ALL, 10)

    def update_progress(self):
        """Update progress and mode indicator when page is shown."""
        super().update_progress()

        # Update mode indicator based on current wizard state
        if self.wizard.is_editing:
            self.mode_text.SetLabel(
                f"Mode: Editing existing configuration\nFile: {self.wizard.config_path}"
            )
            self.mode_text.SetForegroundColour(wx.Colour(0, 0, 128))
        else:
            self.mode_text.SetLabel(
                f"Mode: Creating new configuration\nFile: {self.wizard.config_path}"
            )
            self.mode_text.SetForegroundColour(wx.Colour(0, 128, 0))


class BuildSettingsPage(WizardPageBase):
    """Build settings configuration page."""

    def __init__(self, parent):
        super().__init__(parent, "Build Settings", 2, 7)

        # Build options
        build_box = wx.StaticBox(self, label="Build Options")
        build_sizer = wx.StaticBoxSizer(build_box, wx.VERTICAL)

        # Output directory
        output_sizer = wx.BoxSizer(wx.HORIZONTAL)
        output_sizer.Add(wx.StaticText(self, label="Output Directory:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.output_ctrl = wx.TextCtrl(self, value="dist")
        output_sizer.Add(self.output_ctrl, 1)

        build_sizer.Add(output_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.clean_check = wx.CheckBox(self, label="Clean output directory before build")
        self.clean_check.SetValue(True)
        build_sizer.Add(self.clean_check, 0, wx.ALL, 5)

        self.content_sizer.Add(build_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Logging options
        log_box = wx.StaticBox(self, label="Logging")
        log_sizer = wx.StaticBoxSizer(log_box, wx.VERTICAL)

        # Log level
        level_sizer = wx.BoxSizer(wx.HORIZONTAL)
        level_sizer.Add(wx.StaticText(self, label="Log Level:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.level_choice = wx.Choice(
            self,
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        )
        self.level_choice.SetSelection(1)  # INFO
        level_sizer.Add(self.level_choice, 1)

        log_sizer.Add(level_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Log file
        file_sizer = wx.BoxSizer(wx.HORIZONTAL)
        file_sizer.Add(wx.StaticText(self, label="Log File:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.logfile_ctrl = wx.TextCtrl(self)
        self.logfile_ctrl.SetToolTip("Optional: Leave empty for console only")
        file_sizer.Add(self.logfile_ctrl, 1)

        log_sizer.Add(file_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.content_sizer.Add(log_sizer, 0, wx.EXPAND | wx.ALL, 5)

    def load_existing_values(self):
        """Load existing values if editing."""
        if self.wizard.is_editing:
            # Use structure with build_settings key
            build_settings_config = self.wizard.config.get("build_settings", {})

            build_config = build_settings_config.get("build", {})
            log_config = build_settings_config.get("logging", {})

            self.output_ctrl.SetValue(build_config.get("output_dir", "dist"))
            self.clean_check.SetValue(build_config.get("clean", True))

            level = log_config.get("level", "INFO")
            levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if level in levels:
                self.level_choice.SetSelection(levels.index(level))
            self.logfile_ctrl.SetValue(log_config.get("file", ""))

    def save_data(self):
        """Save build settings."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        # Save under build_settings key
        self.wizard.config["build_settings"] = {
            "build": {
                "output_dir": self.output_ctrl.GetValue().strip() or "dist",
                "build_dir": "build",  # Default build directory
                "clean": self.clean_check.GetValue(),
            },
            "logging": {
                "level": levels[self.level_choice.GetSelection()],
                "file": self.logfile_ctrl.GetValue().strip(),
            }
        }


class ApplicationPage(WizardPageBase):
    """ application information page with validation."""

    def __init__(self, parent):
        super().__init__(parent, "Application Information", 3, 7)

        # Create input fields
        self.name_ctrl = self.add_required_field(
            "Application Name:",
            wx.TextCtrl(self),
            "The name of your application (e.g., 'MyApp')"
        )

        self.version_ctrl = self.add_required_field(
            "Version:",
            wx.TextCtrl(self),
            "Application version (e.g., '1.0.0')"
        )

        self.desc_ctrl = self.add_optional_field(
            "Description:",
            wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(-1, 60)),
            "Brief description of your application"
        )

        self.author_ctrl = self.add_required_field(
            "Author:",
            wx.TextCtrl(self),
            "Your name or organization"
        )

        self.email_ctrl = self.add_required_field(
            "Email:",
            wx.TextCtrl(self),
            "Contact email address"
        )

        self.license_ctrl = self.add_optional_field(
            "License:",
            wx.Choice(self, choices=["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "Proprietary", "Other"]),
            "Software license"
        )
        self.license_ctrl.SetSelection(0)

    def load_existing_values(self):
        """Load existing values if editing."""
        if self.wizard.is_editing:
            app_config = self.wizard.config.get("app", {})
            self.name_ctrl.SetValue(app_config.get("name", ""))
            self.version_ctrl.SetValue(app_config.get("version", "1.0.0"))
            self.desc_ctrl.SetValue(app_config.get("description", ""))
            self.author_ctrl.SetValue(app_config.get("author", ""))
            self.email_ctrl.SetValue(app_config.get("email", ""))

            license_val = app_config.get("license", "MIT")
            licenses = ["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "Proprietary", "Other"]
            if license_val in licenses:
                self.license_ctrl.SetSelection(licenses.index(license_val))

    def validate(self) -> bool:
        """Validate required fields."""
        errors = []

        if not self.name_ctrl.GetValue().strip():
            errors.append("Application name is required")

        if not self.version_ctrl.GetValue().strip():
            errors.append("Version is required")

        if not self.author_ctrl.GetValue().strip():
            errors.append("Author is required")

        email = self.email_ctrl.GetValue().strip()
        if not email:
            errors.append("Email is required")
        elif "@" not in email:
            errors.append("Invalid email format")

        if errors:
            wx.MessageBox(
                "Please fix the following errors:\n\n" + "\n".join(errors),
                "Validation Error",
                wx.OK | wx.ICON_ERROR
            )
            return False

        return True

    def save_data(self):
        """Save application data."""
        self.wizard.config["app"] = {
            "name": self.name_ctrl.GetValue().strip(),
            "version": self.version_ctrl.GetValue().strip(),
            "description": self.desc_ctrl.GetValue().strip(),
            "author": self.author_ctrl.GetValue().strip(),
            "email": self.email_ctrl.GetValue().strip(),
            "license": self.license_ctrl.GetStringSelection(),
        }


class PackagingPage(WizardPageBase):
    """ packaging configuration page."""

    def __init__(self, parent):
        super().__init__(parent, "Packaging Configuration", 4, 7)

        # Engine selection
        engine_sizer = wx.BoxSizer(wx.HORIZONTAL)
        engine_sizer.Add(wx.StaticText(self, label="Packaging Engine: *"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.engine_choice = wx.Choice(
            self,
            choices=["PyInstaller", "Nuitka", "cx_Freeze"]
        )
        self.engine_choice.SetSelection(0)
        self.engine_choice.Bind(wx.EVT_CHOICE, self.on_engine_change)
        engine_sizer.Add(self.engine_choice, 1)

        self.content_sizer.Add(engine_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Engine description
        self.engine_desc = wx.StaticText(self, label="")
        self.engine_desc.SetForegroundColour(wx.Colour(64, 64, 64))
        self.content_sizer.Add(self.engine_desc, 0, wx.ALL, 5)
        self.update_engine_description()

        # Entry point
        self.entry_ctrl = self.add_required_field(
            "Entry Point:",
            wx.TextCtrl(self),
            "Main Python file to run (e.g., 'main.py' or 'src/app.py')"
        )

        # Browse for entry point
        browse_btn = wx.Button(self, label="Browse for Entry Point...")
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse_entry)
        self.content_sizer.Add(browse_btn, 0, wx.LEFT, 100)

        # Basic options
        self.onefile_check = wx.CheckBox(self, label="Create single executable file")
        self.onefile_check.SetValue(True)
        self.content_sizer.Add(self.onefile_check, 0, wx.ALL, 5)

        self.console_check = wx.CheckBox(self, label="Show console window")
        self.content_sizer.Add(self.console_check, 0, wx.ALL, 5)

        # Icon selection
        icon_sizer = wx.BoxSizer(wx.HORIZONTAL)
        icon_sizer.Add(wx.StaticText(self, label="Application Icon:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.icon_ctrl = wx.TextCtrl(self)
        icon_sizer.Add(self.icon_ctrl, 1)

        icon_browse_btn = wx.Button(self, label="Browse...")
        icon_browse_btn.Bind(wx.EVT_BUTTON, self.on_browse_icon)
        icon_sizer.Add(icon_browse_btn, 0, wx.LEFT, 10)

        self.content_sizer.Add(icon_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Separator line
        self.content_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

        # Advanced Options button
        advanced_btn = wx.Button(self, label="Advanced Engine Options...")
        advanced_btn.Bind(wx.EVT_BUTTON, self.on_advanced_options)
        self.content_sizer.Add(advanced_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        # Store engine-specific advanced options
        self.engine_advanced_options = {}

    def load_existing_values(self):
        """Load existing values if editing."""
        if self.wizard.is_editing:
            pkg_config = self.wizard.config.get("packaging", {})

            engine = pkg_config.get("engine", "pyinstaller")
            engines = ["pyinstaller", "nuitka", "cxfreeze"]
            if engine in engines:
                self.engine_choice.SetSelection(engines.index(engine))
                self.update_engine_description()

            self.entry_ctrl.SetValue(pkg_config.get("entry_point", "main.py"))
            self.onefile_check.SetValue(pkg_config.get("one_file", True))
            self.console_check.SetValue(pkg_config.get("console", False))
            self.icon_ctrl.SetValue(pkg_config.get("icon", ""))

            # Load engine-specific advanced options
            engine_options_key = f"{engine}_options"
            if engine_options_key in pkg_config:
                self.engine_advanced_options = pkg_config[engine_options_key]

    def on_engine_change(self, event):
        """Handle engine selection change."""
        self.update_engine_description()
        # Clear engine-specific advanced options when engine changes
        self.engine_advanced_options = {}

    def update_engine_description(self):
        """Update engine description based on selection."""
        descriptions = {
            0: "PyInstaller: Fast and reliable, good for most Python applications. Supports many third-party packages.",
            1: "Nuitka: Compiles Python to C++, produces smaller and faster executables. Best performance.",
            2: "cx_Freeze: Cross-platform, good compatibility. Simple and straightforward."
        }

        selection = self.engine_choice.GetSelection()
        self.engine_desc.SetLabel(descriptions.get(selection, ""))
        self.engine_desc.Wrap(600)

    def on_browse_entry(self, event):
        """Browse for entry point file."""
        with wx.FileDialog(
            self,
            "Select Entry Point",
            wildcard="Python files (*.py)|*.py",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                # Make path relative if possible
                path = Path(dialog.GetPath())
                try:
                    rel_path = path.relative_to(Path.cwd())
                    self.entry_ctrl.SetValue(str(rel_path))
                except ValueError:
                    self.entry_ctrl.SetValue(str(path))

    def on_browse_icon(self, event):
        """Browse for icon file."""
        with wx.FileDialog(
            self,
            "Select Icon File",
            wildcard="Icon files (*.ico;*.icns;*.png)|*.ico;*.icns;*.png|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.icon_ctrl.SetValue(dialog.GetPath())

    def validate(self) -> bool:
        """Validate required fields."""
        if not self.entry_ctrl.GetValue().strip():
            wx.MessageBox(
                "Entry point is required",
                "Validation Error",
                wx.OK | wx.ICON_ERROR
            )
            return False

        return True

    def on_advanced_options(self, event):
        """Handle advanced engine options button click."""
        engines = ["pyinstaller", "nuitka", "cxfreeze"]
        engine = engines[self.engine_choice.GetSelection()]

        dialog = EngineOptionsDialog(self, engine, self.engine_advanced_options)
        if dialog.ShowModal() == wx.ID_OK:
            self.engine_advanced_options = dialog.get_options()
        dialog.Destroy()

    def save_data(self):
        """Save packaging data."""
        engines = ["pyinstaller", "nuitka", "cxfreeze"]
        engine = engines[self.engine_choice.GetSelection()]

        self.wizard.config["packaging"] = {
            "engine": engine,
            "entry_point": self.entry_ctrl.GetValue().strip(),
            "one_file": self.onefile_check.GetValue(),
            "console": self.console_check.GetValue(),
            "icon": self.icon_ctrl.GetValue().strip(),
        }

        # Save engine-specific advanced options if any
        if self.engine_advanced_options:
            engine_options_key = f"{engine}_options"
            self.wizard.config["packaging"][engine_options_key] = self.engine_advanced_options


class DynamicEngineOptionsPage(WizardPageBase):
    """Dynamic engine-specific options page based on parameter schema."""

    def __init__(self, parent):
        super().__init__(parent, "Engine Options", 5, 8)
        self.controls = {}  # Store control references by parameter name
        self.engine = None
        self.schema = {}

    def setup_for_engine(self, engine: str):
        """Set up the page for a specific engine."""
        self.engine = engine

        # Clear existing controls from content_sizer only
        self.controls.clear()

        # Clear the content sizer (this preserves the title and progress bar)
        self.content_sizer.Clear(True)

        # Update page title
        engine_name = engine.replace("_", " ").title()
        self.title = f"{engine_name} Options"

        # Get parameter schema from the packager
        try:
            # Ensure the factory is initialized
            if not packager_factory.packagers:
                packager_factory._register_default_packagers()

            # Get the packager class from the factory
            packager_class = packager_factory.get_packager_class(engine)

            # Create a minimal config for initialization
            minimal_config = {
                "packaging": {"entry_point": "main.py"},
                "build": {"output_dir": "dist", "build_dir": "build"},
                "app": {"name": "app", "version": "1.0.0"}
            }
            packager = packager_class(minimal_config)  # Temporary instance to get schema
            self.schema = packager.get_parameters_schema()

            # Create controls based on schema
            self._create_controls_from_schema()

        except ImportError as e:
            error_label = wx.StaticText(self, label=f"Error: {engine} packager not installed. {str(e)}")
            self.content_sizer.Add(error_label, 0, wx.ALL, 10)
        except Exception as e:
            import traceback
            error_text = f"Error loading {engine} parameters:\n{str(e)}\n\nDetails:\n{traceback.format_exc()}"
            error_ctrl = wx.TextCtrl(self, value=error_text, style=wx.TE_MULTILINE | wx.TE_READONLY)
            error_ctrl.SetMinSize((600, 200))
            self.content_sizer.Add(error_ctrl, 0, wx.ALL | wx.EXPAND, 10)

        self.Layout()

    def _create_controls_from_schema(self):
        """Create UI controls based on parameter schema."""
        # Group parameters by category if possible
        basic_params = []
        advanced_params = []

        for param_name, param_info in self.schema.items():
            # Skip certain base parameters that are handled elsewhere
            if param_name in ["entry_point", "output_dir", "dist_dir"]:
                continue

            # Categorize parameters
            if param_name in ["onefile", "onedir", "console", "windowed", "icon", "name"]:
                basic_params.append((param_name, param_info))
            else:
                advanced_params.append((param_name, param_info))

        # Create basic options section
        if basic_params:
            basic_box = wx.StaticBox(self, label="Basic Options")
            basic_sizer = wx.StaticBoxSizer(basic_box, wx.VERTICAL)

            for param_name, param_info in basic_params:
                self._create_control(basic_sizer, param_name, param_info)

            self.content_sizer.Add(basic_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Create advanced options section
        if advanced_params:
            adv_box = wx.StaticBox(self, label="Advanced Options")
            adv_sizer = wx.StaticBoxSizer(adv_box, wx.VERTICAL)

            # Create a scrolled panel for advanced options if there are many
            if len(advanced_params) > 10:
                scroll_panel = wx.ScrolledWindow(self, size=(-1, 300))
                scroll_panel.SetScrollRate(0, 20)
                scroll_sizer = wx.BoxSizer(wx.VERTICAL)

                for param_name, param_info in advanced_params:
                    self._create_control(scroll_sizer, param_name, param_info, scroll_panel)

                scroll_panel.SetSizer(scroll_sizer)
                adv_sizer.Add(scroll_panel, 1, wx.EXPAND | wx.ALL, 5)
            else:
                for param_name, param_info in advanced_params:
                    self._create_control(adv_sizer, param_name, param_info)

            self.content_sizer.Add(adv_sizer, 0, wx.EXPAND | wx.ALL, 5)

    def _create_control(self, sizer, param_name, param_info, parent=None):
        """Create a single control based on parameter type."""
        if parent is None:
            parent = self

        param_type = param_info.get("type", "input")
        description = param_info.get("description", param_name)
        default = param_info.get("default", "")
        required = param_info.get("required", False)

        # Create label
        label_text = self._format_label(param_name)
        if required:
            label_text += " *"

        if param_type == "flag" or param_type == "boolean":
            # Create checkbox for boolean/flag parameters
            checkbox = wx.CheckBox(parent, label=label_text)
            checkbox.SetToolTip(description)
            if default:
                checkbox.SetValue(bool(default))
            self.controls[param_name] = checkbox
            sizer.Add(checkbox, 0, wx.ALL, 5)

        elif param_type == "list":
            # Create list control with add/remove buttons
            label = wx.StaticText(parent, label=label_text)
            label.SetToolTip(description)
            sizer.Add(label, 0, wx.ALL, 5)

            list_box = wx.ListBox(parent, size=(-1, 80))
            self.controls[param_name] = list_box
            sizer.Add(list_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

            btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
            add_btn = wx.Button(parent, label="Add...", size=(70, -1))
            add_btn.Bind(wx.EVT_BUTTON, lambda e, pn=param_name: self._on_add_list_item(e, pn))
            btn_sizer.Add(add_btn, 0, wx.RIGHT, 5)

            remove_btn = wx.Button(parent, label="Remove", size=(70, -1))
            remove_btn.Bind(wx.EVT_BUTTON, lambda e, pn=param_name: self._on_remove_list_item(e, pn))
            btn_sizer.Add(remove_btn, 0)

            sizer.Add(btn_sizer, 0, wx.LEFT | wx.BOTTOM, 10)

        elif param_type == "choice":
            # Create choice control for enumerated options
            h_sizer = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(parent, label=label_text)
            label.SetToolTip(description)
            h_sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

            choices = param_info.get("choices", [])
            choice_ctrl = wx.Choice(parent, choices=choices)
            if default in choices:
                choice_ctrl.SetSelection(choices.index(default))
            self.controls[param_name] = choice_ctrl
            h_sizer.Add(choice_ctrl, 1)

            sizer.Add(h_sizer, 0, wx.EXPAND | wx.ALL, 5)

        elif param_type == "path":
            # Create text control with browse button for paths
            label = wx.StaticText(parent, label=label_text)
            label.SetToolTip(description)
            sizer.Add(label, 0, wx.ALL, 5)

            h_sizer = wx.BoxSizer(wx.HORIZONTAL)
            text_ctrl = wx.TextCtrl(parent, value=str(default))
            self.controls[param_name] = text_ctrl
            h_sizer.Add(text_ctrl, 1, wx.RIGHT, 5)

            browse_btn = wx.Button(parent, label="Browse...", size=(80, -1))
            browse_btn.Bind(wx.EVT_BUTTON, lambda e, tc=text_ctrl: self._on_browse_path(e, tc))
            h_sizer.Add(browse_btn, 0)

            sizer.Add(h_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        else:  # input, integer, string, or other text-based types
            # Create text control
            label = wx.StaticText(parent, label=label_text)
            label.SetToolTip(description)
            sizer.Add(label, 0, wx.ALL, 5)

            text_ctrl = wx.TextCtrl(parent, value=str(default))
            self.controls[param_name] = text_ctrl
            sizer.Add(text_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    def _format_label(self, param_name: str) -> str:
        """Format parameter name as a readable label."""
        # Convert snake_case to Title Case
        words = param_name.replace("_", " ").split()
        return " ".join(word.capitalize() for word in words)

    def _on_add_list_item(self, event, param_name):
        """Handle adding item to list parameter."""
        dialog = wx.TextEntryDialog(self, f"Enter value to add:", "Add Item")
        if dialog.ShowModal() == wx.ID_OK:
            value = dialog.GetValue().strip()
            if value:
                list_box = self.controls[param_name]
                list_box.Append(value)
        dialog.Destroy()

    def _on_remove_list_item(self, event, param_name):
        """Handle removing item from list parameter."""
        list_box = self.controls[param_name]
        selection = list_box.GetSelection()
        if selection != wx.NOT_FOUND:
            list_box.Delete(selection)

    def _on_browse_path(self, event, text_ctrl):
        """Handle browse button for path parameters."""
        with wx.FileDialog(
            self,
            "Select File",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                text_ctrl.SetValue(dialog.GetPath())

    def load_existing_values(self):
        """Load existing values if editing."""
        if self.wizard.is_editing and self.engine:
            pkg_config = self.wizard.config.get("packaging", {})
            engine_options = pkg_config.get(f"{self.engine}_options", {})

            for param_name, control in self.controls.items():
                if param_name in engine_options:
                    value = engine_options[param_name]

                    if isinstance(control, wx.CheckBox):
                        control.SetValue(bool(value))
                    elif isinstance(control, wx.Choice):
                        choices = [control.GetString(i) for i in range(control.GetCount())]
                        if value in choices:
                            control.SetSelection(choices.index(value))
                    elif isinstance(control, wx.ListBox):
                        control.Clear()
                        if isinstance(value, list):
                            control.AppendItems(value)
                    elif isinstance(control, wx.TextCtrl):
                        control.SetValue(str(value))

    def save_data(self):
        """Save engine-specific options."""
        if not self.engine:
            return

        options = {}

        for param_name, control in self.controls.items():
            param_info = self.schema.get(param_name, {})
            param_type = param_info.get("type", "input")

            if isinstance(control, wx.CheckBox):
                options[param_name] = control.GetValue()
            elif isinstance(control, wx.Choice):
                selection = control.GetSelection()
                if selection != wx.NOT_FOUND:
                    options[param_name] = control.GetString(selection)
            elif isinstance(control, wx.ListBox):
                items = []
                for i in range(control.GetCount()):
                    items.append(control.GetString(i))
                options[param_name] = items
            elif isinstance(control, wx.TextCtrl):
                value = control.GetValue().strip()
                if value:
                    # Convert to appropriate type
                    if param_type == "integer":
                        try:
                            options[param_name] = int(value)
                        except ValueError:
                            options[param_name] = value
                    else:
                        options[param_name] = value

        if "packaging" not in self.wizard.config:
            self.wizard.config["packaging"] = {}

        self.wizard.config["packaging"][f"{self.engine}_options"] = options


class PyInstallerOptionsPage(WizardPageBase):
    """PyInstaller-specific options page."""

    def __init__(self, parent):
        super().__init__(parent, "PyInstaller Options", 6, 9)

        # Hidden imports
        self.content_sizer.Add(
            wx.StaticText(self, label="Hidden Imports (comma-separated):"),
            0, wx.ALL, 5
        )
        self.hidden_imports_ctrl = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(-1, 60))
        self.hidden_imports_ctrl.SetToolTip(
            "Modules that PyInstaller can't detect automatically (e.g., 'sklearn.utils._typedefs')"
        )
        self.content_sizer.Add(self.hidden_imports_ctrl, 0, wx.EXPAND | wx.ALL, 5)

        # Additional data files
        self.content_sizer.Add(
            wx.StaticText(self, label="Additional Files/Directories:"),
            0, wx.ALL, 5
        )

        self.files_list = wx.ListBox(self, size=(-1, 100))
        self.content_sizer.Add(self.files_list, 0, wx.EXPAND | wx.ALL, 5)

        files_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        add_file_btn = wx.Button(self, label="Add File...")
        add_file_btn.Bind(wx.EVT_BUTTON, self.on_add_file)
        files_btn_sizer.Add(add_file_btn, 0, wx.RIGHT, 5)

        add_dir_btn = wx.Button(self, label="Add Directory...")
        add_dir_btn.Bind(wx.EVT_BUTTON, self.on_add_dir)
        files_btn_sizer.Add(add_dir_btn, 0, wx.RIGHT, 5)

        remove_btn = wx.Button(self, label="Remove")
        remove_btn.Bind(wx.EVT_BUTTON, self.on_remove_file)
        files_btn_sizer.Add(remove_btn, 0)

        self.content_sizer.Add(files_btn_sizer, 0, wx.ALL, 5)

        # Exclude modules
        self.content_sizer.Add(
            wx.StaticText(self, label="Exclude Modules (comma-separated):"),
            0, wx.ALL, 5
        )
        self.exclude_ctrl = wx.TextCtrl(self)
        self.exclude_ctrl.SetToolTip("Modules to exclude from the bundle")
        self.content_sizer.Add(self.exclude_ctrl, 0, wx.EXPAND | wx.ALL, 5)

        # Advanced options
        self.upx_check = wx.CheckBox(self, label="Use UPX compression (if available)")
        self.content_sizer.Add(self.upx_check, 0, wx.ALL, 5)

        self.strip_check = wx.CheckBox(self, label="Strip debug symbols")
        self.strip_check.SetValue(True)
        self.content_sizer.Add(self.strip_check, 0, wx.ALL, 5)

        self.noupx_check = wx.CheckBox(self, label="Disable UPX even if available")
        self.content_sizer.Add(self.noupx_check, 0, wx.ALL, 5)

    def load_existing_values(self):
        """Load existing values if editing."""
        if self.wizard.is_editing:
            pkg_config = self.wizard.config.get("packaging", {})

            hidden = pkg_config.get("hidden_imports", [])
            if isinstance(hidden, list):
                self.hidden_imports_ctrl.SetValue(", ".join(hidden))

            # Clear and reload files list
            self.files_list.Clear()
            files = pkg_config.get("additional_files", [])
            if isinstance(files, list):
                self.files_list.AppendItems(files)

            exclude = pkg_config.get("exclude_modules", [])
            if isinstance(exclude, list):
                self.exclude_ctrl.SetValue(", ".join(exclude))

            # Load checkbox values
            self.upx_check.SetValue(pkg_config.get("use_upx", False))
            self.strip_check.SetValue(pkg_config.get("strip", True))
            self.noupx_check.SetValue(pkg_config.get("no_upx", False))

    def on_add_file(self, event):
        """Add file to include."""
        with wx.FileDialog(
            self,
            "Select File to Include",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.files_list.Append(dialog.GetPath())

    def on_add_dir(self, event):
        """Add directory to include."""
        with wx.DirDialog(
            self,
            "Select Directory to Include",
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.files_list.Append(dialog.GetPath())

    def on_remove_file(self, event):
        """Remove selected file."""
        selection = self.files_list.GetSelection()
        if selection != wx.NOT_FOUND:
            self.files_list.Delete(selection)

    def save_data(self):
        """Save PyInstaller-specific options."""
        # Parse comma-separated lists
        hidden_imports = [
            s.strip() for s in self.hidden_imports_ctrl.GetValue().split(",")
            if s.strip()
        ]

        exclude_modules = [
            s.strip() for s in self.exclude_ctrl.GetValue().split(",")
            if s.strip()
        ]

        # Get additional files
        additional_files = []
        for i in range(self.files_list.GetCount()):
            additional_files.append(self.files_list.GetString(i))

        # Update config
        if "packaging" not in self.wizard.config:
            self.wizard.config["packaging"] = {}

        self.wizard.config["packaging"].update({
            "hidden_imports": hidden_imports,
            "exclude_modules": exclude_modules,
            "additional_files": additional_files,
            "use_upx": self.upx_check.GetValue(),
            "strip": self.strip_check.GetValue(),
            "no_upx": self.noupx_check.GetValue(),
        })


class NuitkaOptionsPage(WizardPageBase):
    """Nuitka-specific options page."""

    def __init__(self, parent):
        super().__init__(parent, "Nuitka Options", 6, 9)

        # Optimization level
        opt_sizer = wx.BoxSizer(wx.HORIZONTAL)
        opt_sizer.Add(wx.StaticText(self, label="Optimization Level:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.opt_choice = wx.Choice(
            self,
            choices=["Default", "Size", "Speed"]
        )
        self.opt_choice.SetSelection(0)
        opt_sizer.Add(self.opt_choice, 1)

        self.content_sizer.Add(opt_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Follow imports
        self.follow_imports_check = wx.CheckBox(self, label="Follow all imports")
        self.follow_imports_check.SetValue(True)
        self.content_sizer.Add(self.follow_imports_check, 0, wx.ALL, 5)

        # Enable console
        self.windows_console_check = wx.CheckBox(self, label="Enable Windows console")
        self.content_sizer.Add(self.windows_console_check, 0, wx.ALL, 5)

        # Company info
        self.content_sizer.Add(wx.StaticText(self, label="Company Name:"), 0, wx.ALL, 5)
        self.company_ctrl = wx.TextCtrl(self)
        self.content_sizer.Add(self.company_ctrl, 0, wx.EXPAND | wx.ALL, 5)

        # Product name
        self.content_sizer.Add(wx.StaticText(self, label="Product Name:"), 0, wx.ALL, 5)
        self.product_ctrl = wx.TextCtrl(self)
        self.content_sizer.Add(self.product_ctrl, 0, wx.EXPAND | wx.ALL, 5)

        # File version
        self.content_sizer.Add(wx.StaticText(self, label="File Version:"), 0, wx.ALL, 5)
        self.file_version_ctrl = wx.TextCtrl(self)
        self.content_sizer.Add(self.file_version_ctrl, 0, wx.EXPAND | wx.ALL, 5)

    def load_existing_values(self):
        """Load existing values if editing."""
        if self.wizard.is_editing:
            pkg_config = self.wizard.config.get("packaging", {})
            nuitka_config = pkg_config.get("nuitka_options", {})

            # Set optimization level
            opt = nuitka_config.get("optimization", "")
            if opt == "--optimize-size":
                self.opt_choice.SetSelection(1)
            elif opt == "--optimize-speed":
                self.opt_choice.SetSelection(2)
            else:
                self.opt_choice.SetSelection(0)

            self.follow_imports_check.SetValue(nuitka_config.get("follow_imports", True))
            self.windows_console_check.SetValue(nuitka_config.get("windows_console", False))
            self.company_ctrl.SetValue(nuitka_config.get("company_name", ""))
            self.product_ctrl.SetValue(nuitka_config.get("product_name", ""))
            self.file_version_ctrl.SetValue(nuitka_config.get("file_version", ""))

    def save_data(self):
        """Save Nuitka-specific options."""
        opt_levels = ["", "--optimize-size", "--optimize-speed"]

        if "packaging" not in self.wizard.config:
            self.wizard.config["packaging"] = {}

        self.wizard.config["packaging"]["nuitka_options"] = {
            "optimization": opt_levels[self.opt_choice.GetSelection()],
            "follow_imports": self.follow_imports_check.GetValue(),
            "windows_console": self.windows_console_check.GetValue(),
            "company_name": self.company_ctrl.GetValue().strip(),
            "product_name": self.product_ctrl.GetValue().strip(),
            "file_version": self.file_version_ctrl.GetValue().strip(),
        }


class CxFreezeOptionsPage(WizardPageBase):
    """cx_Freeze-specific options page."""

    def __init__(self, parent):
        super().__init__(parent, "cx_Freeze Options", 6, 9)

        # Build directory
        self.content_sizer.Add(wx.StaticText(self, label="Build Directory:"), 0, wx.ALL, 5)
        self.build_dir_ctrl = wx.TextCtrl(self, value="build")
        self.content_sizer.Add(self.build_dir_ctrl, 0, wx.EXPAND | wx.ALL, 5)

        # Packages to include
        self.content_sizer.Add(
            wx.StaticText(self, label="Include Packages (comma-separated):"),
            0, wx.ALL, 5
        )
        self.packages_ctrl = wx.TextCtrl(self)
        self.packages_ctrl.SetToolTip("Additional packages to include")
        self.content_sizer.Add(self.packages_ctrl, 0, wx.EXPAND | wx.ALL, 5)

        # Modules to exclude
        self.content_sizer.Add(
            wx.StaticText(self, label="Exclude Modules (comma-separated):"),
            0, wx.ALL, 5
        )
        self.excludes_ctrl = wx.TextCtrl(self)
        self.content_sizer.Add(self.excludes_ctrl, 0, wx.EXPAND | wx.ALL, 5)

        # Include files
        self.content_sizer.Add(wx.StaticText(self, label="Include Files:"), 0, wx.ALL, 5)

        self.include_files_list = wx.ListBox(self, size=(-1, 100))
        self.content_sizer.Add(self.include_files_list, 0, wx.EXPAND | wx.ALL, 5)

        files_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        add_btn = wx.Button(self, label="Add...")
        add_btn.Bind(wx.EVT_BUTTON, self.on_add_file)
        files_btn_sizer.Add(add_btn, 0, wx.RIGHT, 5)

        remove_btn = wx.Button(self, label="Remove")
        remove_btn.Bind(wx.EVT_BUTTON, self.on_remove_file)
        files_btn_sizer.Add(remove_btn, 0)

        self.content_sizer.Add(files_btn_sizer, 0, wx.ALL, 5)

        # Options
        self.compress_check = wx.CheckBox(self, label="Compress")
        self.compress_check.SetValue(True)
        self.content_sizer.Add(self.compress_check, 0, wx.ALL, 5)

        self.optimize_check = wx.CheckBox(self, label="Optimize bytecode")
        self.optimize_check.SetValue(True)
        self.content_sizer.Add(self.optimize_check, 0, wx.ALL, 5)

    def load_existing_values(self):
        """Load existing values if editing."""
        if self.wizard.is_editing:
            pkg_config = self.wizard.config.get("packaging", {})
            cx_config = pkg_config.get("cxfreeze_options", {})

            self.build_dir_ctrl.SetValue(cx_config.get("build_dir", "build"))

            packages = cx_config.get("packages", [])
            if isinstance(packages, list):
                self.packages_ctrl.SetValue(", ".join(packages))

            excludes = cx_config.get("excludes", [])
            if isinstance(excludes, list):
                self.excludes_ctrl.SetValue(", ".join(excludes))

            # Clear and reload include files list
            self.include_files_list.Clear()
            include_files = cx_config.get("include_files", [])
            if isinstance(include_files, list):
                self.include_files_list.AppendItems(include_files)

            self.compress_check.SetValue(cx_config.get("compress", True))
            self.optimize_check.SetValue(cx_config.get("optimize", True))

    def on_add_file(self, event):
        """Add file to include."""
        with wx.FileDialog(
            self,
            "Select File to Include",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.include_files_list.Append(dialog.GetPath())

    def on_remove_file(self, event):
        """Remove selected file."""
        selection = self.include_files_list.GetSelection()
        if selection != wx.NOT_FOUND:
            self.include_files_list.Delete(selection)

    def save_data(self):
        """Save cx_Freeze-specific options."""
        packages = [
            s.strip() for s in self.packages_ctrl.GetValue().split(",")
            if s.strip()
        ]

        excludes = [
            s.strip() for s in self.excludes_ctrl.GetValue().split(",")
            if s.strip()
        ]

        include_files = []
        for i in range(self.include_files_list.GetCount()):
            include_files.append(self.include_files_list.GetString(i))

        if "packaging" not in self.wizard.config:
            self.wizard.config["packaging"] = {}

        self.wizard.config["packaging"]["cxfreeze_options"] = {
            "build_dir": self.build_dir_ctrl.GetValue().strip(),
            "packages": packages,
            "excludes": excludes,
            "include_files": include_files,
            "compress": self.compress_check.GetValue(),
            "optimize": self.optimize_check.GetValue(),
        }


class SecurityPage(WizardPageBase):
    """ security configuration page."""

    def __init__(self, parent):
        super().__init__(parent, "Security Configuration", 5, 7)

        # Signing
        signing_box = wx.StaticBox(self, label="Package Signing")
        signing_sizer = wx.StaticBoxSizer(signing_box, wx.VERTICAL)

        self.signing_check = wx.CheckBox(self, label="Enable package signing")
        self.signing_check.Bind(wx.EVT_CHECKBOX, self.on_signing_change)
        signing_sizer.Add(self.signing_check, 0, wx.ALL, 5)

        # Private key path
        key_sizer = wx.BoxSizer(wx.HORIZONTAL)
        key_sizer.Add(wx.StaticText(self, label="Private Key:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.key_ctrl = wx.TextCtrl(self)
        key_sizer.Add(self.key_ctrl, 1)

        browse_btn = wx.Button(self, label="Browse...")
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse_key)
        key_sizer.Add(browse_btn, 0, wx.LEFT, 5)

        generate_btn = wx.Button(self, label="Generate...")
        generate_btn.Bind(wx.EVT_BUTTON, self.on_generate_key)
        key_sizer.Add(generate_btn, 0, wx.LEFT, 5)

        signing_sizer.Add(key_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.content_sizer.Add(signing_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Verification
        verify_box = wx.StaticBox(self, label="Signature Verification")
        verify_sizer = wx.StaticBoxSizer(verify_box, wx.VERTICAL)

        self.strict_check = wx.CheckBox(self, label="Strict verification mode")
        self.strict_check.SetValue(True)
        self.strict_check.SetToolTip("Reject packages without valid signatures")
        verify_sizer.Add(self.strict_check, 0, wx.ALL, 5)

        self.content_sizer.Add(verify_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # SSL/TLS
        ssl_box = wx.StaticBox(self, label="SSL/TLS")
        ssl_sizer = wx.StaticBoxSizer(ssl_box, wx.VERTICAL)

        self.ssl_verify_check = wx.CheckBox(self, label="Verify SSL certificates")
        self.ssl_verify_check.SetValue(True)
        ssl_sizer.Add(self.ssl_verify_check, 0, wx.ALL, 5)

        self.content_sizer.Add(ssl_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Disable signing controls initially
        self.on_signing_change(None)

    def load_existing_values(self):
        """Load existing values if editing."""
        if self.wizard.is_editing:
            security_config = self.wizard.config.get("security", {})

            signing_config = security_config.get("signing", {})
            self.signing_check.SetValue(signing_config.get("enabled", False))
            self.key_ctrl.SetValue(signing_config.get("private_key_path", ""))

            verify_config = security_config.get("verification", {})
            self.strict_check.SetValue(verify_config.get("strict", True))

            ssl_config = security_config.get("ssl", {})
            self.ssl_verify_check.SetValue(ssl_config.get("verify", True))

            self.on_signing_change(None)

    def on_signing_change(self, event):
        """Handle signing checkbox change."""
        enabled = self.signing_check.GetValue()
        self.key_ctrl.Enable(enabled)
        for child in self.GetChildren():
            if isinstance(child, wx.Button) and child.GetLabel() in ["Browse...", "Generate..."]:
                child.Enable(enabled)

    def on_browse_key(self, event):
        """Browse for private key file."""
        with wx.FileDialog(
            self,
            "Select Private Key",
            wildcard="Key files (*.key)|*.key|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.key_ctrl.SetValue(dialog.GetPath())

    def on_generate_key(self, event):
        """Generate new keypair."""
        with wx.DirDialog(
            self,
            "Select Directory for Keys",
            style=wx.DD_DEFAULT_STYLE,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                key_dir = Path(dialog.GetPath())

                try:
                    from looma.security.signing import SigningManager

                    signer = SigningManager({})
                    private_key, public_key = signer.generate_keypair()

                    private_path = key_dir / "private.key"
                    public_path = key_dir / "public.key"

                    private_path.write_text(private_key)
                    public_path.write_text(public_key)

                    self.key_ctrl.SetValue(str(private_path))

                    wx.MessageBox(
                        f"Keypair generated:\n\nPrivate: {private_path}\nPublic: {public_path}\n\n"
                        "Keep the private key secure!",
                        "Keys Generated",
                        wx.OK | wx.ICON_INFORMATION
                    )
                except Exception as e:
                    wx.MessageBox(
                        f"Failed to generate keys: {e}",
                        "Error",
                        wx.OK | wx.ICON_ERROR
                    )

    def save_data(self):
        """Save security data."""
        self.wizard.config["security"] = {
            "signing": {
                "enabled": self.signing_check.GetValue(),
                "private_key_path": self.key_ctrl.GetValue().strip() if self.signing_check.GetValue() else "",
            },
            "verification": {
                "strict": self.strict_check.GetValue(),
            },
            "ssl": {
                "verify": self.ssl_verify_check.GetValue(),
            },
        }


class SourcePage(WizardPageBase):
    """ update source configuration page."""

    def __init__(self, parent):
        super().__init__(parent, "Update Source Configuration", 6, 7)

        # Enable updates
        self.enable_check = wx.CheckBox(self, label="Enable automatic updates")
        self.enable_check.SetValue(True)
        self.enable_check.Bind(wx.EVT_CHECKBOX, self.on_enable_change)
        self.content_sizer.Add(self.enable_check, 0, wx.ALL, 10)

        # Source type
        source_sizer = wx.BoxSizer(wx.HORIZONTAL)
        source_sizer.Add(wx.StaticText(self, label="Update Source: *"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.source_choice = wx.Choice(
            self,
            choices=["GitHub Releases", "GitLab Releases", "AWS S3", "Artifactory", "HTTP Server"]
        )
        self.source_choice.SetSelection(0)
        self.source_choice.Bind(wx.EVT_CHOICE, self.on_source_change)
        source_sizer.Add(self.source_choice, 1)

        self.content_sizer.Add(source_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Dynamic source configuration panel
        self.source_panel = wx.Panel(self)
        self.source_sizer = wx.BoxSizer(wx.VERTICAL)
        self.source_panel.SetSizer(self.source_sizer)
        self.content_sizer.Add(self.source_panel, 1, wx.EXPAND | wx.ALL, 5)

        # Update configuration
        self.content_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 10)

        # Update channel
        channel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        channel_sizer.Add(wx.StaticText(self, label="Update Channel:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.channel_choice = wx.Choice(
            self,
            choices=["stable", "beta", "alpha", "nightly"]
        )
        self.channel_choice.SetSelection(0)
        channel_sizer.Add(self.channel_choice, 1)

        self.content_sizer.Add(channel_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Update strategy
        strategy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        strategy_sizer.Add(wx.StaticText(self, label="Update Strategy:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.strategy_choice = wx.Choice(
            self,
            choices=["Prompt User", "Silent Update", "Force Update"]
        )
        self.strategy_choice.SetSelection(0)
        strategy_sizer.Add(self.strategy_choice, 1)

        self.content_sizer.Add(strategy_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Check interval
        interval_sizer = wx.BoxSizer(wx.HORIZONTAL)
        interval_sizer.Add(wx.StaticText(self, label="Check Interval (hours):"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.interval_ctrl = wx.SpinCtrl(self, min=1, max=720, initial=24)
        interval_sizer.Add(self.interval_ctrl, 1)

        self.content_sizer.Add(interval_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Initialize source panel
        self.create_github_panel()

    def load_existing_values(self):
        """Load existing values if editing."""
        if self.wizard.is_editing:
            update_config = self.wizard.config.get("update", {})
            self.enable_check.SetValue(update_config.get("enabled", True))

            source_type = update_config.get("source", {}).get("type", "github")
            source_types = ["github", "gitlab", "s3", "artifactory", "http"]
            if source_type in source_types:
                self.source_choice.SetSelection(source_types.index(source_type))
                self.on_source_change(None)

            channel = update_config.get("channel", "stable")
            channels = ["stable", "beta", "alpha", "nightly"]
            if channel in channels:
                self.channel_choice.SetSelection(channels.index(channel))

            strategy = update_config.get("strategy", "prompt")
            strategies = ["prompt", "silent", "force"]
            if strategy in strategies:
                self.strategy_choice.SetSelection(strategies.index(strategy))

            interval = update_config.get("check_interval", 86400)
            self.interval_ctrl.SetValue(interval // 3600)

            # Trigger enable/disable state
            self.on_enable_change(None)

    def on_enable_change(self, event):
        """Handle enable checkbox change."""
        enabled = self.enable_check.GetValue()
        for child in self.GetChildren():
            if child != self.enable_check:
                child.Enable(enabled)

    def on_source_change(self, event):
        """Handle source type change."""
        # Clear current panel
        for child in self.source_panel.GetChildren():
            child.Destroy()

        # Create appropriate panel
        selection = self.source_choice.GetSelection()
        if selection == 0:
            self.create_github_panel()
        elif selection == 1:
            self.create_gitlab_panel()
        elif selection == 2:
            self.create_s3_panel()
        elif selection == 3:
            self.create_artifactory_panel()
        elif selection == 4:
            self.create_http_panel()

        self.source_panel.Layout()
        self.Layout()

    def create_github_panel(self):
        """Create GitHub configuration panel."""
        self.source_sizer.Clear(True)

        # Repository
        repo_sizer = wx.BoxSizer(wx.HORIZONTAL)
        repo_sizer.Add(wx.StaticText(self.source_panel, label="Repository: *"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.github_repo_ctrl = wx.TextCtrl(self.source_panel)
        self.github_repo_ctrl.SetToolTip("Format: owner/repository")
        repo_sizer.Add(self.github_repo_ctrl, 1)

        self.source_sizer.Add(repo_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Token (optional)
        token_sizer = wx.BoxSizer(wx.HORIZONTAL)
        token_sizer.Add(wx.StaticText(self.source_panel, label="Access Token:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.github_token_ctrl = wx.TextCtrl(self.source_panel, style=wx.TE_PASSWORD)
        self.github_token_ctrl.SetToolTip("Optional: For private repositories")
        token_sizer.Add(self.github_token_ctrl, 1)

        self.source_sizer.Add(token_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Load existing values
        if self.wizard.is_editing:
            source_config = self.wizard.config.get("update", {}).get("source", {})
            if source_config.get("type") == "github":
                self.github_repo_ctrl.SetValue(source_config.get("repo", ""))
                self.github_token_ctrl.SetValue(source_config.get("token", ""))

    def create_gitlab_panel(self):
        """Create GitLab configuration panel."""
        self.source_sizer.Clear(True)

        # Project ID
        project_sizer = wx.BoxSizer(wx.HORIZONTAL)
        project_sizer.Add(wx.StaticText(self.source_panel, label="Project ID: *"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.gitlab_project_ctrl = wx.TextCtrl(self.source_panel)
        project_sizer.Add(self.gitlab_project_ctrl, 1)

        self.source_sizer.Add(project_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # URL
        url_sizer = wx.BoxSizer(wx.HORIZONTAL)
        url_sizer.Add(wx.StaticText(self.source_panel, label="GitLab URL:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.gitlab_url_ctrl = wx.TextCtrl(self.source_panel, value="https://gitlab.com")
        url_sizer.Add(self.gitlab_url_ctrl, 1)

        self.source_sizer.Add(url_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Token
        token_sizer = wx.BoxSizer(wx.HORIZONTAL)
        token_sizer.Add(wx.StaticText(self.source_panel, label="Access Token: *"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.gitlab_token_ctrl = wx.TextCtrl(self.source_panel, style=wx.TE_PASSWORD)
        token_sizer.Add(self.gitlab_token_ctrl, 1)

        self.source_sizer.Add(token_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Load existing values
        if self.wizard.is_editing:
            source_config = self.wizard.config.get("update", {}).get("source", {})
            if source_config.get("type") == "gitlab":
                self.gitlab_project_ctrl.SetValue(str(source_config.get("project_id", "")))
                self.gitlab_url_ctrl.SetValue(source_config.get("url", "https://gitlab.com"))
                self.gitlab_token_ctrl.SetValue(source_config.get("token", ""))

    def create_s3_panel(self):
        """Create S3 configuration panel."""
        self.source_sizer.Clear(True)

        # Bucket
        bucket_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bucket_sizer.Add(wx.StaticText(self.source_panel, label="Bucket: *"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.s3_bucket_ctrl = wx.TextCtrl(self.source_panel)
        bucket_sizer.Add(self.s3_bucket_ctrl, 1)

        self.source_sizer.Add(bucket_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Region
        region_sizer = wx.BoxSizer(wx.HORIZONTAL)
        region_sizer.Add(wx.StaticText(self.source_panel, label="Region:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.s3_region_ctrl = wx.TextCtrl(self.source_panel, value="us-east-1")
        region_sizer.Add(self.s3_region_ctrl, 1)

        self.source_sizer.Add(region_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Prefix
        prefix_sizer = wx.BoxSizer(wx.HORIZONTAL)
        prefix_sizer.Add(wx.StaticText(self.source_panel, label="Prefix:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.s3_prefix_ctrl = wx.TextCtrl(self.source_panel)
        self.s3_prefix_ctrl.SetToolTip("Optional: S3 key prefix")
        prefix_sizer.Add(self.s3_prefix_ctrl, 1)

        self.source_sizer.Add(prefix_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Load existing values
        if self.wizard.is_editing:
            source_config = self.wizard.config.get("update", {}).get("source", {})
            if source_config.get("type") == "s3":
                self.s3_bucket_ctrl.SetValue(source_config.get("bucket", ""))
                self.s3_region_ctrl.SetValue(source_config.get("region", "us-east-1"))
                self.s3_prefix_ctrl.SetValue(source_config.get("prefix", ""))

    def create_artifactory_panel(self):
        """Create Artifactory configuration panel."""
        self.source_sizer.Clear(True)

        # URL
        url_sizer = wx.BoxSizer(wx.HORIZONTAL)
        url_sizer.Add(wx.StaticText(self.source_panel, label="URL: *"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.artifactory_url_ctrl = wx.TextCtrl(self.source_panel)
        url_sizer.Add(self.artifactory_url_ctrl, 1)

        self.source_sizer.Add(url_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Repository
        repo_sizer = wx.BoxSizer(wx.HORIZONTAL)
        repo_sizer.Add(wx.StaticText(self.source_panel, label="Repository: *"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.artifactory_repo_ctrl = wx.TextCtrl(self.source_panel)
        repo_sizer.Add(self.artifactory_repo_ctrl, 1)

        self.source_sizer.Add(repo_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # API Key
        key_sizer = wx.BoxSizer(wx.HORIZONTAL)
        key_sizer.Add(wx.StaticText(self.source_panel, label="API Key:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.artifactory_key_ctrl = wx.TextCtrl(self.source_panel, style=wx.TE_PASSWORD)
        key_sizer.Add(self.artifactory_key_ctrl, 1)

        self.source_sizer.Add(key_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Load existing values
        if self.wizard.is_editing:
            source_config = self.wizard.config.get("update", {}).get("source", {})
            if source_config.get("type") == "artifactory":
                self.artifactory_url_ctrl.SetValue(source_config.get("url", ""))
                self.artifactory_repo_ctrl.SetValue(source_config.get("repository", ""))
                self.artifactory_key_ctrl.SetValue(source_config.get("api_key", ""))

    def create_http_panel(self):
        """Create HTTP configuration panel."""
        self.source_sizer.Clear(True)

        # Base URL
        url_sizer = wx.BoxSizer(wx.HORIZONTAL)
        url_sizer.Add(wx.StaticText(self.source_panel, label="Base URL: *"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.http_url_ctrl = wx.TextCtrl(self.source_panel)
        url_sizer.Add(self.http_url_ctrl, 1)

        self.source_sizer.Add(url_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Endpoint
        endpoint_sizer = wx.BoxSizer(wx.HORIZONTAL)
        endpoint_sizer.Add(wx.StaticText(self.source_panel, label="Update Endpoint:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.http_endpoint_ctrl = wx.TextCtrl(self.source_panel, value="/updates")
        endpoint_sizer.Add(self.http_endpoint_ctrl, 1)

        self.source_sizer.Add(endpoint_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Auth token
        auth_sizer = wx.BoxSizer(wx.HORIZONTAL)
        auth_sizer.Add(wx.StaticText(self.source_panel, label="Auth Token:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.http_auth_ctrl = wx.TextCtrl(self.source_panel, style=wx.TE_PASSWORD)
        self.http_auth_ctrl.SetToolTip("Optional: Bearer token for authentication")
        auth_sizer.Add(self.http_auth_ctrl, 1)

        self.source_sizer.Add(auth_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Load existing values
        if self.wizard.is_editing:
            source_config = self.wizard.config.get("update", {}).get("source", {})
            if source_config.get("type") == "http":
                self.http_url_ctrl.SetValue(source_config.get("base_url", ""))
                self.http_endpoint_ctrl.SetValue(source_config.get("update_endpoint", "/updates"))
                self.http_auth_ctrl.SetValue(source_config.get("auth_token", ""))

    def validate(self) -> bool:
        """Validate source configuration."""
        if not self.enable_check.GetValue():
            return True

        selection = self.source_choice.GetSelection()

        if selection == 0:  # GitHub
            if not hasattr(self, 'github_repo_ctrl') or not self.github_repo_ctrl.GetValue().strip():
                wx.MessageBox("GitHub repository is required", "Validation Error", wx.OK | wx.ICON_ERROR)
                return False
            if "/" not in self.github_repo_ctrl.GetValue():
                wx.MessageBox("Repository format should be: owner/repository", "Validation Error", wx.OK | wx.ICON_ERROR)
                return False

        elif selection == 1:  # GitLab
            if not hasattr(self, 'gitlab_project_ctrl') or not self.gitlab_project_ctrl.GetValue().strip():
                wx.MessageBox("GitLab project ID is required", "Validation Error", wx.OK | wx.ICON_ERROR)
                return False
            if not hasattr(self, 'gitlab_token_ctrl') or not self.gitlab_token_ctrl.GetValue().strip():
                wx.MessageBox("GitLab access token is required", "Validation Error", wx.OK | wx.ICON_ERROR)
                return False

        elif selection == 2:  # S3
            if not hasattr(self, 's3_bucket_ctrl') or not self.s3_bucket_ctrl.GetValue().strip():
                wx.MessageBox("S3 bucket is required", "Validation Error", wx.OK | wx.ICON_ERROR)
                return False

        elif selection == 3:  # Artifactory
            if not hasattr(self, 'artifactory_url_ctrl') or not self.artifactory_url_ctrl.GetValue().strip():
                wx.MessageBox("Artifactory URL is required", "Validation Error", wx.OK | wx.ICON_ERROR)
                return False
            if not hasattr(self, 'artifactory_repo_ctrl') or not self.artifactory_repo_ctrl.GetValue().strip():
                wx.MessageBox("Artifactory repository is required", "Validation Error", wx.OK | wx.ICON_ERROR)
                return False

        elif selection == 4:  # HTTP
            if not hasattr(self, 'http_url_ctrl') or not self.http_url_ctrl.GetValue().strip():
                wx.MessageBox("HTTP base URL is required", "Validation Error", wx.OK | wx.ICON_ERROR)
                return False

        return True

    def save_data(self):
        """Save update source data."""
        source_types = ["github", "gitlab", "s3", "artifactory", "http"]
        source_type = source_types[self.source_choice.GetSelection()]

        source_config = {"type": source_type}

        if source_type == "github":
            if hasattr(self, 'github_repo_ctrl'):
                source_config["repo"] = self.github_repo_ctrl.GetValue().strip()
                token = self.github_token_ctrl.GetValue().strip()
                if token:
                    source_config["token"] = token

        elif source_type == "gitlab":
            if hasattr(self, 'gitlab_project_ctrl'):
                source_config["project_id"] = self.gitlab_project_ctrl.GetValue().strip()
                source_config["url"] = self.gitlab_url_ctrl.GetValue().strip()
                source_config["token"] = self.gitlab_token_ctrl.GetValue().strip()

        elif source_type == "s3":
            if hasattr(self, 's3_bucket_ctrl'):
                source_config["bucket"] = self.s3_bucket_ctrl.GetValue().strip()
                source_config["region"] = self.s3_region_ctrl.GetValue().strip()
                prefix = self.s3_prefix_ctrl.GetValue().strip()
                if prefix:
                    source_config["prefix"] = prefix

        elif source_type == "artifactory":
            if hasattr(self, 'artifactory_url_ctrl'):
                source_config["url"] = self.artifactory_url_ctrl.GetValue().strip()
                source_config["repository"] = self.artifactory_repo_ctrl.GetValue().strip()
                api_key = self.artifactory_key_ctrl.GetValue().strip()
                if api_key:
                    source_config["api_key"] = api_key

        elif source_type == "http":
            if hasattr(self, 'http_url_ctrl'):
                source_config["base_url"] = self.http_url_ctrl.GetValue().strip()
                source_config["update_endpoint"] = self.http_endpoint_ctrl.GetValue().strip()
                auth = self.http_auth_ctrl.GetValue().strip()
                if auth:
                    source_config["auth_token"] = auth

        strategies = ["prompt", "silent", "force"]
        channels = ["stable", "beta", "alpha", "nightly"]

        self.wizard.config["update"] = {
            "enabled": self.enable_check.GetValue(),
            "source": source_config,
            "channel": channels[self.channel_choice.GetSelection()],
            "strategy": strategies[self.strategy_choice.GetSelection()],
            "check_interval": self.interval_ctrl.GetValue() * 3600,
        }


class SummaryPage(WizardPageBase):
    """ summary page showing all configuration."""

    def __init__(self, parent):
        super().__init__(parent, "Configuration Summary", 7, 7)

        # Summary text
        self.summary_text = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(-1, 350)
        )
        self.content_sizer.Add(self.summary_text, 1, wx.EXPAND | wx.ALL, 10)

        # Save location
        self.location_text = wx.StaticText(self, label="")
        self.location_text.SetForegroundColour(wx.Colour(0, 128, 0))
        self.content_sizer.Add(self.location_text, 0, wx.ALL, 10)

    def update_progress(self):
        """Update summary when page is shown."""
        super().update_progress()

        # Generate summary (in YAML order)
        summary = []
        config = self.wizard.config

        summary.append("CONFIGURATION SUMMARY")
        summary.append("=" * 50)
        summary.append("")

        # Build settings (first in YAML)
        # Support both old 'advanced' and new 'build_settings' keys for backward compatibility
        build_settings_config = config.get("build_settings") or config.get("advanced", {})
        build_config = build_settings_config.get("build", {})
        log_config = build_settings_config.get("logging", {})

        summary.append("BUILD SETTINGS:")
        summary.append(f"  Output Directory: {build_config.get('output_dir', 'dist')}")
        summary.append(f"  Build Directory: {build_config.get('build_dir', 'build')}")
        summary.append(f"  Clean Build: {build_config.get('clean', True)}")
        summary.append(f"  Log Level: {log_config.get('level', 'INFO')}")
        if log_config.get('file'):
            summary.append(f"  Log File: {log_config.get('file', '')}")
        summary.append("")

        # Application
        app = config.get("app", {})
        summary.append("APPLICATION:")
        summary.append(f"  Name: {app.get('name', 'Not set')}")
        summary.append(f"  Version: {app.get('version', 'Not set')}")
        summary.append(f"  Author: {app.get('author', 'Not set')}")
        summary.append(f"  Email: {app.get('email', 'Not set')}")
        summary.append(f"  License: {app.get('license', 'MIT')}")
        summary.append("")

        # Packaging
        pkg = config.get("packaging", {})
        summary.append("PACKAGING:")
        summary.append(f"  Engine: {pkg.get('engine', 'pyinstaller')}")
        summary.append(f"  Entry Point: {pkg.get('entry_point', 'Not set')}")
        summary.append(f"  Single File: {pkg.get('one_file', True)}")
        summary.append(f"  Console: {pkg.get('console', False)}")

        # Engine-specific
        if pkg.get("engine") == "pyinstaller":
            if pkg.get("hidden_imports"):
                summary.append(f"  Hidden Imports: {len(pkg.get('hidden_imports', []))} modules")
            if pkg.get("additional_files"):
                summary.append(f"  Additional Files: {len(pkg.get('additional_files', []))} items")
        summary.append("")

        # Security
        security = config.get("security", {})
        summary.append("SECURITY:")
        summary.append(f"  Signing Enabled: {security.get('signing', {}).get('enabled', False)}")
        summary.append(f"  Strict Verification: {security.get('verification', {}).get('strict', True)}")
        summary.append(f"  SSL Verification: {security.get('ssl', {}).get('verify', True)}")
        summary.append("")

        # Update source
        update = config.get("update", {})
        summary.append("UPDATE CONFIGURATION:")
        summary.append(f"  Enabled: {update.get('enabled', True)}")

        if update.get("enabled"):
            source = update.get("source", {})
            summary.append(f"  Source: {source.get('type', 'github')}")

            if source.get("type") == "github":
                summary.append(f"  Repository: {source.get('repo', 'Not set')}")
            elif source.get("type") == "gitlab":
                summary.append(f"  Project ID: {source.get('project_id', 'Not set')}")
            elif source.get("type") == "s3":
                summary.append(f"  Bucket: {source.get('bucket', 'Not set')}")

            summary.append(f"  Channel: {update.get('channel', 'stable')}")
            summary.append(f"  Strategy: {update.get('strategy', 'prompt')}")
        summary.append("")

        # Set summary text
        self.summary_text.SetValue("\n".join(summary))

        # Set location text
        self.location_text.SetLabel(f"Configuration will be saved to: {self.wizard.config_path}")
