""" configuration wizard for Looma GUI with progress tracking and validation."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import wx
import wx.adv
import wx.lib.agw.aui as aui
from looma.core.config import ConfigManager
from looma.core.constants import DEFAULT_CONFIG_FILE


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
        self.config = self._initialize_config(load_existing)
        self.is_editing = False

        # Track pages for progress
        self.pages = []
        self.current_page_index = 0

        # Create  pages with validation
        self.file_selection_page = FileSelectionPage(self)
        self.welcome_page = WelcomePage(self)
        self.app_page = ApplicationPage(self)
        self.packaging_page = PackagingPage(self)
        self.pyinstaller_page = PyInstallerOptionsPage(self)
        self.nuitka_page = NuitkaOptionsPage(self)
        self.cxfreeze_page = CxFreezeOptionsPage(self)
        self.source_page = SourcePage(self)
        self.security_page = SecurityPage(self)
        self.advanced_page = AdvancedOptionsPage(self)
        self.summary_page = SummaryPage(self)

        # Store pages for progress tracking
        self.pages = [
            self.file_selection_page,
            self.welcome_page,
            self.app_page,
            self.packaging_page,
            # Engine-specific pages will be dynamically linked
            self.source_page,
            self.security_page,
            self.advanced_page,
            self.summary_page,
        ]

        # Chain pages (basic flow, engine pages will be inserted dynamically)
        wx.adv.WizardPageSimple.Chain(self.file_selection_page, self.welcome_page)
        wx.adv.WizardPageSimple.Chain(self.welcome_page, self.app_page)
        wx.adv.WizardPageSimple.Chain(self.app_page, self.packaging_page)
        # Dynamic chaining for engine-specific pages
        wx.adv.WizardPageSimple.Chain(self.packaging_page, self.source_page)
        wx.adv.WizardPageSimple.Chain(self.source_page, self.security_page)
        wx.adv.WizardPageSimple.Chain(self.security_page, self.advanced_page)
        wx.adv.WizardPageSimple.Chain(self.advanced_page, self.summary_page)

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
            "version": "1.0",
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
            "advanced": {
                "build": {
                    "output_dir": "dist",
                    "clean": True,
                },
                "logging": {
                    "level": "INFO",
                    "file": "",
                },
            },
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
        return self.file_selection_page

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

        # Handle dynamic page flow for packaging engines
        if event.GetPage() == self.packaging_page and event.GetDirection():
            self._setup_engine_page_flow()

    def _setup_engine_page_flow(self):
        """Dynamically set up page flow based on selected engine."""
        engine = self.config.get("packaging", {}).get("engine", "pyinstaller")

        # Unchain all engine pages first
        for page in [self.pyinstaller_page, self.nuitka_page, self.cxfreeze_page]:
            page.SetPrev(None)
            page.SetNext(None)

        # Chain the appropriate engine page
        if engine == "pyinstaller":
            wx.adv.WizardPageSimple.Chain(self.packaging_page, self.pyinstaller_page)
            wx.adv.WizardPageSimple.Chain(self.pyinstaller_page, self.source_page)
        elif engine == "nuitka":
            wx.adv.WizardPageSimple.Chain(self.packaging_page, self.nuitka_page)
            wx.adv.WizardPageSimple.Chain(self.nuitka_page, self.source_page)
        elif engine == "cxfreeze":
            wx.adv.WizardPageSimple.Chain(self.packaging_page, self.cxfreeze_page)
            wx.adv.WizardPageSimple.Chain(self.cxfreeze_page, self.source_page)

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

    def __init__(self, parent, title: str, step_number: int, total_steps: int):
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
            help_btn = wx.Button(self, label="?", size=(20, 20))
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
            help_btn = wx.Button(self, label="?", size=(20, 20))
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


class FileSelectionPage(WizardPageBase):
    """Page for selecting configuration file to create or edit."""

    def __init__(self, parent):
        super().__init__(parent, "Configuration File Selection", 1, 9)

        # Description
        desc = wx.StaticText(
            self,
            label="Choose whether to create a new configuration or edit an existing one."
        )
        desc.Wrap(600)
        self.content_sizer.Add(desc, 0, wx.ALL, 10)

        # Radio buttons for choice
        self.new_radio = wx.RadioButton(self, label="Create new configuration", style=wx.RB_GROUP)
        self.edit_radio = wx.RadioButton(self, label="Edit existing configuration")

        self.content_sizer.Add(self.new_radio, 0, wx.ALL, 10)
        self.content_sizer.Add(self.edit_radio, 0, wx.ALL, 10)

        # File path input
        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        path_sizer.Add(wx.StaticText(self, label="File path:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.path_ctrl = wx.TextCtrl(self, value=str(self.wizard.config_path))
        path_sizer.Add(self.path_ctrl, 1, wx.EXPAND)

        browse_btn = wx.Button(self, label="Browse...")
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        path_sizer.Add(browse_btn, 0, wx.LEFT, 10)

        self.content_sizer.Add(path_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Status text
        self.status_text = wx.StaticText(self, label="")
        self.content_sizer.Add(self.status_text, 0, wx.ALL, 10)

        # Bind events
        self.new_radio.Bind(wx.EVT_RADIOBUTTON, self.on_radio_change)
        self.edit_radio.Bind(wx.EVT_RADIOBUTTON, self.on_radio_change)
        self.path_ctrl.Bind(wx.EVT_TEXT, self.on_path_change)

        # Check initial state
        self.check_file_status()

    def on_radio_change(self, event):
        """Handle radio button change."""
        self.check_file_status()

    def on_path_change(self, event):
        """Handle path text change."""
        self.check_file_status()

    def check_file_status(self):
        """Check and display file status."""
        path = Path(self.path_ctrl.GetValue())

        if path.exists():
            self.status_text.SetLabel(f"✓ File exists: {path}")
            self.status_text.SetForegroundColour(wx.Colour(0, 128, 0))
            self.edit_radio.SetValue(True)
        else:
            self.status_text.SetLabel(f"File will be created: {path}")
            self.status_text.SetForegroundColour(wx.Colour(128, 128, 0))
            self.new_radio.SetValue(True)

    def on_browse(self, event):
        """Handle browse button click."""
        if self.edit_radio.GetValue():
            # Browse for existing file
            with wx.FileDialog(
                self,
                "Select Configuration File",
                wildcard="YAML files (*.yml;*.yaml)|*.yml;*.yaml|All files (*.*)|*.*",
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as dialog:
                if dialog.ShowModal() == wx.ID_OK:
                    self.path_ctrl.SetValue(dialog.GetPath())
        else:
            # Browse for new file location
            with wx.FileDialog(
                self,
                "Save Configuration File",
                wildcard="YAML files (*.yml;*.yaml)|*.yml;*.yaml",
                defaultFile="looma.yml",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            ) as dialog:
                if dialog.ShowModal() == wx.ID_OK:
                    self.path_ctrl.SetValue(dialog.GetPath())

    def save_data(self):
        """Save selected file path."""
        self.wizard.config_path = Path(self.path_ctrl.GetValue())

        # Load existing config if editing
        if self.edit_radio.GetValue() and self.wizard.config_path.exists():
            try:
                config_manager = ConfigManager(self.wizard.config_path)
                loaded_config = config_manager.load()
                self.wizard.config = self.wizard._merge_configs(self.wizard.config, loaded_config)
                self.wizard.is_editing = True
            except Exception:
                pass


class WelcomePage(WizardPageBase):
    """ welcome page with better introduction."""

    def __init__(self, parent):
        super().__init__(parent, "Welcome to Looma Configuration Wizard", 2, 9)

        # Welcome message
        welcome_text = wx.StaticText(
            self,
            label="This wizard will guide you through configuring your Looma packaging and auto-update settings.\n\n"
                  "The configuration process includes:\n"
                  "• Application information\n"
                  "• Packaging engine selection and customization\n"
                  "• Update source configuration\n"
                  "• Security settings\n"
                  "• Advanced options\n\n"
                  "Required fields are marked with an asterisk (*).\n"
                  "You can go back to previous steps at any time."
        )
        welcome_text.Wrap(600)
        self.content_sizer.Add(welcome_text, 0, wx.ALL, 10)

        # Mode indicator
        if self.wizard.is_editing:
            mode_text = wx.StaticText(
                self,
                label=f"Mode: Editing existing configuration\nFile: {self.wizard.config_path}"
            )
            mode_text.SetForegroundColour(wx.Colour(0, 0, 128))
        else:
            mode_text = wx.StaticText(
                self,
                label=f"Mode: Creating new configuration\nFile: {self.wizard.config_path}"
            )
            mode_text.SetForegroundColour(wx.Colour(0, 128, 0))

        self.content_sizer.Add(mode_text, 0, wx.ALL, 10)


class ApplicationPage(WizardPageBase):
    """ application information page with validation."""

    def __init__(self, parent):
        super().__init__(parent, "Application Information", 3, 9)

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

        # Load existing values if editing
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
        super().__init__(parent, "Packaging Configuration", 4, 9)

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

        # Note about engine-specific options
        note_text = wx.StaticText(
            self,
            label="Note: Engine-specific options will be configured in the next step."
        )
        note_text.SetForegroundColour(wx.Colour(0, 0, 128))
        note_font = wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL)
        note_text.SetFont(note_font)
        self.content_sizer.Add(note_text, 0, wx.ALL | wx.TOP, 10)

        # Load existing values if editing
        if self.wizard.is_editing:
            pkg_config = self.wizard.config.get("packaging", {})

            engine = pkg_config.get("engine", "pyinstaller")
            engines = ["pyinstaller", "nuitka", "cxfreeze"]
            if engine in engines:
                self.engine_choice.SetSelection(engines.index(engine))

            self.entry_ctrl.SetValue(pkg_config.get("entry_point", "main.py"))
            self.onefile_check.SetValue(pkg_config.get("one_file", True))
            self.console_check.SetValue(pkg_config.get("console", False))
            self.icon_ctrl.SetValue(pkg_config.get("icon", ""))

    def on_engine_change(self, event):
        """Handle engine selection change."""
        self.update_engine_description()

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

    def save_data(self):
        """Save packaging data."""
        engines = ["pyinstaller", "nuitka", "cxfreeze"]
        self.wizard.config["packaging"] = {
            "engine": engines[self.engine_choice.GetSelection()],
            "entry_point": self.entry_ctrl.GetValue().strip(),
            "one_file": self.onefile_check.GetValue(),
            "console": self.console_check.GetValue(),
            "icon": self.icon_ctrl.GetValue().strip(),
        }


class PyInstallerOptionsPage(WizardPageBase):
    """PyInstaller-specific options page."""

    def __init__(self, parent):
        super().__init__(parent, "PyInstaller Options", 5, 9)

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

        # Load existing values if editing
        if self.wizard.is_editing:
            pkg_config = self.wizard.config.get("packaging", {})

            hidden = pkg_config.get("hidden_imports", [])
            if isinstance(hidden, list):
                self.hidden_imports_ctrl.SetValue(", ".join(hidden))

            files = pkg_config.get("additional_files", [])
            if isinstance(files, list):
                self.files_list.AppendItems(files)

            exclude = pkg_config.get("exclude_modules", [])
            if isinstance(exclude, list):
                self.exclude_ctrl.SetValue(", ".join(exclude))

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
        super().__init__(parent, "Nuitka Options", 5, 9)

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

        # Load existing values if editing
        if self.wizard.is_editing:
            pkg_config = self.wizard.config.get("packaging", {})
            nuitka_config = pkg_config.get("nuitka_options", {})

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
        super().__init__(parent, "cx_Freeze Options", 5, 9)

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

        # Load existing values if editing
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


class SourcePage(WizardPageBase):
    """ update source configuration page."""

    def __init__(self, parent):
        super().__init__(parent, "Update Source Configuration", 6, 9)

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

        # Load existing values if editing
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


class SecurityPage(WizardPageBase):
    """ security configuration page."""

    def __init__(self, parent):
        super().__init__(parent, "Security Configuration", 7, 9)

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

        # Load existing values if editing
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


class AdvancedOptionsPage(WizardPageBase):
    """Advanced options configuration page."""

    def __init__(self, parent):
        super().__init__(parent, "Advanced Options", 8, 9)

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

        # Load existing values if editing
        if self.wizard.is_editing:
            advanced_config = self.wizard.config.get("advanced", {})

            build_config = advanced_config.get("build", {})
            self.output_ctrl.SetValue(build_config.get("output_dir", "dist"))
            self.clean_check.SetValue(build_config.get("clean", True))

            log_config = advanced_config.get("logging", {})
            level = log_config.get("level", "INFO")
            levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if level in levels:
                self.level_choice.SetSelection(levels.index(level))
            self.logfile_ctrl.SetValue(log_config.get("file", ""))

    def save_data(self):
        """Save advanced options."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        if "advanced" not in self.wizard.config:
            self.wizard.config["advanced"] = {}

        self.wizard.config["advanced"]["build"] = {
            "output_dir": self.output_ctrl.GetValue().strip() or "dist",
            "clean": self.clean_check.GetValue(),
        }

        self.wizard.config["advanced"]["logging"] = {
            "level": levels[self.level_choice.GetSelection()],
            "file": self.logfile_ctrl.GetValue().strip(),
        }


class SummaryPage(WizardPageBase):
    """ summary page showing all configuration."""

    def __init__(self, parent):
        super().__init__(parent, "Configuration Summary", 9, 9)

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

        # Generate summary
        summary = []
        config = self.wizard.config

        summary.append("CONFIGURATION SUMMARY")
        summary.append("=" * 50)
        summary.append("")

        # Application
        app = config.get("app", {})
        summary.append("APPLICATION:")
        summary.append(f"  Name: {app.get('name', 'Not set')}")
        summary.append(f"  Version: {app.get('version', 'Not set')}")
        summary.append(f"  Author: {app.get('author', 'Not set')}")
        summary.append(f"  Email: {app.get('email', 'Not set')}")
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

        # Security
        security = config.get("security", {})
        summary.append("SECURITY:")
        summary.append(f"  Signing Enabled: {security.get('signing', {}).get('enabled', False)}")
        summary.append(f"  Strict Verification: {security.get('verification', {}).get('strict', True)}")
        summary.append(f"  SSL Verification: {security.get('ssl', {}).get('verify', True)}")
        summary.append("")

        # Set summary text
        self.summary_text.SetValue("\n".join(summary))

        # Set location text
        self.location_text.SetLabel(f"Configuration will be saved to: {self.wizard.config_path}")

