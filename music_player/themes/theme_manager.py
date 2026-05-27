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
