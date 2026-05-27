"""Theme management system for SyncPlay lyric overlay."""

from dataclasses import dataclass
from typing import Optional
import json
from pathlib import Path


@dataclass
class Theme:
    """Represents a lyric overlay theme."""
    name: str
    played_color: str  # Hex color
    played_opacity: float  # 0.0 to 1.0
    unplayed_color: str  # Hex color
    unplayed_opacity: float  # 0.0 to 1.0
    is_builtin: bool = False
    
    def to_dict(self) -> dict:
        """Convert theme to dictionary for serialization."""
        return {
            "name": self.name,
            "played_color": self.played_color,
            "played_opacity": self.played_opacity,
            "unplayed_color": self.unplayed_color,
            "unplayed_opacity": self.unplayed_opacity,
            "is_builtin": self.is_builtin,
        }
    
    @staticmethod
    def from_dict(data: dict) -> "Theme":
        """Create theme from dictionary."""
        return Theme(
            name=data["name"],
            played_color=data["played_color"],
            played_opacity=data["played_opacity"],
            unplayed_color=data["unplayed_color"],
            unplayed_opacity=data["unplayed_opacity"],
            is_builtin=data.get("is_builtin", False),
        )


class ThemeManager:
    """Manages built-in and custom themes."""
    
    # Built-in preset themes
    BUILTIN_THEMES = [
        Theme(
            name="Spotify Green",
            played_color="#1DB954",
            played_opacity=1.0,
            unplayed_color="#FFFFFF",
            unplayed_opacity=0.7,
            is_builtin=True,
        ),
        Theme(
            name="Neon Blue",
            played_color="#00D4FF",
            played_opacity=1.0,
            unplayed_color="#AAAAAA",
            unplayed_opacity=0.8,
            is_builtin=True,
        ),
        Theme(
            name="Warm Sunset",
            played_color="#FF6B35",
            played_opacity=1.0,
            unplayed_color="#FFE0B2",
            unplayed_opacity=0.9,
            is_builtin=True,
        ),
        Theme(
            name="Monochrome",
            played_color="#FFFFFF",
            played_opacity=1.0,
            unplayed_color="#666666",
            unplayed_opacity=0.8,
            is_builtin=True,
        ),
        Theme(
            name="Cyberpunk",
            played_color="#FF00FF",
            played_opacity=1.0,
            unplayed_color="#00FFFF",
            unplayed_opacity=0.85,
            is_builtin=True,
        ),
        Theme(
            name="Classic Green",
            played_color="#00FF00",
            played_opacity=1.0,
            unplayed_color="#FFFFFF",
            unplayed_opacity=1.0,
            is_builtin=True,
        ),
    ]
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize theme manager.
