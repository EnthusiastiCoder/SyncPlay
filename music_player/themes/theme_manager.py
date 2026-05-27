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
