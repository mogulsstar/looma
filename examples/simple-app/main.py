#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple application example with Looma auto-update support.

This example demonstrates how to integrate Looma's update client
into your Python application.
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
import json
from pathlib import Path


class SimpleApp:
    """
    A simple GUI application with auto-update support.
    
    Attributes
    ----------
    root : tk.Tk
        The main window
    version : str
        Current application version
    """
    
    def __init__(self):
        """Initialize the application."""
        self.root = tk.Tk()
        self.root.title("Simple App with Looma")
        self.root.geometry("600x400")
        
        # Load version from package info
        self.version = self._get_version()
        
        # Check for updates on startup (if Looma client is available)
        self._check_updates_on_startup()
        
        # Setup UI
        self._setup_ui()
    
    def _get_version(self) -> str:
        """
        Get application version.
        
        Returns
        -------
        str
            Version string
        """
        version_file = Path(__file__).parent / "version.json"
        if version_file.exists():
            with open(version_file, 'r') as f:
                data = json.load(f)
                return data.get('version', '1.0.0')
        return '1.0.0'
    
    def _check_updates_on_startup(self):
        """Check for updates on application startup."""
        try:
            # Import Looma client if available
            from looma.client import UpdateClient
            
            # Create update client
            self.update_client = UpdateClient()
            
            # Schedule update check after 1 second
            self.root.after(1000, self._async_check_updates)
        except ImportError:
            # Looma client not available, skip update check
            self.update_client = None
    
    def _async_check_updates(self):
        """Asynchronously check for updates."""
        if self.update_client:
            # This would typically be done in a background thread
            # For simplicity, we're simulating it here
            pass
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title label
        title_label = ttk.Label(
            main_frame,
            text="Simple Application",
            font=('Helvetica', 16, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Version label
        version_label = ttk.Label(
            main_frame,
            text=f"Version: {self.version}",
            font=('Helvetica', 10)
        )
        version_label.grid(row=1, column=0, columnspan=2, pady=5)
        
        # Feature buttons
        features_frame = ttk.LabelFrame(
            main_frame,
            text="Features",
            padding="10"
        )
        features_frame.grid(row=2, column=0, columnspan=2, pady=20, sticky=(tk.W, tk.E))
        
        # Sample feature buttons
        ttk.Button(
            features_frame,
            text="Feature 1",
            command=lambda: self._show_message("Feature 1 clicked!")
        ).grid(row=0, column=0, padx=5, pady=5)
        
        ttk.Button(
            features_frame,
            text="Feature 2",
            command=lambda: self._show_message("Feature 2 clicked!")
        ).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(
            features_frame,
            text="Feature 3",
            command=lambda: self._show_message("Feature 3 clicked!")
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Update section
        update_frame = ttk.LabelFrame(
            main_frame,
            text="Updates",
            padding="10"
        )
        update_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        # Check updates button
        ttk.Button(
            update_frame,
            text="Check for Updates",
            command=self._manual_check_updates
        ).grid(row=0, column=0, padx=5)
        
        # Status label
        self.status_label = ttk.Label(
            update_frame,
            text="No updates checked yet",
            font=('Helvetica', 9)
        )
        self.status_label.grid(row=0, column=1, padx=10)
        
        # Exit button
        ttk.Button(
            main_frame,
            text="Exit",
            command=self.root.quit
        ).grid(row=4, column=0, columnspan=2, pady=20)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
    
    def _show_message(self, message: str):
        """
        Show a message dialog.
        
        Parameters
        ----------
        message : str
            Message to display
        """
        messagebox.showinfo("Information", message)
    
    def _manual_check_updates(self):
        """Manually check for updates."""
        if self.update_client:
            # Simulate checking for updates
            self.status_label.config(text="Checking for updates...")
            self.root.after(2000, self._update_check_complete)
        else:
            self.status_label.config(text="Update client not available")
    
    def _update_check_complete(self):
        """Called when update check is complete."""
        # Simulate no updates available
        self.status_label.config(text="You're up to date!")
    
    def run(self):
        """Run the application."""
        self.root.mainloop()


def main():
    """Main entry point."""
    app = SimpleApp()
    app.run()


if __name__ == "__main__":
    main()