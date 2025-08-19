"""Advanced engine options dialog for dynamic configuration."""

from pathlib import Path
from typing import Dict, Any, Optional

import wx

from looma.packager.factory import packager_factory


class EngineOptionsDialog(wx.Dialog):
    """Dialog for configuring advanced engine-specific options."""

    def __init__(self, parent, engine: str, initial_options: Optional[Dict[str, Any]] = None):
        """
        Initialize the advanced options dialog.

        Parameters
        ----------
        parent : wx.Window
            Parent window
        engine : str
            Packaging engine name
        initial_options : Optional[Dict[str, Any]]
            Initial option values
        """
        super().__init__(
            parent,
            title=f"Advanced {engine.title()} Options",
            size=(700, 600),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )

        self.engine = engine
        self.controls = {}
        self.schema = {}
        self.options = initial_options or {}

        self._create_ui()
        self.Centre()
        self.SetMinSize((600, 400))

    def _create_ui(self):
        """Create the user interface."""
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Create scrolled panel for options
        scroll_panel = wx.ScrolledWindow(self)
        scroll_panel.SetScrollRate(0, 20)
        scroll_sizer = wx.BoxSizer(wx.VERTICAL)

        # Get parameter schema from the packager
        try:
            # Ensure the factory is initialized
            if not packager_factory.packagers:
                packager_factory._register_default_packagers()

            # Get the packager class
            packager_class = packager_factory.get_packager_class(self.engine)

            # Create a minimal config for initialization
            minimal_config = {
                "packaging": {"entry_point": "main.py"},
                "build": {"output_dir": "dist", "build_dir": "build"},
                "app": {"name": "app", "version": "1.0.0"}
            }
            packager = packager_class(minimal_config)
            self.schema = packager.get_parameters_schema()

            # Create controls for advanced options only
            self._create_advanced_controls(scroll_sizer, scroll_panel)

        except Exception as e:
            error_label = wx.StaticText(scroll_panel, label=f"Error loading options: {str(e)}")
            scroll_sizer.Add(error_label, 0, wx.ALL, 10)

        scroll_panel.SetSizer(scroll_sizer)
        main_sizer.Add(scroll_panel, 1, wx.EXPAND | wx.ALL, 10)

        # Create button bar
        btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(main_sizer)

    def _create_advanced_controls(self, sizer, parent):
        """Create controls for advanced options only."""
        # Filter out basic options that are handled in the main page
        basic_options = ["onefile", "onedir", "console", "windowed", "icon", "name",
                        "entry_point", "output_dir", "dist_dir", "one_file"]

        advanced_params = []
        for param_name, param_info in self.schema.items():
            if param_name not in basic_options:
                advanced_params.append((param_name, param_info))

        if not advanced_params:
            label = wx.StaticText(parent, label="No advanced options available for this engine.")
            sizer.Add(label, 0, wx.ALL, 10)
            return

        # Group parameters by category
        grouped_params = self._group_parameters(advanced_params)

        for category, params in grouped_params.items():
            # Create category section
            if category:
                box = wx.StaticBox(parent, label=category)
                box_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
            else:
                box_sizer = wx.BoxSizer(wx.VERTICAL)

            for param_name, param_info in params:
                self._create_control(box_sizer, param_name, param_info, parent)

            sizer.Add(box_sizer, 0, wx.EXPAND | wx.ALL, 5)

    def _group_parameters(self, params):
        """Group parameters by category."""
        groups = {
            "Imports and Modules": [],
            "Optimization": [],
            "Security": [],
            "Paths and Files": [],
            "Other": []
        }

        for param_name, param_info in params:
            if "import" in param_name or "module" in param_name:
                groups["Imports and Modules"].append((param_name, param_info))
            elif "optim" in param_name or "compress" in param_name or "strip" in param_name:
                groups["Optimization"].append((param_name, param_info))
            elif "sign" in param_name or "cert" in param_name:
                groups["Security"].append((param_name, param_info))
            elif "path" in param_name or "file" in param_name or "data" in param_name:
                groups["Paths and Files"].append((param_name, param_info))
            else:
                groups["Other"].append((param_name, param_info))

        # Remove empty groups
        return {k: v for k, v in groups.items() if v}

    def _create_control(self, sizer, param_name, param_info, parent):
        """Create a single control based on parameter type."""
        param_type = param_info.get("type", "input")
        description = param_info.get("description", param_name)
        default = param_info.get("default", "")
        required = param_info.get("required", False)

        # Get initial value if exists
        initial_value = self.options.get(param_name, default)

        # Create label
        label_text = self._format_label(param_name)
        if required:
            label_text += " *"

        if param_type == "flag" or param_type == "boolean":
            # Create checkbox
            checkbox = wx.CheckBox(parent, label=label_text)
            checkbox.SetToolTip(description)
            checkbox.SetValue(bool(initial_value))
            self.controls[param_name] = checkbox
            sizer.Add(checkbox, 0, wx.ALL, 5)

        elif param_type == "list":
            # Create list control with add/remove buttons
            label = wx.StaticText(parent, label=label_text)
            label.SetToolTip(description)
            sizer.Add(label, 0, wx.ALL, 5)

            list_box = wx.ListBox(parent, size=(-1, 100))
            if isinstance(initial_value, list):
                list_box.AppendItems([str(item) for item in initial_value])
            self.controls[param_name] = list_box
            sizer.Add(list_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

            btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
            add_btn = wx.Button(parent, label="Add...", size=(80, -1))
            add_btn.Bind(wx.EVT_BUTTON, lambda e, pn=param_name, pi=param_info: self._on_add_list_item(e, pn, pi))
            btn_sizer.Add(add_btn, 0, wx.RIGHT, 5)

            remove_btn = wx.Button(parent, label="Remove", size=(80, -1))
            remove_btn.Bind(wx.EVT_BUTTON, lambda e, pn=param_name: self._on_remove_list_item(e, pn))
            btn_sizer.Add(remove_btn, 0)

            sizer.Add(btn_sizer, 0, wx.LEFT | wx.BOTTOM, 10)

        elif param_type == "choice":
            # Create choice control
            h_sizer = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(parent, label=label_text)
            label.SetToolTip(description)
            h_sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

            choices = param_info.get("choices", [])
            choice_ctrl = wx.Choice(parent, choices=choices)
            if initial_value in choices:
                choice_ctrl.SetSelection(choices.index(initial_value))
            self.controls[param_name] = choice_ctrl
            h_sizer.Add(choice_ctrl, 1)

            sizer.Add(h_sizer, 0, wx.EXPAND | wx.ALL, 5)

        elif param_type == "path":
            # Create text control with browse button
            label = wx.StaticText(parent, label=label_text)
            label.SetToolTip(description)
            sizer.Add(label, 0, wx.ALL, 5)

            h_sizer = wx.BoxSizer(wx.HORIZONTAL)
            text_ctrl = wx.TextCtrl(parent, value=str(initial_value))
            self.controls[param_name] = text_ctrl
            h_sizer.Add(text_ctrl, 1, wx.RIGHT, 5)

            browse_btn = wx.Button(parent, label="Browse...", size=(80, -1))
            browse_btn.Bind(wx.EVT_BUTTON, lambda e, tc=text_ctrl, pn=param_name: self._on_browse_path(e, tc, pn))
            h_sizer.Add(browse_btn, 0)

            sizer.Add(h_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        else:  # input, integer, string, or other text-based types
            # Create text control
            label = wx.StaticText(parent, label=label_text)
            label.SetToolTip(description)
            sizer.Add(label, 0, wx.ALL, 5)

            text_ctrl = wx.TextCtrl(parent, value=str(initial_value))
            self.controls[param_name] = text_ctrl
            sizer.Add(text_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    def _format_label(self, param_name: str) -> str:
        """Format parameter name as a readable label."""
        # Convert snake_case to Title Case
        words = param_name.replace("_", " ").split()
        return " ".join(word.capitalize() for word in words)

    def _on_add_list_item(self, event, param_name, param_info):
        """Handle adding item to list parameter."""
        # Check if this is a path-related parameter
        is_path = any(keyword in param_name.lower()
                     for keyword in ["path", "file", "dir", "folder", "data"])

        if is_path:
            # Determine if it's a file or directory
            is_dir = any(keyword in param_name.lower()
                        for keyword in ["dir", "folder", "path"])

            if is_dir:
                dialog = wx.DirDialog(
                    self,
                    "Select Directory",
                    style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
                )
            else:
                dialog = wx.FileDialog(
                    self,
                    "Select File",
                    style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
                )

            if dialog.ShowModal() == wx.ID_OK:
                path = dialog.GetPath()
                list_box = self.controls[param_name]
                list_box.Append(path)

            dialog.Destroy()
        else:
            # Text input dialog
            dialog = wx.TextEntryDialog(
                self,
                f"Enter value to add:",
                f"Add {self._format_label(param_name)}"
            )

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

    def _on_browse_path(self, event, text_ctrl, param_name):
        """Handle browse button for path parameters."""
        # Determine if it's a file or directory
        is_dir = any(keyword in param_name.lower()
                    for keyword in ["dir", "folder", "output"])

        if is_dir:
            dialog = wx.DirDialog(
                self,
                "Select Directory",
                style=wx.DD_DEFAULT_STYLE
            )
        else:
            dialog = wx.FileDialog(
                self,
                "Select File",
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            )

        if dialog.ShowModal() == wx.ID_OK:
            text_ctrl.SetValue(dialog.GetPath())

        dialog.Destroy()

    def get_options(self) -> Dict[str, Any]:
        """
        Get the configured options.

        Returns
        -------
        Dict[str, Any]
            Dictionary of option values
        """
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
                if items:  # Only add if not empty
                    options[param_name] = items
            elif isinstance(control, wx.TextCtrl):
                value = control.GetValue().strip()
                if value:  # Only add if not empty
                    # Convert to appropriate type
                    if param_type == "integer":
                        try:
                            options[param_name] = int(value)
                        except ValueError:
                            options[param_name] = value
                    else:
                        options[param_name] = value

        return options