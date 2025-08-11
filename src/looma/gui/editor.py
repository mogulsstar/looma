"""Configuration editor for Looma GUI."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import wx
import wx.lib.agw.aui as aui
import wx.stc as stc


class ConfigEditor(wx.Panel):
    """
    Configuration editor panel with syntax highlighting.
    
    Attributes
    ----------
    config : dict
        Configuration dictionary
    editor : wx.stc.StyledTextCtrl
        Syntax-highlighting editor
    tree : wx.TreeCtrl
        Configuration tree view
    """
    
    def __init__(self, parent, config: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration editor.
        
        Parameters
        ----------
        parent : wx.Window
            Parent window
        config : Optional[Dict[str, Any]]
            Initial configuration
        """
        super().__init__(parent)
        
        self.config = config or {}
        self.modified = False
        
        # Create UI
        self._create_ui()
        
        # Load configuration
        self.set_config(self.config)
    
    def _create_ui(self):
        """Create user interface."""
        # Main sizer
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Create splitter
        splitter = wx.SplitterWindow(self, style=wx.SP_3D | wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(200)
        
        # Left panel - Tree view
        left_panel = wx.Panel(splitter)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Tree control
        self.tree = wx.TreeCtrl(
            left_panel,
            style=(
                wx.TR_DEFAULT_STYLE |
                wx.TR_HAS_BUTTONS |
                wx.TR_LINES_AT_ROOT |
                wx.TR_SINGLE
            ),
        )
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_selection)
        
        left_sizer.Add(self.tree, 1, wx.EXPAND | wx.ALL, 5)
        left_panel.SetSizer(left_sizer)
        
        # Right panel - Editor
        right_panel = wx.Panel(splitter)
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Editor toolbar
        toolbar_panel = wx.Panel(right_panel)
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.format_btn = wx.Button(toolbar_panel, label="Format")
        self.format_btn.Bind(wx.EVT_BUTTON, self.on_format)
        
        self.validate_btn = wx.Button(toolbar_panel, label="Validate")
        self.validate_btn.Bind(wx.EVT_BUTTON, self.on_validate)
        
        toolbar_sizer.Add(self.format_btn, 0, wx.ALL, 2)
        toolbar_sizer.Add(self.validate_btn, 0, wx.ALL, 2)
        toolbar_sizer.AddStretchSpacer()
        
        toolbar_panel.SetSizer(toolbar_sizer)
        right_sizer.Add(toolbar_panel, 0, wx.EXPAND | wx.ALL, 5)
        
        # YAML editor with syntax highlighting
        self.editor = stc.StyledTextCtrl(right_panel)
        self._setup_editor()
        
        right_sizer.Add(self.editor, 1, wx.EXPAND | wx.ALL, 5)
        right_panel.SetSizer(right_sizer)
        
        # Set up splitter
        splitter.SplitVertically(left_panel, right_panel, 300)
        
        sizer.Add(splitter, 1, wx.EXPAND)
        self.SetSizer(sizer)
    
    def _setup_editor(self):
        """Set up syntax highlighting editor."""
        # Set lexer for YAML
        self.editor.SetLexer(stc.STC_LEX_YAML)
        
        # Set up styles
        self.editor.StyleSetSpec(stc.STC_STYLE_DEFAULT, "size:10,face:Consolas")
        self.editor.StyleClearAll()
        
        # YAML styles
        self.editor.StyleSetSpec(stc.STC_YAML_DEFAULT, "fore:#000000")
        self.editor.StyleSetSpec(stc.STC_YAML_KEY, "fore:#0000FF,bold")
        self.editor.StyleSetSpec(stc.STC_YAML_NUMBER, "fore:#FF0000")
        self.editor.StyleSetSpec(stc.STC_YAML_REFERENCE, "fore:#008080")
        self.editor.StyleSetSpec(stc.STC_YAML_DOCUMENT, "fore:#000000")
        self.editor.StyleSetSpec(stc.STC_YAML_TEXT, "fore:#008000")
        self.editor.StyleSetSpec(stc.STC_YAML_ERROR, "fore:#FF0000,back:#FFCCCC")
        self.editor.StyleSetSpec(stc.STC_YAML_OPERATOR, "fore:#800080")
        
        # Set up margins
        self.editor.SetMarginType(0, stc.STC_MARGIN_NUMBER)
        self.editor.SetMarginWidth(0, 40)
        self.editor.SetMarginLineNumbers(0, True)
        
        # Set up indentation
        self.editor.SetIndent(2)
        self.editor.SetUseTabs(False)
        self.editor.SetTabWidth(2)
        self.editor.SetIndentationGuides(True)
        
        # Enable code folding
        self.editor.SetProperty("fold", "1")
        self.editor.SetProperty("fold.comment", "1")
        self.editor.SetProperty("fold.compact", "0")
        
        self.editor.SetMarginType(1, stc.STC_MARGIN_SYMBOL)
        self.editor.SetMarginMask(1, stc.STC_MASK_FOLDERS)
        self.editor.SetMarginSensitive(1, True)
        self.editor.SetMarginWidth(1, 20)
        
        # Folding markers
        self.editor.MarkerDefine(
            stc.STC_MARKNUM_FOLDER,
            stc.STC_MARK_BOXPLUS,
            "white",
            "black",
        )
        self.editor.MarkerDefine(
            stc.STC_MARKNUM_FOLDEROPEN,
            stc.STC_MARK_BOXMINUS,
            "white",
            "black",
        )
        self.editor.MarkerDefine(
            stc.STC_MARKNUM_FOLDEREND,
            stc.STC_MARK_BOXPLUSCONNECTED,
            "white",
            "black",
        )
        self.editor.MarkerDefine(
            stc.STC_MARKNUM_FOLDEROPENMID,
            stc.STC_MARK_BOXMINUSCONNECTED,
            "white",
            "black",
        )
        self.editor.MarkerDefine(
            stc.STC_MARKNUM_FOLDERMIDTAIL,
            stc.STC_MARK_TCORNER,
            "white",
            "black",
        )
        self.editor.MarkerDefine(
            stc.STC_MARKNUM_FOLDERTAIL,
            stc.STC_MARK_LCORNER,
            "white",
            "black",
        )
        self.editor.MarkerDefine(
            stc.STC_MARKNUM_FOLDERSUB,
            stc.STC_MARK_VLINE,
            "white",
            "black",
        )
        
        # Bind events
        self.editor.Bind(stc.EVT_STC_CHANGE, self.on_text_change)
        self.editor.Bind(stc.EVT_STC_MARGINCLICK, self.on_margin_click)
    
    def set_config(self, config: Dict[str, Any]):
        """
        Set configuration to edit.
        
        Parameters
        ----------
        config : dict
            Configuration dictionary
        """
        import yaml
        
        self.config = config
        self.modified = False
        
        # Update editor
        try:
            yaml_text = yaml.dump(config, default_flow_style=False, sort_keys=False)
            self.editor.SetText(yaml_text)
            self.editor.EmptyUndoBuffer()
        except Exception as e:
            self.editor.SetText(f"# Error converting configuration:\n# {e}")
        
        # Update tree
        self._update_tree()
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration.
        
        Returns
        -------
        dict
            Configuration dictionary
        """
        import yaml
        
        try:
            yaml_text = self.editor.GetText()
            self.config = yaml.safe_load(yaml_text) or {}
        except Exception:
            # Return last valid configuration
            pass
        
        return self.config
    
    def _update_tree(self):
        """Update tree view with configuration."""
        self.tree.DeleteAllItems()
        
        if not self.config:
            return
        
        # Create root
        root = self.tree.AddRoot("Configuration")
        
        # Add sections
        self._add_tree_items(root, self.config)
        
        # Expand root
        self.tree.Expand(root)
    
    def _add_tree_items(self, parent, data):
        """
        Recursively add tree items.
        
        Parameters
        ----------
        parent : wx.TreeItemId
            Parent tree item
        data : dict or list or Any
            Data to add
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    item = self.tree.AppendItem(parent, str(key))
                    self._add_tree_items(item, value)
                else:
                    self.tree.AppendItem(parent, f"{key}: {value}")
        elif isinstance(data, list):
            for i, value in enumerate(data):
                if isinstance(value, (dict, list)):
                    item = self.tree.AppendItem(parent, f"[{i}]")
                    self._add_tree_items(item, value)
                else:
                    self.tree.AppendItem(parent, f"[{i}]: {value}")
    
    def on_tree_selection(self, event):
        """Handle tree selection change."""
        item = event.GetItem()
        if not item.IsOk():
            return
        
        # Get path to selected item
        path = []
        while item != self.tree.GetRootItem():
            text = self.tree.GetItemText(item)
            # Remove value part if present
            if ":" in text:
                text = text.split(":")[0].strip()
            path.insert(0, text)
            item = self.tree.GetItemParent(item)
        
        # Navigate to line in editor
        if path:
            self._navigate_to_path(path)
    
    def _navigate_to_path(self, path):
        """
        Navigate editor to configuration path.
        
        Parameters
        ----------
        path : list
            Path components
        """
        # Simple implementation - search for first key
        if path:
            search_text = f"{path[0]}:"
            pos = self.editor.FindText(0, self.editor.GetTextLength(), search_text)
            if pos >= 0:
                line = self.editor.LineFromPosition(pos)
                self.editor.GotoLine(line)
                self.editor.SetSelection(pos, pos + len(search_text))
    
    def on_text_change(self, event):
        """Handle text change in editor."""
        self.modified = True
        
        # Update tree after a delay
        wx.CallLater(500, self._update_tree_from_editor)
    
    def _update_tree_from_editor(self):
        """Update tree from editor content."""
        import yaml
        
        try:
            yaml_text = self.editor.GetText()
            config = yaml.safe_load(yaml_text) or {}
            if config != self.config:
                self.config = config
                self._update_tree()
        except Exception:
            # Invalid YAML, don't update tree
            pass
    
    def on_margin_click(self, event):
        """Handle margin click for code folding."""
        if event.GetMargin() == 1:
            line = self.editor.LineFromPosition(event.GetPosition())
            level = self.editor.GetFoldLevel(line)
            
            if level & stc.STC_FOLDLEVELHEADERFLAG:
                self.editor.ToggleFold(line)
    
    def on_format(self, event):
        """Handle format button click."""
        import yaml
        
        try:
            # Parse current text
            yaml_text = self.editor.GetText()
            config = yaml.safe_load(yaml_text) or {}
            
            # Format and set back
            formatted = yaml.dump(config, default_flow_style=False, sort_keys=False)
            self.editor.SetText(formatted)
            
            wx.MessageBox(
                "Configuration formatted successfully",
                "Format",
                wx.OK | wx.ICON_INFORMATION,
            )
        except Exception as e:
            wx.MessageBox(
                f"Failed to format configuration:\n{e}",
                "Format Error",
                wx.OK | wx.ICON_ERROR,
            )
    
    def on_validate(self, event):
        """Handle validate button click."""
        try:
            # Get current configuration
            config = self.get_config()
            
            # Validate using ConfigManager
            from looma.core.config import ConfigManager
            
            config_manager = ConfigManager()
            if config_manager.validate(config):
                wx.MessageBox(
                    "Configuration is valid!",
                    "Validation",
                    wx.OK | wx.ICON_INFORMATION,
                )
            else:
                wx.MessageBox(
                    "Configuration validation failed",
                    "Validation Error",
                    wx.OK | wx.ICON_ERROR,
                )
        except Exception as e:
            wx.MessageBox(
                f"Validation error:\n{e}",
                "Error",
                wx.OK | wx.ICON_ERROR,
            )
    
    def is_modified(self) -> bool:
        """
        Check if configuration has been modified.
        
        Returns
        -------
        bool
            True if modified
        """
        return self.modified
    
    def mark_saved(self):
        """Mark configuration as saved."""
        self.modified = False
        self.editor.SetSavePoint()