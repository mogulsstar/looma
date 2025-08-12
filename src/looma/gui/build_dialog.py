"""Build dialog for Looma GUI."""

import asyncio
import threading
from pathlib import Path
from typing import Any, Dict, Optional

import wx
import wx.lib.agw.aui as aui


class BuildDialog(wx.Dialog):
    """
    Build dialog for package building.

    Attributes
    ----------
    config : dict
        Configuration dictionary
    build_thread : threading.Thread
        Build thread
    """

    def __init__(self, parent, config: Dict[str, Any]):
        """
        Initialize build dialog.

        Parameters
        ----------
        parent : wx.Window
            Parent window
        config : dict
            Configuration dictionary
        """
        super().__init__(
            parent,
            title="Build Package",
            size=(600, 500),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        self.config = config
        self.build_thread = None
        self.cancelled = False

        # Create UI
        self._create_ui()

        # Center dialog
        self.Centre()

    def _create_ui(self):
        """Create user interface."""
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Options panel
        options_panel = wx.Panel(self)
        options_sizer = wx.BoxSizer(wx.VERTICAL)

        # Build options
        options_box = wx.StaticBox(options_panel, label="Build Options")
        box_sizer = wx.StaticBoxSizer(options_box, wx.VERTICAL)

        # Engine selection
        engine_sizer = wx.BoxSizer(wx.HORIZONTAL)
        engine_sizer.Add(
            wx.StaticText(options_panel, label="Engine:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        self.engine_choice = wx.Choice(
            options_panel,
            choices=["pyinstaller", "nuitka", "cxfreeze"],
        )

        # Set from config
        engine = self.config.get("packaging", {}).get("engine", "pyinstaller")
        engines = ["pyinstaller", "nuitka", "cxfreeze"]
        if engine in engines:
            self.engine_choice.SetSelection(engines.index(engine))
        else:
            self.engine_choice.SetSelection(0)

        engine_sizer.Add(self.engine_choice, 1)
        box_sizer.Add(engine_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Output directory
        output_sizer = wx.BoxSizer(wx.HORIZONTAL)
        output_sizer.Add(
            wx.StaticText(options_panel, label="Output:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        self.output_ctrl = wx.TextCtrl(options_panel, value="dist")
        output_sizer.Add(self.output_ctrl, 1)

        browse_btn = wx.Button(options_panel, label="Browse...")
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        output_sizer.Add(browse_btn, 0, wx.LEFT, 5)

        box_sizer.Add(output_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Build options checkboxes
        self.clean_check = wx.CheckBox(options_panel, label="Clean before build")
        self.clean_check.SetValue(True)
        box_sizer.Add(self.clean_check, 0, wx.ALL, 5)

        self.sign_check = wx.CheckBox(options_panel, label="Sign package")
        sign_enabled = self.config.get("security", {}).get("signing", {}).get("enabled", False)
        self.sign_check.SetValue(sign_enabled)
        box_sizer.Add(self.sign_check, 0, wx.ALL, 5)

        self.upload_check = wx.CheckBox(options_panel, label="Upload after build")
        box_sizer.Add(self.upload_check, 0, wx.ALL, 5)

        options_sizer.Add(box_sizer, 0, wx.EXPAND | wx.ALL, 10)
        options_panel.SetSizer(options_sizer)

        sizer.Add(options_panel, 0, wx.EXPAND | wx.ALL, 10)

        # Progress panel
        progress_panel = wx.Panel(self)
        progress_sizer = wx.BoxSizer(wx.VERTICAL)

        # Status text
        self.status_text = wx.StaticText(progress_panel, label="Ready to build")
        progress_sizer.Add(self.status_text, 0, wx.ALL, 5)

        # Progress bar
        self.progress_bar = wx.Gauge(progress_panel, range=100)
        progress_sizer.Add(self.progress_bar, 0, wx.EXPAND | wx.ALL, 5)

        # Output text
        self.output_text = wx.TextCtrl(
            progress_panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(-1, 200),
        )
        self.output_text.SetBackgroundColour(wx.Colour(240, 240, 240))
        progress_sizer.Add(self.output_text, 1, wx.EXPAND | wx.ALL, 5)

        progress_panel.SetSizer(progress_sizer)
        sizer.Add(progress_panel, 1, wx.EXPAND | wx.ALL, 10)

        # Button panel
        button_panel = wx.Panel(self)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.build_btn = wx.Button(button_panel, label="Build")
        self.build_btn.Bind(wx.EVT_BUTTON, self.on_build)
        button_sizer.Add(self.build_btn, 0, wx.ALL, 5)

        self.cancel_btn = wx.Button(button_panel, wx.ID_CANCEL, label="Cancel")
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.cancel_btn.Enable(False)
        button_sizer.Add(self.cancel_btn, 0, wx.ALL, 5)

        button_sizer.AddStretchSpacer()

        self.close_btn = wx.Button(button_panel, wx.ID_CLOSE, label="Close")
        self.close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        button_sizer.Add(self.close_btn, 0, wx.ALL, 5)

        button_panel.SetSizer(button_sizer)
        sizer.Add(button_panel, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)

        # Bind events
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_browse(self, event):
        """Handle browse for output directory."""
        with wx.DirDialog(
            self,
            "Select Output Directory",
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.output_ctrl.SetValue(dialog.GetPath())

    def on_build(self, event):
        """Handle build button click."""
        # Disable build button, enable cancel
        self.build_btn.Enable(False)
        self.cancel_btn.Enable(True)
        self.close_btn.Enable(False)

        # Clear output
        self.output_text.Clear()
        self.progress_bar.SetValue(0)
        self.cancelled = False

        # Start build thread
        self.build_thread = threading.Thread(target=self._build_thread)
        self.build_thread.daemon = True
        self.build_thread.start()

    def _build_thread(self):
        """Build thread function."""
        try:
            # Update status
            wx.CallAfter(self._update_status, "Initializing build...")
            wx.CallAfter(self._update_progress, 10)

            # Get build options
            engine = self.engine_choice.GetStringSelection()
            output_dir = Path(self.output_ctrl.GetValue())
            clean = self.clean_check.GetValue()
            sign = self.sign_check.GetValue()
            upload = self.upload_check.GetValue()

            # Import packager
            from looma.packager import PackagerFactory

            # Create packager
            wx.CallAfter(self._update_status, f"Creating {engine} packager...")
            wx.CallAfter(self._update_progress, 20)

            packager = PackagerFactory.create(engine, self.config)

            # Clean if requested
            if clean and output_dir.exists():
                wx.CallAfter(self._update_status, "Cleaning output directory...")
                wx.CallAfter(self._append_output, f"Cleaning {output_dir}...\n")

                import shutil
                shutil.rmtree(output_dir, ignore_errors=True)

            # Check if cancelled
            if self.cancelled:
                wx.CallAfter(self._build_cancelled)
                return

            # Build package
            wx.CallAfter(self._update_status, "Building package...")
            wx.CallAfter(self._update_progress, 30)
            wx.CallAfter(self._append_output, f"Building with {engine}...\n")

            # Create async event loop for build
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Run build
                result = loop.run_until_complete(
                    self._run_build(packager, output_dir)
                )

                if not result:
                    raise Exception("Build failed")

                wx.CallAfter(self._update_progress, 70)

                # Sign if requested
                if sign:
                    wx.CallAfter(self._update_status, "Signing package...")
                    wx.CallAfter(self._update_progress, 80)
                    wx.CallAfter(self._append_output, "Signing package...\n")

                    from looma.security.signing import Signer

                    signer = Signer(self.config)

                    # Find built package
                    packages = list(output_dir.glob("*.exe")) + \
                               list(output_dir.glob("*.dmg")) + \
                               list(output_dir.glob("*.AppImage"))

                    if packages:
                        for package in packages:
                            signature = signer.sign_package(package)
                            sig_path = package.with_suffix(package.suffix + ".sig")
                            sig_path.write_text(signature)
                            wx.CallAfter(
                                self._append_output,
                                f"Signed: {package.name}\n"
                            )

                # Upload if requested
                if upload:
                    wx.CallAfter(self._update_status, "Uploading package...")
                    wx.CallAfter(self._update_progress, 90)
                    wx.CallAfter(self._append_output, "Uploading package...\n")

                    # TODO: Implement upload
                    wx.CallAfter(
                        self._append_output,
                        "Upload not yet implemented\n"
                    )

                # Complete
                wx.CallAfter(self._update_progress, 100)
                wx.CallAfter(self._build_complete)

            finally:
                loop.close()

        except Exception as e:
            wx.CallAfter(self._build_error, str(e))

    async def _run_build(self, packager, output_dir):
        """
        Run build asynchronously.

        Parameters
        ----------
        packager : BasePackager
            Packager instance
        output_dir : Path
            Output directory

        Returns
        -------
        bool
            True if successful
        """
        try:
            # Build
            result = await packager.build(output_dir)

            # Update output
            wx.CallAfter(
                self._append_output,
                f"Build completed: {output_dir}\n"
            )

            return result

        except Exception as e:
            wx.CallAfter(
                self._append_output,
                f"Build error: {e}\n"
            )
            return False

    def _update_status(self, status: str):
        """Update status text."""
        self.status_text.SetLabel(status)

    def _update_progress(self, value: int):
        """Update progress bar."""
        self.progress_bar.SetValue(value)

    def _append_output(self, text: str):
        """Append text to output."""
        self.output_text.AppendText(text)

    def _build_complete(self):
        """Handle build completion."""
        self._update_status("Build completed successfully!")

        # Re-enable buttons
        self.build_btn.Enable(True)
        self.cancel_btn.Enable(False)
        self.close_btn.Enable(True)

        # Show success message
        wx.MessageBox(
            "Package built successfully!",
            "Build Complete",
            wx.OK | wx.ICON_INFORMATION,
        )

    def _build_error(self, error: str):
        """Handle build error."""
        self._update_status(f"Build failed: {error}")
        self._append_output(f"\nERROR: {error}\n")

        # Re-enable buttons
        self.build_btn.Enable(True)
        self.cancel_btn.Enable(False)
        self.close_btn.Enable(True)

        # Show error message
        wx.MessageBox(
            f"Build failed:\n{error}",
            "Build Error",
            wx.OK | wx.ICON_ERROR,
        )

    def _build_cancelled(self):
        """Handle build cancellation."""
        self._update_status("Build cancelled")
        self._append_output("\nBuild cancelled by user\n")

        # Re-enable buttons
        self.build_btn.Enable(True)
        self.cancel_btn.Enable(False)
        self.close_btn.Enable(True)

    def on_cancel(self, event):
        """Handle cancel button click."""
        self.cancelled = True
        self.cancel_btn.Enable(False)
        self._update_status("Cancelling...")

    def on_close(self, event):
        """Handle close button click."""
        if self.build_thread and self.build_thread.is_alive():
            # Confirm if build is running
            result = wx.MessageBox(
                "Build is still running. Cancel and close?",
                "Confirm Close",
                wx.YES_NO | wx.ICON_QUESTION,
            )

            if result == wx.YES:
                self.cancelled = True
                self.build_thread.join(timeout=2.0)

        self.EndModal(wx.ID_CLOSE)
