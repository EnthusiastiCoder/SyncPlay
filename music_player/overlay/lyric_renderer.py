"""QPainter-based word-level lyric renderer for the overlay."""

from typing import Optional

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QFont, QFontMetrics, QColor

from music_player.config import ConfigManager
from music_player.models.wlrc import WlrcData, WlrcLine


class LyricRenderer:
    """Renders 3 lyric lines with word-level coloring via QPainter.

    Supports two modes:
    - Word-level: each word snaps to played color when playback reaches its start_ms.
    - Line-level fallback: linear left-to-right interpolation when no word data.
    """

    def __init__(self, config: ConfigManager):
        self._config = config
    
    def calculate_required_width(
        self,
        wlrc: Optional[WlrcData],
        current_time_ms: int,
        padding: int = 40
    ) -> int:
        """Calculate the minimum width needed to display all visible lines without truncation."""
        if wlrc is None or not wlrc.lines:
            return 400  # Default minimum width
        
        prev_line, current_line, next_line = wlrc.get_display_lines(current_time_ms)
        
        font_family = self._config.get("font_family", "Segoe UI")
        base_size = self._config.get("font_size_base", 28)
        ratio = self._config.get("font_ratio_side_lines", 0.75)
        
        side_size = max(8, int(base_size * ratio))
        
        base_font = QFont(font_family, base_size, QFont.Weight.Bold)
        side_font = QFont(font_family, side_size)
        
        max_width = 0
