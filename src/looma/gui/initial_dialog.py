"""Initial dialog for choosing between creating new or editing existing configuration."""

import wx
from pathlib import Path
from typing import Optional, Tuple


class InitialChoiceDialog(wx.Dialog):
    """Dialog for initial choice between creating new or editing existing configuration."""
    
    def __init__(self, parent=None):
        """Initialize the initial choice dialog."""
        super().__init__(
            parent,
            title="Looma Configuration Tool",
            size=(500, 400),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        
        self.choice = None  # 'new', 'edit', or None (cancelled)
        self.config_path = None
        
        self._create_ui()
        self.Centre()
        self.SetMinSize((450, 350))
    
    def _create_ui(self):
        """Create the user interface."""
        # Main panel to avoid GTK warnings
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title area
        title_text = wx.StaticText(panel, label="Welcome to Looma")
        title_font = wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title_text.SetFont(title_font)
        main_sizer.Add(title_text, 0, wx.ALIGN_CENTER | wx.TOP, 30)
        
        subtitle_text = wx.StaticText(panel, label="Python Application Packaging & Auto-Update Platform")
        subtitle_font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL)
        subtitle_text.SetFont(subtitle_font)
        subtitle_text.SetForegroundColour(wx.Colour(100, 100, 100))
        main_sizer.Add(subtitle_text, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        
        # Separator line
        line = wx.StaticLine(panel)
        main_sizer.Add(line, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        
        # Question text
        question_text = wx.StaticText(panel, label="What would you like to do?")
        question_font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        question_text.SetFont(question_font)
        main_sizer.Add(question_text, 0, wx.ALIGN_CENTER | wx.TOP, 30)
        
        # Button panel
        button_panel = wx.Panel(panel)
        button_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Create New Configuration button
        new_btn = wx.Button(button_panel, wx.ID_ANY, label="Create New Configuration", size=(300, 45))
        new_btn.SetToolTip("Start the configuration wizard to create a new Looma configuration")
        new_btn.Bind(wx.EVT_BUTTON, self.on_new_config)
        button_sizer.Add(new_btn, 0, wx.ALIGN_CENTER | wx.TOP, 20)
        
        # Edit Existing Configuration button
        edit_btn = wx.Button(button_panel, wx.ID_ANY, label="Edit Existing Configuration", size=(300, 45))
        edit_btn.SetToolTip("Open an existing Looma configuration file for editing")
        edit_btn.Bind(wx.EVT_BUTTON, self.on_edit_config)
        button_sizer.Add(edit_btn, 0, wx.ALIGN_CENTER | wx.TOP, 15)
        
        button_panel.SetSizer(button_sizer)
        main_sizer.Add(button_panel, 1, wx.EXPAND | wx.ALL, 10)
        
        # Bottom button bar
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()
        
        # Exit button
        exit_btn = wx.Button(panel, wx.ID_CANCEL, label="Exit")
        exit_btn.Bind(wx.EVT_BUTTON, self.on_exit)
        btn_sizer.Add(exit_btn, 0, wx.ALL, 10)
        
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.BOTTOM, 5)
        
        panel.SetSizer(main_sizer)
        
        # Create outer sizer for the dialog
        outer_sizer = wx.BoxSizer(wx.VERTICAL)
        outer_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(outer_sizer)
    
    def on_new_config(self, event):
        """Handle create new configuration button."""
        # Ask user where to save the new configuration
        with wx.FileDialog(
            self,
            "Save New Configuration As",
            wildcard="YAML files (*.yml;*.yaml)|*.yml;*.yaml|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            defaultFile="looma.yml"
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.config_path = Path(dialog.GetPath())
                # Ensure .yml extension
                if not self.config_path.suffix in ['.yml', '.yaml']:
                    self.config_path = self.config_path.with_suffix('.yml')
                self.choice = 'new'
                self.EndModal(wx.ID_OK)
    
    def on_edit_config(self, event):
        """Handle edit existing configuration button."""
        # Show file dialog to select configuration file
        with wx.FileDialog(
            self,
            "Select Configuration File",
            wildcard="Configuration files (*.yml;*.yaml;*.json;*.toml)|*.yml;*.yaml;*.json;*.toml|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.config_path = Path(dialog.GetPath())
                self.choice = 'edit'
                self.EndModal(wx.ID_OK)
    
    def on_exit(self, event):
        """Handle exit button."""
        self.choice = None
        self.EndModal(wx.ID_CANCEL)
    
    def get_choice(self) -> Tuple[Optional[str], Optional[Path]]:
        """
        Get the user's choice.
        
        Returns
        -------
        Tuple[Optional[str], Optional[Path]]
            Tuple of (choice, config_path) where choice is 'new', 'edit', or None
        """
        return self.choice, self.config_path