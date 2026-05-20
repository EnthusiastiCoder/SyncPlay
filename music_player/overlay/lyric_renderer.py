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
        
        # Check all three lines
        for line, font in [(prev_line, side_font), (current_line, base_font), (next_line, side_font)]:
            if line:
                metrics = QFontMetrics(font)
                text = line.text
                line_width = metrics.horizontalAdvance(text)
                max_width = max(max_width, line_width)
        
        return max(400, max_width + padding)

    def render(
        self,
        painter: QPainter,
        rect: QRect,
        wlrc: Optional[WlrcData],
        current_time_ms: int,
    ) -> None:
        """Draw prev/current/next lyric lines inside the given rect."""
        if wlrc is None or not wlrc.lines:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        prev_line, current_line, next_line = wlrc.get_display_lines(current_time_ms)

        font_family = self._config.get("font_family", "Segoe UI")
        base_size = self._config.get("font_size_base", 28)
        ratio = self._config.get("font_ratio_side_lines", 0.75)
        
        played_color = QColor(self._config.get("played_color", "#00FF00"))
        played_opacity = self._config.get("played_opacity", 1.0)
        played_color.setAlphaF(played_opacity)
        
        unplayed_color = QColor(self._config.get("unplayed_color", "#FFFFFF"))
        unplayed_opacity = self._config.get("unplayed_opacity", 1.0)
        unplayed_color.setAlphaF(unplayed_opacity)

        side_size = max(8, int(base_size * ratio))

        base_font = QFont(font_family, base_size, QFont.Weight.Bold)
        side_font = QFont(font_family, side_size)

        w = rect.width()
        y = rect.y() + 10

        # Draw previous line (fully played)
        y = self._draw_line(
            painter, prev_line, side_font, played_color, played_color,
            current_time_ms, w, y, fully_played=True,
        )

        # Draw current line (word-level coloring)
        y = self._draw_line(
            painter, current_line, base_font, played_color, unplayed_color,
            current_time_ms, w, y, fully_played=False,
        )

        # Draw next line (fully unplayed)
        y = self._draw_line(
            painter, next_line, side_font, unplayed_color, unplayed_color,
            current_time_ms, w, y, fully_unplayed=True,
        )

    def draw_line_at(
        self,
        painter: QPainter,
        line: Optional[WlrcLine],
        font_size: int,
        y: int,
        width: int,
        opacity: float,
        current_time_ms: int,
        is_active: bool = False,
        is_played: bool = True,
        font_weight: Optional[int] = None,
    ) -> None:
        """Draw a single lyric line at explicit y, font size, opacity, and weight.

        Used by the overlay during animated line transitions.
        font_weight overrides the default Bold/Normal selection when provided.
        """
        if line is None or opacity <= 0.01:
            return

        font_family = self._config.get("font_family", "Segoe UI")
