"""Theme management for Looma GUI."""

from typing import Dict, Optional

import wx


class Theme:
    """
    Base theme class.

    Attributes
    ----------
    name : str
        Theme name
    colors : dict
        Color definitions
    fonts : dict
        Font definitions
    """

    def __init__(self):
        """Initialize theme."""
        self.name = "Default"
        self.colors = {}
        self.fonts = {}
        self._init_theme()

    def _init_theme(self):
        """Initialize theme settings."""
        # Override in subclasses
        pass

    def apply(self, window: wx.Window):
        """
        Apply theme to window.

        Parameters
        ----------
        window : wx.Window
            Window to apply theme to
        """
        # Set window colors
        if "background" in self.colors:
            window.SetBackgroundColour(self.colors["background"])

        if "foreground" in self.colors:
            window.SetForegroundColour(self.colors["foreground"])

        # Apply to children recursively
        for child in window.GetChildren():
            self._apply_to_control(child)

        window.Refresh()

    def _apply_to_control(self, control: wx.Window):
        """
        Apply theme to control.

        Parameters
        ----------
        control : wx.Window
            Control to apply theme to
        """
        # Set control colors based on type
        if isinstance(control, wx.TextCtrl):
            if "text_background" in self.colors:
                control.SetBackgroundColour(self.colors["text_background"])
            if "text_foreground" in self.colors:
                control.SetForegroundColour(self.colors["text_foreground"])

        elif isinstance(control, wx.Button):
            if "button_background" in self.colors:
                control.SetBackgroundColour(self.colors["button_background"])
            if "button_foreground" in self.colors:
                control.SetForegroundColour(self.colors["button_foreground"])

        elif isinstance(control, wx.StaticText):
            if "label_foreground" in self.colors:
                control.SetForegroundColour(self.colors["label_foreground"])

        elif isinstance(control, wx.Panel):
            if "panel_background" in self.colors:
                control.SetBackgroundColour(self.colors["panel_background"])

        # Apply to children
        if hasattr(control, "GetChildren"):
            for child in control.GetChildren():
                self._apply_to_control(child)


class LightTheme(Theme):
    """Light theme."""

    def _init_theme(self):
        """Initialize light theme."""
        self.name = "Light"

        self.colors = {
            "background": wx.Colour(255, 255, 255),
            "foreground": wx.Colour(0, 0, 0),
            "panel_background": wx.Colour(245, 245, 245),
            "text_background": wx.Colour(255, 255, 255),
            "text_foreground": wx.Colour(0, 0, 0),
            "button_background": wx.Colour(240, 240, 240),
            "button_foreground": wx.Colour(0, 0, 0),
            "label_foreground": wx.Colour(64, 64, 64),
            "selection": wx.Colour(0, 120, 215),
            "selection_text": wx.Colour(255, 255, 255),
            "error": wx.Colour(255, 0, 0),
            "warning": wx.Colour(255, 165, 0),
            "success": wx.Colour(0, 128, 0),
        }

        self.fonts = {
            "default": wx.Font(
                9,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            ),
            "bold": wx.Font(
                9,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
            ),
            "monospace": wx.Font(
                9,
                wx.FONTFAMILY_TELETYPE,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            ),
        }


class DarkTheme(Theme):
    """Dark theme."""

    def _init_theme(self):
        """Initialize dark theme."""
        self.name = "Dark"

        self.colors = {
            "background": wx.Colour(30, 30, 30),
            "foreground": wx.Colour(240, 240, 240),
            "panel_background": wx.Colour(45, 45, 45),
            "text_background": wx.Colour(25, 25, 25),
            "text_foreground": wx.Colour(240, 240, 240),
            "button_background": wx.Colour(60, 60, 60),
            "button_foreground": wx.Colour(240, 240, 240),
            "label_foreground": wx.Colour(200, 200, 200),
            "selection": wx.Colour(0, 120, 215),
            "selection_text": wx.Colour(255, 255, 255),
            "error": wx.Colour(255, 85, 85),
            "warning": wx.Colour(255, 200, 0),
            "success": wx.Colour(85, 255, 85),
        }

        self.fonts = {
            "default": wx.Font(
                9,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            ),
            "bold": wx.Font(
                9,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
            ),
            "monospace": wx.Font(
                9,
                wx.FONTFAMILY_TELETYPE,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            ),
        }


class BlueTheme(Theme):
    """Blue theme."""

    def _init_theme(self):
        """Initialize blue theme."""
        self.name = "Blue"

        self.colors = {
            "background": wx.Colour(240, 248, 255),  # Alice Blue
            "foreground": wx.Colour(0, 0, 64),
            "panel_background": wx.Colour(230, 240, 250),
            "text_background": wx.Colour(255, 255, 255),
            "text_foreground": wx.Colour(0, 0, 64),
            "button_background": wx.Colour(100, 149, 237),  # Cornflower Blue
            "button_foreground": wx.Colour(255, 255, 255),
            "label_foreground": wx.Colour(70, 130, 180),  # Steel Blue
            "selection": wx.Colour(0, 120, 215),
            "selection_text": wx.Colour(255, 255, 255),
            "error": wx.Colour(220, 20, 60),  # Crimson
            "warning": wx.Colour(255, 140, 0),  # Dark Orange
            "success": wx.Colour(34, 139, 34),  # Forest Green
        }

        self.fonts = {
            "default": wx.Font(
                9,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            ),
            "bold": wx.Font(
                9,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
            ),
            "monospace": wx.Font(
                9,
                wx.FONTFAMILY_TELETYPE,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            ),
        }


class ThemeManager:
    """
    Manages application themes.

    Attributes
    ----------
    themes : dict
        Available themes
    current_theme : Theme
        Currently active theme
    """

    def __init__(self):
        """Initialize theme manager."""
        self.themes = {
            "Light": LightTheme(),
            "Dark": DarkTheme(),
            "Blue": BlueTheme(),
        }
        self.current_theme = self.themes["Light"]

    def get_themes(self) -> list:
        """
        Get list of available theme names.

        Returns
        -------
        list
            Theme names
        """
        return list(self.themes.keys())

    def get_theme(self, name: str) -> Optional[Theme]:
        """
        Get theme by name.

        Parameters
        ----------
        name : str
            Theme name

        Returns
        -------
        Optional[Theme]
            Theme or None
        """
        return self.themes.get(name)

    def set_theme(self, name: str) -> bool:
        """
        Set current theme.

        Parameters
        ----------
        name : str
            Theme name

        Returns
        -------
        bool
            True if theme was set
        """
        if name in self.themes:
            self.current_theme = self.themes[name]
            return True
        return False

    def apply_theme(self, window: wx.Window):
        """
        Apply current theme to window.

        Parameters
        ----------
        window : wx.Window
            Window to apply theme to
        """
        if self.current_theme:
            self.current_theme.apply(window)

    def get_color(self, color_name: str) -> Optional[wx.Colour]:
        """
        Get color from current theme.

        Parameters
        ----------
        color_name : str
            Color name

        Returns
        -------
        Optional[wx.Colour]
            Color or None
        """
        if self.current_theme and color_name in self.current_theme.colors:
            return self.current_theme.colors[color_name]
        return None

    def get_font(self, font_name: str) -> Optional[wx.Font]:
        """
        Get font from current theme.

        Parameters
        ----------
        font_name : str
            Font name

        Returns
        -------
        Optional[wx.Font]
            Font or None
        """
        if self.current_theme and font_name in self.current_theme.fonts:
            return self.current_theme.fonts[font_name]
        return None

    def load_theme_from_file(self, file_path: str) -> bool:
        """
        Load theme from JSON file.

        Parameters
        ----------
        file_path : str
            Path to theme file

        Returns
        -------
        bool
            True if loaded successfully
        """
        import json
        from pathlib import Path

        try:
            path = Path(file_path)
            if not path.exists():
                return False

            with open(path, "r") as f:
                theme_data = json.load(f)

            # Create custom theme
            custom_theme = Theme()
            custom_theme.name = theme_data.get("name", "Custom")

            # Load colors
            if "colors" in theme_data:
                for color_name, color_value in theme_data["colors"].items():
                    if isinstance(color_value, list) and len(color_value) >= 3:
                        custom_theme.colors[color_name] = wx.Colour(*color_value[:3])
                    elif isinstance(color_value, str):
                        # Parse hex color
                        if color_value.startswith("#"):
                            color_value = color_value[1:]
                        if len(color_value) == 6:
                            r = int(color_value[0:2], 16)
                            g = int(color_value[2:4], 16)
                            b = int(color_value[4:6], 16)
                            custom_theme.colors[color_name] = wx.Colour(r, g, b)

            # Add to themes
            self.themes[custom_theme.name] = custom_theme
            return True

        except Exception:
            return False

    def save_theme_to_file(self, theme_name: str, file_path: str) -> bool:
        """
        Save theme to JSON file.

        Parameters
        ----------
        theme_name : str
            Theme name to save
        file_path : str
            Path to save file

        Returns
        -------
        bool
            True if saved successfully
        """
        import json
        from pathlib import Path

        try:
            if theme_name not in self.themes:
                return False

            theme = self.themes[theme_name]

            # Prepare theme data
            theme_data = {
                "name": theme.name,
                "colors": {},
            }

            # Convert colors
            for color_name, color_value in theme.colors.items():
                theme_data["colors"][color_name] = [
                    color_value.Red(),
                    color_value.Green(),
                    color_value.Blue(),
                ]

            # Save to file
            path = Path(file_path)
            with open(path, "w") as f:
                json.dump(theme_data, f, indent=2)

            return True

        except Exception:
            return False


# Global theme manager instance
_theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    """
    Get the global theme manager instance.

    Returns
    -------
    ThemeManager
        Global theme manager instance
    """
    return _theme_manager
