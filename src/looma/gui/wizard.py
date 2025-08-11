"""Configuration wizard for Looma GUI."""

from pathlib import Path
from typing import Optional

import wx
import wx.adv


class ConfigWizard(wx.adv.Wizard):
    """
    Configuration wizard for first-time setup.
    
    Attributes
    ----------
    config : dict
        Configuration dictionary
    config_path : Path
        Path to save configuration
    """
    
    def __init__(self, parent, config_path: Optional[Path] = None):
        """
        Initialize configuration wizard.
        
        Parameters
        ----------
        parent : wx.Window
            Parent window
        config_path : Optional[Path]
            Configuration file path
        """
        super().__init__(
            parent,
            title="Looma Configuration Wizard",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        
        self.config_path = config_path or Path("looma.yml")
        self.config = {
            "version": "1.0",
            "app": {},
            "packaging": {},
            "update": {"source": {}},
            "security": {"signing": {}, "verification": {}},
        }
        
        # Create pages
        self.welcome_page = WelcomePage(self)
        self.app_page = ApplicationPage(self)
        self.packaging_page = PackagingPage(self)
        self.source_page = SourcePage(self)
        self.security_page = SecurityPage(self)
        self.summary_page = SummaryPage(self)
        
        # Chain pages
        wx.adv.WizardPageSimple.Chain(self.welcome_page, self.app_page)
        wx.adv.WizardPageSimple.Chain(self.app_page, self.packaging_page)
        wx.adv.WizardPageSimple.Chain(self.packaging_page, self.source_page)
        wx.adv.WizardPageSimple.Chain(self.source_page, self.security_page)
        wx.adv.WizardPageSimple.Chain(self.security_page, self.summary_page)
        
        # Set initial size
        self.SetPageSize((500, 400))
        
        # Bind events
        self.Bind(wx.adv.EVT_WIZARD_FINISHED, self.on_finished)
    
    def GetFirstPage(self):
        """Get first wizard page."""
        return self.welcome_page
    
    def get_config(self) -> dict:
        """Get configuration dictionary."""
        return self.config
    
    def get_config_path(self) -> Path:
        """Get configuration file path."""
        return self.config_path
    
    def on_finished(self, event):
        """Handle wizard finished."""
        # Collect data from all pages
        self.app_page.save_data()
        self.packaging_page.save_data()
        self.source_page.save_data()
        self.security_page.save_data()
        
        # Save configuration
        try:
            from looma.core.config import ConfigManager
            
            config_manager = ConfigManager(self.config_path)
            config_manager.save(self.config, self.config_path)
            
            wx.MessageBox(
                f"Configuration saved to {self.config_path}",
                "Success",
                wx.OK | wx.ICON_INFORMATION,
            )
        except Exception as e:
            wx.MessageBox(
                f"Failed to save configuration:\n{e}",
                "Error",
                wx.OK | wx.ICON_ERROR,
            )


class WelcomePage(wx.adv.WizardPageSimple):
    """Welcome page for configuration wizard."""
    
    def __init__(self, parent):
        """Initialize welcome page."""
        super().__init__(parent)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(
            self,
            label="Welcome to Looma Configuration Wizard",
            style=wx.ALIGN_CENTER,
        )
        title_font = title.GetFont()
        title_font.PointSize += 4
        title_font = title_font.Bold()
        title.SetFont(title_font)
        
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 20)
        
        # Description
        desc = wx.StaticText(
            self,
            label=(
                "This wizard will help you create a configuration file "
                "for your Looma application.\n\n"
                "You will be guided through the following steps:\n\n"
                "  1. Application Information\n"
                "  2. Packaging Settings\n"
                "  3. Update Source Configuration\n"
                "  4. Security Settings\n"
                "  5. Review and Save\n\n"
                "Click Next to begin."
            ),
        )
        sizer.Add(desc, 0, wx.ALL | wx.EXPAND, 20)
        
        self.SetSizer(sizer)


class ApplicationPage(wx.adv.WizardPageSimple):
    """Application information page."""
    
    def __init__(self, parent):
        """Initialize application page."""
        super().__init__(parent)
        self.parent = parent
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Application Information")
        title_font = title.GetFont()
        title_font.PointSize += 2
        title_font = title_font.Bold()
        title.SetFont(title_font)
        
        sizer.Add(title, 0, wx.ALL, 10)
        
        # Form
        form_sizer = wx.FlexGridSizer(6, 2, 10, 10)
        form_sizer.AddGrowableCol(1)
        
        # Name
        form_sizer.Add(wx.StaticText(self, label="Name:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.name_ctrl = wx.TextCtrl(self)
        form_sizer.Add(self.name_ctrl, 1, wx.EXPAND)
        
        # Version
        form_sizer.Add(wx.StaticText(self, label="Version:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.version_ctrl = wx.TextCtrl(self, value="1.0.0")
        form_sizer.Add(self.version_ctrl, 1, wx.EXPAND)
        
        # Description
        form_sizer.Add(wx.StaticText(self, label="Description:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.desc_ctrl = wx.TextCtrl(self)
        form_sizer.Add(self.desc_ctrl, 1, wx.EXPAND)
        
        # Author
        form_sizer.Add(wx.StaticText(self, label="Author:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.author_ctrl = wx.TextCtrl(self)
        form_sizer.Add(self.author_ctrl, 1, wx.EXPAND)
        
        # Email
        form_sizer.Add(wx.StaticText(self, label="Email:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.email_ctrl = wx.TextCtrl(self)
        form_sizer.Add(self.email_ctrl, 1, wx.EXPAND)
        
        # License
        form_sizer.Add(wx.StaticText(self, label="License:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.license_ctrl = wx.ComboBox(
            self,
            choices=["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "Proprietary"],
            value="MIT",
        )
        form_sizer.Add(self.license_ctrl, 1, wx.EXPAND)
        
        sizer.Add(form_sizer, 0, wx.ALL | wx.EXPAND, 20)
        
        self.SetSizer(sizer)
    
    def save_data(self):
        """Save page data to configuration."""
        self.parent.config["app"] = {
            "name": self.name_ctrl.GetValue(),
            "version": self.version_ctrl.GetValue(),
            "description": self.desc_ctrl.GetValue(),
            "author": self.author_ctrl.GetValue(),
            "email": self.email_ctrl.GetValue(),
            "license": self.license_ctrl.GetValue(),
        }


class PackagingPage(wx.adv.WizardPageSimple):
    """Packaging settings page."""
    
    def __init__(self, parent):
        """Initialize packaging page."""
        super().__init__(parent)
        self.parent = parent
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Packaging Settings")
        title_font = title.GetFont()
        title_font.PointSize += 2
        title_font = title_font.Bold()
        title.SetFont(title_font)
        
        sizer.Add(title, 0, wx.ALL, 10)
        
        # Engine selection
        engine_sizer = wx.BoxSizer(wx.HORIZONTAL)
        engine_sizer.Add(wx.StaticText(self, label="Engine:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        
        self.engine_choice = wx.Choice(
            self,
            choices=["pyinstaller", "nuitka", "cxfreeze"],
        )
        self.engine_choice.SetSelection(0)
        engine_sizer.Add(self.engine_choice, 1)
        
        sizer.Add(engine_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Entry point
        entry_sizer = wx.BoxSizer(wx.HORIZONTAL)
        entry_sizer.Add(wx.StaticText(self, label="Entry Point:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        
        self.entry_ctrl = wx.TextCtrl(self, value="main.py")
        entry_sizer.Add(self.entry_ctrl, 1)
        
        browse_btn = wx.Button(self, label="Browse...")
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        entry_sizer.Add(browse_btn, 0, wx.LEFT, 5)
        
        sizer.Add(entry_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Options
        self.one_file_check = wx.CheckBox(self, label="Create single file executable")
        sizer.Add(self.one_file_check, 0, wx.ALL, 10)
        
        self.console_check = wx.CheckBox(self, label="Show console window")
        self.console_check.SetValue(True)
        sizer.Add(self.console_check, 0, wx.ALL, 10)
        
        # Icon
        icon_sizer = wx.BoxSizer(wx.HORIZONTAL)
        icon_sizer.Add(wx.StaticText(self, label="Icon:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        
        self.icon_ctrl = wx.TextCtrl(self)
        icon_sizer.Add(self.icon_ctrl, 1)
        
        icon_browse_btn = wx.Button(self, label="Browse...")
        icon_browse_btn.Bind(wx.EVT_BUTTON, self.on_browse_icon)
        icon_sizer.Add(icon_browse_btn, 0, wx.LEFT, 5)
        
        sizer.Add(icon_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        self.SetSizer(sizer)
    
    def on_browse(self, event):
        """Handle browse for entry point."""
        with wx.FileDialog(
            self,
            "Select Entry Point",
            wildcard="Python files (*.py)|*.py",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.entry_ctrl.SetValue(dialog.GetPath())
    
    def on_browse_icon(self, event):
        """Handle browse for icon."""
        wildcard = "Icon files (*.ico;*.icns)|*.ico;*.icns|All files (*.*)|*.*"
        
        with wx.FileDialog(
            self,
            "Select Icon",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.icon_ctrl.SetValue(dialog.GetPath())
    
    def save_data(self):
        """Save page data to configuration."""
        self.parent.config["packaging"] = {
            "engine": self.engine_choice.GetStringSelection(),
            "entry_point": self.entry_ctrl.GetValue(),
            "one_file": self.one_file_check.GetValue(),
            "console": self.console_check.GetValue(),
            "icon": self.icon_ctrl.GetValue() or None,
        }


class SourcePage(wx.adv.WizardPageSimple):
    """Update source configuration page."""
    
    def __init__(self, parent):
        """Initialize source page."""
        super().__init__(parent)
        self.parent = parent
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Update Source Configuration")
        title_font = title.GetFont()
        title_font.PointSize += 2
        title_font = title_font.Bold()
        title.SetFont(title_font)
        
        sizer.Add(title, 0, wx.ALL, 10)
        
        # Source type
        type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        type_sizer.Add(wx.StaticText(self, label="Source Type:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        
        self.type_choice = wx.Choice(
            self,
            choices=["github", "gitlab", "s3", "artifactory", "http"],
        )
        self.type_choice.SetSelection(0)
        self.type_choice.Bind(wx.EVT_CHOICE, self.on_type_change)
        type_sizer.Add(self.type_choice, 1)
        
        sizer.Add(type_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Dynamic fields panel
        self.fields_panel = wx.Panel(self)
        self.fields_sizer = wx.BoxSizer(wx.VERTICAL)
        self.fields_panel.SetSizer(self.fields_sizer)
        
        sizer.Add(self.fields_panel, 1, wx.ALL | wx.EXPAND, 10)
        
        # Channel
        channel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        channel_sizer.Add(wx.StaticText(self, label="Channel:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        
        self.channel_choice = wx.Choice(
            self,
            choices=["stable", "beta", "alpha", "nightly"],
        )
        self.channel_choice.SetSelection(0)
        channel_sizer.Add(self.channel_choice, 1)
        
        sizer.Add(channel_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Strategy
        strategy_sizer = wx.BoxSizer(wx.HORIZONTAL)
        strategy_sizer.Add(wx.StaticText(self, label="Update Strategy:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        
        self.strategy_choice = wx.Choice(
            self,
            choices=["prompt", "silent", "force"],
        )
        self.strategy_choice.SetSelection(0)
        strategy_sizer.Add(self.strategy_choice, 1)
        
        sizer.Add(strategy_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        self.SetSizer(sizer)
        
        # Initialize fields
        self.on_type_change(None)
    
    def on_type_change(self, event):
        """Handle source type change."""
        # Clear existing fields
        self.fields_sizer.Clear(True)
        
        source_type = self.type_choice.GetStringSelection()
        
        if source_type == "github":
            self._create_github_fields()
        elif source_type == "gitlab":
            self._create_gitlab_fields()
        elif source_type == "s3":
            self._create_s3_fields()
        elif source_type == "artifactory":
            self._create_artifactory_fields()
        elif source_type == "http":
            self._create_http_fields()
        
        self.fields_panel.Layout()
        self.Layout()
    
    def _create_github_fields(self):
        """Create GitHub-specific fields."""
        # Repository
        repo_sizer = wx.BoxSizer(wx.HORIZONTAL)
        repo_sizer.Add(wx.StaticText(self.fields_panel, label="Repository:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.repo_ctrl = wx.TextCtrl(self.fields_panel)
        self.repo_ctrl.SetHint("owner/repository")
        repo_sizer.Add(self.repo_ctrl, 1)
        self.fields_sizer.Add(repo_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        
        # Token
        token_sizer = wx.BoxSizer(wx.HORIZONTAL)
        token_sizer.Add(wx.StaticText(self.fields_panel, label="Token:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.token_ctrl = wx.TextCtrl(self.fields_panel, style=wx.TE_PASSWORD)
        self.token_ctrl.SetHint("${GITHUB_TOKEN}")
        token_sizer.Add(self.token_ctrl, 1)
        self.fields_sizer.Add(token_sizer, 0, wx.EXPAND)
    
    def _create_gitlab_fields(self):
        """Create GitLab-specific fields."""
        # Project ID
        project_sizer = wx.BoxSizer(wx.HORIZONTAL)
        project_sizer.Add(wx.StaticText(self.fields_panel, label="Project ID:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.project_ctrl = wx.TextCtrl(self.fields_panel)
        project_sizer.Add(self.project_ctrl, 1)
        self.fields_sizer.Add(project_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        
        # Token
        token_sizer = wx.BoxSizer(wx.HORIZONTAL)
        token_sizer.Add(wx.StaticText(self.fields_panel, label="Token:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.token_ctrl = wx.TextCtrl(self.fields_panel, style=wx.TE_PASSWORD)
        self.token_ctrl.SetHint("${GITLAB_TOKEN}")
        token_sizer.Add(self.token_ctrl, 1)
        self.fields_sizer.Add(token_sizer, 0, wx.EXPAND)
    
    def _create_s3_fields(self):
        """Create S3-specific fields."""
        # Bucket
        bucket_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bucket_sizer.Add(wx.StaticText(self.fields_panel, label="Bucket:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.bucket_ctrl = wx.TextCtrl(self.fields_panel)
        bucket_sizer.Add(self.bucket_ctrl, 1)
        self.fields_sizer.Add(bucket_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        
        # Region
        region_sizer = wx.BoxSizer(wx.HORIZONTAL)
        region_sizer.Add(wx.StaticText(self.fields_panel, label="Region:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.region_ctrl = wx.TextCtrl(self.fields_panel, value="us-east-1")
        region_sizer.Add(self.region_ctrl, 1)
        self.fields_sizer.Add(region_sizer, 0, wx.EXPAND)
    
    def _create_artifactory_fields(self):
        """Create Artifactory-specific fields."""
        # URL
        url_sizer = wx.BoxSizer(wx.HORIZONTAL)
        url_sizer.Add(wx.StaticText(self.fields_panel, label="URL:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.url_ctrl = wx.TextCtrl(self.fields_panel)
        url_sizer.Add(self.url_ctrl, 1)
        self.fields_sizer.Add(url_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        
        # Repository
        repo_sizer = wx.BoxSizer(wx.HORIZONTAL)
        repo_sizer.Add(wx.StaticText(self.fields_panel, label="Repository:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.repo_ctrl = wx.TextCtrl(self.fields_panel)
        repo_sizer.Add(self.repo_ctrl, 1)
        self.fields_sizer.Add(repo_sizer, 0, wx.EXPAND)
    
    def _create_http_fields(self):
        """Create HTTP-specific fields."""
        # Base URL
        url_sizer = wx.BoxSizer(wx.HORIZONTAL)
        url_sizer.Add(wx.StaticText(self.fields_panel, label="Base URL:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.url_ctrl = wx.TextCtrl(self.fields_panel)
        url_sizer.Add(self.url_ctrl, 1)
        self.fields_sizer.Add(url_sizer, 0, wx.EXPAND)
    
    def save_data(self):
        """Save page data to configuration."""
        source_type = self.type_choice.GetStringSelection()
        source_config = {"type": source_type}
        
        if source_type == "github":
            if hasattr(self, "repo_ctrl"):
                source_config["repo"] = self.repo_ctrl.GetValue()
            if hasattr(self, "token_ctrl"):
                source_config["token"] = self.token_ctrl.GetValue()
        elif source_type == "gitlab":
            if hasattr(self, "project_ctrl"):
                source_config["project_id"] = self.project_ctrl.GetValue()
            if hasattr(self, "token_ctrl"):
                source_config["token"] = self.token_ctrl.GetValue()
        elif source_type == "s3":
            if hasattr(self, "bucket_ctrl"):
                source_config["bucket"] = self.bucket_ctrl.GetValue()
            if hasattr(self, "region_ctrl"):
                source_config["region"] = self.region_ctrl.GetValue()
        elif source_type == "artifactory":
            if hasattr(self, "url_ctrl"):
                source_config["url"] = self.url_ctrl.GetValue()
            if hasattr(self, "repo_ctrl"):
                source_config["repository"] = self.repo_ctrl.GetValue()
        elif source_type == "http":
            if hasattr(self, "url_ctrl"):
                source_config["base_url"] = self.url_ctrl.GetValue()
        
        self.parent.config["update"]["source"] = source_config
        self.parent.config["update"]["channel"] = self.channel_choice.GetStringSelection()
        self.parent.config["update"]["strategy"] = self.strategy_choice.GetStringSelection()


class SecurityPage(wx.adv.WizardPageSimple):
    """Security settings page."""
    
    def __init__(self, parent):
        """Initialize security page."""
        super().__init__(parent)
        self.parent = parent
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Security Settings")
        title_font = title.GetFont()
        title_font.PointSize += 2
        title_font = title_font.Bold()
        title.SetFont(title_font)
        
        sizer.Add(title, 0, wx.ALL, 10)
        
        # Enable signing
        self.signing_check = wx.CheckBox(self, label="Enable package signing")
        sizer.Add(self.signing_check, 0, wx.ALL, 10)
        self.signing_check.Bind(wx.EVT_CHECKBOX, self.on_signing_change)
        
        # Signing panel
        self.signing_panel = wx.Panel(self)
        signing_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Private key
        key_sizer = wx.BoxSizer(wx.HORIZONTAL)
        key_sizer.Add(wx.StaticText(self.signing_panel, label="Private Key:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.key_ctrl = wx.TextCtrl(self.signing_panel, value="keys/private.key")
        key_sizer.Add(self.key_ctrl, 1)
        
        key_browse_btn = wx.Button(self.signing_panel, label="Browse...")
        key_browse_btn.Bind(wx.EVT_BUTTON, self.on_browse_key)
        key_sizer.Add(key_browse_btn, 0, wx.LEFT, 5)
        
        generate_btn = wx.Button(self.signing_panel, label="Generate...")
        generate_btn.Bind(wx.EVT_BUTTON, self.on_generate_keys)
        key_sizer.Add(generate_btn, 0, wx.LEFT, 5)
        
        signing_sizer.Add(key_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        self.signing_panel.SetSizer(signing_sizer)
        self.signing_panel.Enable(False)
        sizer.Add(self.signing_panel, 0, wx.ALL | wx.EXPAND, 10)
        
        # Verification
        self.strict_check = wx.CheckBox(self, label="Strict signature verification")
        self.strict_check.SetValue(True)
        sizer.Add(self.strict_check, 0, wx.ALL, 10)
        
        self.ssl_check = wx.CheckBox(self, label="Verify SSL certificates")
        self.ssl_check.SetValue(True)
        sizer.Add(self.ssl_check, 0, wx.ALL, 10)
        
        self.SetSizer(sizer)
    
    def on_signing_change(self, event):
        """Handle signing checkbox change."""
        self.signing_panel.Enable(self.signing_check.GetValue())
    
    def on_browse_key(self, event):
        """Handle browse for private key."""
        with wx.FileDialog(
            self,
            "Select Private Key",
            wildcard="Key files (*.key;*.pem)|*.key;*.pem|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.key_ctrl.SetValue(dialog.GetPath())
    
    def on_generate_keys(self, event):
        """Handle generate keys."""
        wx.MessageBox(
            "Key generation will be implemented in a future version.\n"
            "For now, please use the Looma CLI to generate keys:\n\n"
            "looma keys generate",
            "Generate Keys",
            wx.OK | wx.ICON_INFORMATION,
        )
    
    def save_data(self):
        """Save page data to configuration."""
        self.parent.config["security"]["signing"] = {
            "enabled": self.signing_check.GetValue(),
            "private_key_path": self.key_ctrl.GetValue() if self.signing_check.GetValue() else None,
        }
        
        self.parent.config["security"]["verification"] = {
            "strict": self.strict_check.GetValue(),
        }
        
        self.parent.config["security"]["ssl"] = {
            "verify": self.ssl_check.GetValue(),
        }


class SummaryPage(wx.adv.WizardPageSimple):
    """Summary page for configuration wizard."""
    
    def __init__(self, parent):
        """Initialize summary page."""
        super().__init__(parent)
        self.parent = parent
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Configuration Summary")
        title_font = title.GetFont()
        title_font.PointSize += 2
        title_font = title_font.Bold()
        title.SetFont(title_font)
        
        sizer.Add(title, 0, wx.ALL, 10)
        
        # Summary text
        self.summary_text = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(-1, 250),
        )
        sizer.Add(self.summary_text, 1, wx.ALL | wx.EXPAND, 10)
        
        # Save path
        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        path_sizer.Add(wx.StaticText(self, label="Save to:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        
        self.path_ctrl = wx.TextCtrl(self, value=str(self.parent.config_path))
        path_sizer.Add(self.path_ctrl, 1)
        
        browse_btn = wx.Button(self, label="Browse...")
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        path_sizer.Add(browse_btn, 0, wx.LEFT, 5)
        
        sizer.Add(path_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        self.SetSizer(sizer)
        
        # Bind page change event
        self.Bind(wx.adv.EVT_WIZARD_PAGE_CHANGED, self.on_page_changed)
    
    def on_page_changed(self, event):
        """Handle page changed event."""
        # Update summary
        config = self.parent.config
        
        summary = []
        summary.append("APPLICATION INFORMATION")
        summary.append(f"  Name: {config.get('app', {}).get('name', 'Not set')}")
        summary.append(f"  Version: {config.get('app', {}).get('version', 'Not set')}")
        summary.append("")
        
        summary.append("PACKAGING SETTINGS")
        summary.append(f"  Engine: {config.get('packaging', {}).get('engine', 'Not set')}")
        summary.append(f"  Entry Point: {config.get('packaging', {}).get('entry_point', 'Not set')}")
        summary.append("")
        
        summary.append("UPDATE SOURCE")
        summary.append(f"  Type: {config.get('update', {}).get('source', {}).get('type', 'Not set')}")
        summary.append(f"  Channel: {config.get('update', {}).get('channel', 'Not set')}")
        summary.append(f"  Strategy: {config.get('update', {}).get('strategy', 'Not set')}")
        summary.append("")
        
        summary.append("SECURITY")
        summary.append(f"  Signing: {'Enabled' if config.get('security', {}).get('signing', {}).get('enabled') else 'Disabled'}")
        summary.append(f"  Strict Verification: {'Yes' if config.get('security', {}).get('verification', {}).get('strict') else 'No'}")
        
        self.summary_text.SetValue("\n".join(summary))
    
    def on_browse(self, event):
        """Handle browse for save path."""
        with wx.FileDialog(
            self,
            "Save Configuration",
            wildcard="YAML files (*.yml;*.yaml)|*.yml;*.yaml",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.path_ctrl.SetValue(dialog.GetPath())
                self.parent.config_path = Path(dialog.GetPath())