"""Main wxPython application for Looma GUI."""

import sys
from pathlib import Path
from typing import Optional

import wx
import wx.adv
import wx.lib.newevent

from looma.core.config import ConfigManager
from looma.core.constants import UI_MIN_HEIGHT, UI_MIN_WIDTH, UI_WINDOW_HEIGHT, UI_WINDOW_WIDTH
from looma.gui.editor import ConfigEditor
from looma.gui.wizard import ConfigWizard
from looma.gui.initial_dialog import InitialChoiceDialog

# Custom events
BuildEvent, EVT_BUILD = wx.lib.newevent.NewEvent()
ValidateEvent, EVT_VALIDATE = wx.lib.newevent.NewEvent()


class LoomaApp(wx.App):
    """
    Main wxPython application for Looma GUI.

    Attributes
    ----------
    config_path : Optional[Path]
        Path to configuration file
    wizard_mode : bool
        Start in wizard mode
    """

    def __init__(self, config_path: Optional[Path] = None, wizard_mode: bool = False):
        """
        Initialize Looma GUI application.

        Parameters
        ----------
        config_path : Optional[Path]
            Configuration file path
        wizard_mode : bool
            Start in wizard mode
        """
        self.config_path = config_path
        self.wizard_mode = wizard_mode
        super().__init__()

    def OnInit(self) -> bool:
        """
        Initialize application.

        Returns
        -------
        bool
            True if initialization successful
        """
        # Set application name
        self.SetAppName("Looma")
        self.SetAppDisplayName("Looma Configuration Tool")

        # Show initial choice dialog if no config path specified
        if not self.config_path and not self.wizard_mode:
            dialog = InitialChoiceDialog()
            result = dialog.ShowModal()

            if result == wx.ID_OK:
                choice, config_path = dialog.get_choice()

                if choice == 'new':
                    # Start wizard for new configuration with the selected path
                    self.config_path = config_path
                    dialog.Destroy()
                    self.show_wizard(new_config=True)
                elif choice == 'edit':
                    # Open main window with selected configuration
                    self.config_path = config_path
                    dialog.Destroy()
                    self.show_main_window()
                else:
                    dialog.Destroy()
                    return False
            else:
                dialog.Destroy()
                return False
        elif self.wizard_mode:
            self.show_wizard()
        else:
            self.show_main_window()

        return True

    def show_wizard(self, new_config=False):
        """Show configuration wizard.

        Parameters
        ----------
        new_config : bool
            True if creating new configuration, False if editing existing
        """
        wizard = ConfigWizard(None, self.config_path)

        if wizard.RunWizard(wizard.GetFirstPage()):
            # Wizard completed successfully
            config_path = wizard.config_path

            if config_path:
                # Open main window with new configuration
                self.config_path = config_path
                wizard.Destroy()
                self.show_main_window()
        else:
            wizard.Destroy()
            if new_config:
                # If creating new config was cancelled, show initial dialog again
                self.OnInit()

    def show_main_window(self):
        """Show main application window."""
        frame = MainFrame(self.config_path)
        frame.Show()
        self.SetTopWindow(frame)


class MainFrame(wx.Frame):
    """
    Main application frame.

    Attributes
    ----------
    config_manager : ConfigManager
        Configuration manager
    config_editor : ConfigEditor
        Configuration editor panel
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize main frame.

        Parameters
        ----------
        config_path : Optional[Path]
            Configuration file path
        """
        super().__init__(
            None,
            title="Looma Configuration Tool",
            size=(UI_WINDOW_WIDTH, UI_WINDOW_HEIGHT),
        )

        # Set minimum size
        self.SetMinSize((UI_MIN_WIDTH, UI_MIN_HEIGHT))

        # Load configuration
        self.config_path = config_path or Path("looma.yml")
        self.config_manager = ConfigManager(self.config_path)

        # Try to load existing configuration
        self.config = {}
        if self.config_path.exists():
            try:
                self.config = self.config_manager.load()
            except Exception:
                # Will create new configuration
                pass

        # Create UI
        self._create_ui()

        # Center window
        self.Centre()

    def _create_ui(self):
        """Create user interface."""
        # Create menu bar
        self._create_menu_bar()

        # Create toolbar
        self._create_toolbar()

        # Create status bar
        self.CreateStatusBar()
        self.SetStatusText("Ready")

        # Create main panel
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Add configuration editor
        self.config_editor = ConfigEditor(panel, self.config)
        sizer.Add(self.config_editor, 1, wx.EXPAND | wx.ALL, 5)

        # Add button panel
        button_panel = self._create_button_panel(panel)
        sizer.Add(button_panel, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(sizer)

        # Bind events
        self.Bind(EVT_BUILD, self.on_build)
        self.Bind(EVT_VALIDATE, self.on_validate)

    def _create_menu_bar(self):
        """Create menu bar."""
        menu_bar = wx.MenuBar()

        # File menu
        file_menu = wx.Menu()

        new_item = file_menu.Append(wx.ID_NEW, "&New\tCtrl+N", "Create new configuration")
        open_item = file_menu.Append(wx.ID_OPEN, "&Open\tCtrl+O", "Open configuration file")
        save_item = file_menu.Append(wx.ID_SAVE, "&Save\tCtrl+S", "Save configuration")
        save_as_item = file_menu.Append(wx.ID_SAVEAS, "Save &As...\tCtrl+Shift+S", "Save configuration as")

        file_menu.AppendSeparator()

        import_item = file_menu.Append(wx.ID_ANY, "&Import...", "Import configuration")
        export_item = file_menu.Append(wx.ID_ANY, "&Export...", "Export configuration")

        file_menu.AppendSeparator()

        exit_item = file_menu.Append(wx.ID_EXIT, "E&xit\tCtrl+Q", "Exit application")

        menu_bar.Append(file_menu, "&File")

        # Edit menu
        edit_menu = wx.Menu()

        undo_item = edit_menu.Append(wx.ID_UNDO, "&Undo\tCtrl+Z", "Undo last change")
        redo_item = edit_menu.Append(wx.ID_REDO, "&Redo\tCtrl+Y", "Redo last change")

        edit_menu.AppendSeparator()

        cut_item = edit_menu.Append(wx.ID_CUT, "Cu&t\tCtrl+X", "Cut selection")
        copy_item = edit_menu.Append(wx.ID_COPY, "&Copy\tCtrl+C", "Copy selection")
        paste_item = edit_menu.Append(wx.ID_PASTE, "&Paste\tCtrl+V", "Paste from clipboard")

        menu_bar.Append(edit_menu, "&Edit")

        # Tools menu
        tools_menu = wx.Menu()

        validate_item = tools_menu.Append(wx.ID_ANY, "&Validate\tF5", "Validate configuration")
        wizard_item = tools_menu.Append(wx.ID_ANY, "&Configuration Wizard...", "Open configuration wizard")

        tools_menu.AppendSeparator()

        build_item = tools_menu.Append(wx.ID_ANY, "&Build Package\tF6", "Build application package")

        menu_bar.Append(tools_menu, "&Tools")

        # Help menu
        help_menu = wx.Menu()

        docs_item = help_menu.Append(wx.ID_HELP, "&Documentation\tF1", "Open documentation")
        help_menu.AppendSeparator()
        about_item = help_menu.Append(wx.ID_ABOUT, "&About", "About Looma")

        menu_bar.Append(help_menu, "&Help")

        self.SetMenuBar(menu_bar)

        # Bind menu events
        self.Bind(wx.EVT_MENU, self.on_new, new_item)
        self.Bind(wx.EVT_MENU, self.on_open, open_item)
        self.Bind(wx.EVT_MENU, self.on_save, save_item)
        self.Bind(wx.EVT_MENU, self.on_save_as, save_as_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.Bind(wx.EVT_MENU, self.on_validate, validate_item)
        self.Bind(wx.EVT_MENU, self.on_wizard, wizard_item)
        self.Bind(wx.EVT_MENU, self.on_build, build_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)

    def _create_toolbar(self):
        """Create toolbar."""
        toolbar = self.CreateToolBar(wx.TB_HORIZONTAL | wx.TB_FLAT)

        # Add toolbar buttons
        new_tool = toolbar.AddTool(
            wx.ID_NEW,
            "New",
            wx.ArtProvider.GetBitmap(wx.ART_NEW, wx.ART_TOOLBAR),
            "Create new configuration",
        )

        open_tool = toolbar.AddTool(
            wx.ID_OPEN,
            "Open",
            wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR),
            "Open configuration file",
        )

        save_tool = toolbar.AddTool(
            wx.ID_SAVE,
            "Save",
            wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR),
            "Save configuration",
        )

        toolbar.AddSeparator()

        validate_tool = toolbar.AddTool(
            wx.ID_ANY,
            "Validate",
            wx.ArtProvider.GetBitmap(wx.ART_TICK_MARK, wx.ART_TOOLBAR),
            "Validate configuration",
        )

        # Add Edit Configuration button
        edit_config_tool = toolbar.AddTool(
            wx.ID_ANY,
            "Edit Configuration",
            wx.ArtProvider.GetBitmap(wx.ART_CDROM, wx.ART_TOOLBAR),
            "Edit configuration with wizard",
        )

        build_tool = toolbar.AddTool(
            wx.ID_ANY,
            "Build",
            wx.ArtProvider.GetBitmap(wx.ART_EXECUTABLE_FILE, wx.ART_TOOLBAR),
            "Build package",
        )

        toolbar.Realize()

        # Bind toolbar events
        self.Bind(wx.EVT_TOOL, self.on_new, new_tool)
        self.Bind(wx.EVT_TOOL, self.on_open, open_tool)
        self.Bind(wx.EVT_TOOL, self.on_save, save_tool)
        self.Bind(wx.EVT_TOOL, self.on_validate, validate_tool)
        self.Bind(wx.EVT_TOOL, self.on_edit_with_wizard, edit_config_tool)
        self.Bind(wx.EVT_TOOL, self.on_build, build_tool)

    def _create_button_panel(self, parent):
        """
        Create button panel.

        Parameters
        ----------
        parent : wx.Window
            Parent window

        Returns
        -------
        wx.Panel
            Button panel
        """
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Add buttons
        save_btn = wx.Button(panel, label="Save")
        build_btn = wx.Button(panel, label="Build Package")

        # Bind events
        save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        build_btn.Bind(wx.EVT_BUTTON, self.on_build)

        # Add to sizer
        sizer.Add(save_btn, 0, wx.ALL, 5)
        sizer.AddStretchSpacer()
        sizer.Add(build_btn, 0, wx.ALL, 5)

        panel.SetSizer(sizer)
        return panel

    def on_new(self, event):
        """Handle new configuration."""
        # First ask where to save the new configuration
        with wx.FileDialog(
            self,
            "Save New Configuration As",
            wildcard="YAML files (*.yml;*.yaml)|*.yml;*.yaml|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            defaultFile="looma.yml"
        ) as file_dialog:
            if file_dialog.ShowModal() != wx.ID_OK:
                return

            new_path = Path(file_dialog.GetPath())
            # Ensure .yml extension
            if not new_path.suffix in ['.yml', '.yaml']:
                new_path = new_path.with_suffix('.yml')

        # Ask user if they want to use wizard or start blank
        dialog = wx.MessageDialog(
            self,
            "Would you like to use the Configuration Wizard to create a new configuration?",
            "New Configuration",
            wx.YES_NO | wx.ICON_QUESTION
        )

        result = dialog.ShowModal()
        dialog.Destroy()

        if result == wx.ID_YES:
            # Use wizard for new configuration
            wizard = ConfigWizard(self, new_path, load_existing=False)

            if wizard.RunWizard(wizard.GetFirstPage()):
                # Wizard completed, load the new configuration
                config_path = wizard.config_path
                if config_path and config_path.exists():
                    try:
                        self.config_manager = ConfigManager(config_path)
                        self.config = self.config_manager.load()
                        self.config_path = config_path
                        self.config_editor.set_config(self.config)
                        self.SetTitle(f"Looma Configuration Tool - {config_path.name}")
                        self.SetStatusText(f"New configuration created: {config_path}")
                    except Exception as e:
                        wx.MessageBox(
                            f"Failed to load new configuration:\n{e}",
                            "Error",
                            wx.OK | wx.ICON_ERROR,
                        )

            wizard.Destroy()
        else:
            # Create blank configuration at the specified path
            self.config = {}
            self.config_path = new_path
            self.config_manager = ConfigManager(self.config_path)

            # Save the empty configuration
            try:
                self.config_manager.save(self.config, self.config_path)
                self.config_editor.set_config(self.config)
                self.SetTitle(f"Looma Configuration Tool - {self.config_path.name}")
                self.SetStatusText(f"New blank configuration created: {self.config_path}")
            except Exception as e:
                wx.MessageBox(
                    f"Failed to create new configuration:\n{e}",
                    "Error",
                    wx.OK | wx.ICON_ERROR,
                )

    def on_open(self, event):
        """Handle open configuration."""
        wildcard = "YAML files (*.yml;*.yaml)|*.yml;*.yaml|All files (*.*)|*.*"

        with wx.FileDialog(
            self,
            "Open Configuration File",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                path = Path(dialog.GetPath())
                try:
                    self.config_manager = ConfigManager(path)
                    self.config = self.config_manager.load()
                    self.config_path = path
                    self.config_editor.set_config(self.config)
                    self.SetTitle(f"Looma Configuration Tool - {path.name}")
                    self.SetStatusText(f"Loaded: {path}")
                except Exception as e:
                    wx.MessageBox(
                        f"Failed to load configuration:\n{e}",
                        "Error",
                        wx.OK | wx.ICON_ERROR,
                    )

    def on_save(self, event):
        """Handle save configuration."""
        try:
            self.config = self.config_editor.get_config()
            self.config_manager.save(self.config, self.config_path)
            self.SetStatusText(f"Saved: {self.config_path}")
        except Exception as e:
            wx.MessageBox(
                f"Failed to save configuration:\n{e}",
                "Error",
                wx.OK | wx.ICON_ERROR,
            )

    def on_save_as(self, event):
        """Handle save configuration as."""
        wildcard = "YAML files (*.yml;*.yaml)|*.yml;*.yaml|All files (*.*)|*.*"

        with wx.FileDialog(
            self,
            "Save Configuration File",
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                path = Path(dialog.GetPath())
                try:
                    self.config = self.config_editor.get_config()
                    self.config_manager.save(self.config, path)
                    self.config_path = path
                    self.SetTitle(f"Looma Configuration Tool - {path.name}")
                    self.SetStatusText(f"Saved: {path}")
                except Exception as e:
                    wx.MessageBox(
                        f"Failed to save configuration:\n{e}",
                        "Error",
                        wx.OK | wx.ICON_ERROR,
                    )

    def on_validate(self, event):
        """Handle validate configuration."""
        try:
            self.config = self.config_editor.get_config()
            if self.config_manager.validate(self.config):
                wx.MessageBox(
                    "Configuration is valid!",
                    "Validation Successful",
                    wx.OK | wx.ICON_INFORMATION,
                )
                self.SetStatusText("Configuration validated successfully")
            else:
                wx.MessageBox(
                    "Configuration validation failed",
                    "Validation Error",
                    wx.OK | wx.ICON_ERROR,
                )
                self.SetStatusText("Configuration validation failed")
        except Exception as e:
            wx.MessageBox(
                f"Validation error:\n{e}",
                "Error",
                wx.OK | wx.ICON_ERROR,
            )

    def on_build(self, event):
        """Handle build package."""
        from looma.gui.build_dialog import BuildDialog

        dialog = BuildDialog(self, self.config)
        dialog.ShowModal()
        dialog.Destroy()

    def on_wizard(self, event):
        """Handle configuration wizard."""
        wizard = ConfigWizard(self, self.config_path, load_existing=True)

        if wizard.RunWizard(wizard.GetFirstPage()):
            # Wizard completed, reload configuration
            config_path = wizard.config_path
            if config_path and config_path.exists():
                try:
                    self.config_manager = ConfigManager(config_path)
                    self.config = self.config_manager.load()
                    self.config_path = config_path
                    self.config_editor.set_config(self.config)
                    self.SetTitle(f"Looma Configuration Tool - {config_path.name}")
                    self.SetStatusText(f"Configuration updated via wizard")
                except Exception as e:
                    wx.MessageBox(
                        f"Failed to load wizard configuration:\n{e}",
                        "Error",
                        wx.OK | wx.ICON_ERROR,
                    )

        wizard.Destroy()

    def on_edit_with_wizard(self, event):
        """Handle edit configuration with wizard button."""
        # Save current config first if modified
        try:
            self.config = self.config_editor.get_config()
            self.config_manager.save(self.config, self.config_path)
        except Exception:
            # Ignore save errors, user may want to fix in wizard
            pass

        # Open wizard with current configuration
        wizard = ConfigWizard(self, self.config_path, load_existing=True)

        if wizard.RunWizard(wizard.GetFirstPage()):
            # Wizard completed, reload configuration
            config_path = wizard.config_path
            if config_path and config_path.exists():
                try:
                    self.config_manager = ConfigManager(config_path)
                    self.config = self.config_manager.load()
                    self.config_path = config_path
                    self.config_editor.set_config(self.config)
                    self.SetTitle(f"Looma Configuration Tool - {config_path.name}")
                    self.SetStatusText(f"Configuration updated via wizard")
                except Exception as e:
                    wx.MessageBox(
                        f"Failed to load wizard configuration:\n{e}",
                        "Error",
                        wx.OK | wx.ICON_ERROR,
                    )

        wizard.Destroy()

    def on_about(self, event):
        """Handle about dialog."""
        info = wx.adv.AboutDialogInfo()
        info.SetName("Looma")
        info.SetVersion("1.0.0")
        info.SetDescription("A comprehensive Python packaging and auto-update platform")
        info.SetCopyright("(C) 2025 Looma Team")
        info.SetWebSite("https://looma.dev")
        info.SetLicense("MIT License")

        wx.adv.AboutBox(info)

    def on_exit(self, event):
        """Handle exit application."""
        self.Close(True)
