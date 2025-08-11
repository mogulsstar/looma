"""Update UI dialogs for Looma client."""

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Optional

from looma.core.utils import format_size


class UpdateDialog:
    """
    Update dialog for user interaction.
    
    Attributes
    ----------
    update_info : UpdateInfo
        Update information
    config : ConfigManager
        Configuration
    root : tk.Tk
        Root window
    result : str
        Dialog result
    """
    
    def __init__(self, update_info, config):
        """
        Initialize update dialog.
        
        Parameters
        ----------
        update_info : UpdateInfo
            Update information
        config : ConfigManager
            Configuration
        """
        self.update_info = update_info
        self.config = config
        self.result = None
        self.downloaded_path = None
        self.progress_var = None
    
    def show(self) -> str:
        """
        Show update dialog.
        
        Returns
        -------
        str
            User choice: "update", "skip", "later", or "cancel"
        """
        self.root = tk.Tk()
        self.root.title(self.config.get("update.ui.window_title", "Update Available"))
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # Center window
        self._center_window()
        
        # Create UI
        self._create_ui()
        
        # Run main loop
        self.root.mainloop()
        
        return self.result
    
    def _center_window(self):
        """Center the window on screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_ui(self):
        """Create dialog UI."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text=f"Version {self.update_info.version} is available",
            font=("", 14, "bold"),
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Current version
        current_version = self.config.get("app.version", "Unknown")
        version_label = ttk.Label(
            main_frame,
            text=f"Current version: {current_version}",
            font=("", 10),
        )
        version_label.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        # Release notes
        if self.config.get("update.ui.show_release_notes", True) and self.update_info.notes:
            notes_label = ttk.Label(main_frame, text="What's new:")
            notes_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
            
            notes_text = tk.Text(main_frame, height=8, width=50, wrap=tk.WORD)
            notes_text.grid(row=3, column=0, columnspan=2, pady=(0, 10))
            notes_text.insert("1.0", self.update_info.notes)
            notes_text.config(state=tk.DISABLED)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(main_frame, command=notes_text.yview)
            scrollbar.grid(row=3, column=2, sticky=(tk.N, tk.S))
            notes_text.config(yscrollcommand=scrollbar.set)
        
        # Download size
        size_label = ttk.Label(
            main_frame,
            text=f"Download size: {format_size(self.update_info.size)}",
            font=("", 9),
        )
        size_label.grid(row=4, column=0, columnspan=2, pady=(0, 10))
        
        # Progress bar (hidden initially)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            length=400,
        )
        self.progress_label = ttk.Label(main_frame, text="")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=(10, 0))
        
        # Update button
        update_btn = ttk.Button(
            button_frame,
            text="Update Now",
            command=self._on_update,
        )
        update_btn.grid(row=0, column=0, padx=5)
        
        # Later button
        if self.config.get("update.ui.allow_remind_later", True):
            later_btn = ttk.Button(
                button_frame,
                text="Remind Me Later",
                command=self._on_later,
            )
            later_btn.grid(row=0, column=1, padx=5)
        
        # Skip button
        if self.config.get("update.ui.allow_skip", True):
            skip_btn = ttk.Button(
                button_frame,
                text="Skip This Version",
                command=self._on_skip,
            )
            skip_btn.grid(row=0, column=2, padx=5)
        
        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
        )
        cancel_btn.grid(row=0, column=3, padx=5)
        
        # Set focus
        update_btn.focus()
    
    def _on_update(self):
        """Handle update button click."""
        self.result = "update"
        
        if not self.downloaded_path:
            # Show progress bar
            self.progress_bar.grid(row=5, column=0, columnspan=2, pady=(0, 5))
            self.progress_label.grid(row=5, column=2, pady=(0, 5))
            self.root.update()
        else:
            self.root.quit()
    
    def _on_skip(self):
        """Handle skip button click."""
        self.result = "skip"
        self.root.quit()
    
    def _on_later(self):
        """Handle later button click."""
        self.result = "later"
        self.root.quit()
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self.result = "cancel"
        self.root.quit()
    
    def update_progress(self, downloaded: int, total: Optional[int], percent: float):
        """
        Update download progress.
        
        Parameters
        ----------
        downloaded : int
            Bytes downloaded
        total : Optional[int]
            Total bytes
        percent : float
            Progress percentage
        """
        if self.progress_var:
            self.progress_var.set(percent)
            
            if total:
                text = f"{format_size(downloaded)} / {format_size(total)}"
            else:
                text = format_size(downloaded)
            
            self.progress_label.config(text=text)
            self.root.update()
    
    def set_downloaded(self, package_path: Path):
        """
        Set downloaded package path.
        
        Parameters
        ----------
        package_path : Path
            Downloaded package path
        """
        self.downloaded_path = package_path