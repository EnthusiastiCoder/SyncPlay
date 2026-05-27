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
