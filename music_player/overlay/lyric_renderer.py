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

        played_color = QColor(self._config.get("played_color", "#00FF00"))
        p_base = self._config.get("played_opacity", 1.0)
        played_color.setAlphaF(min(1.0, p_base * opacity))

        unplayed_color = QColor(self._config.get("unplayed_color", "#FFFFFF"))
        u_base = self._config.get("unplayed_opacity", 1.0)
        unplayed_color.setAlphaF(min(1.0, u_base * opacity))

        if font_weight is not None:
            font = QFont(font_family, font_size)
            font.setWeight(QFont.Weight(font_weight))
        else:
            font = QFont(font_family, font_size,
                         QFont.Weight.Bold if is_active else QFont.Weight.Normal)

        if is_active:
            self._draw_line(
                painter, line, font, played_color, unplayed_color,
                current_time_ms, width, y,
            )
        elif is_played:
            self._draw_line(
                painter, line, font, played_color, played_color,
                current_time_ms, width, y, fully_played=True,
            )
        else:
            self._draw_line(
                painter, line, font, unplayed_color, unplayed_color,
                current_time_ms, width, y, fully_unplayed=True,
            )

    def _draw_line(
        self,
        painter: QPainter,
        line: Optional[WlrcLine],
        font: QFont,
        played_color: QColor,
        unplayed_color: QColor,
        current_time_ms: int,
        width: int,
        y: int,
        fully_played: bool = False,
        fully_unplayed: bool = False,
    ) -> int:
        """Draw a single lyric line. Returns the new y offset after drawing."""
        if line is None:
            fm = QFontMetrics(font)
            return y + fm.height() + 8

        painter.setFont(font)
        fm = QFontMetrics(font)

        if line.has_word_timing and not fully_played and not fully_unplayed:
            return self._draw_word_level(
                painter, line, font, fm, played_color, unplayed_color,
                current_time_ms, width, y,
            )
        elif line.has_word_timing:
            # Fully played or fully unplayed — draw entire line in one color
            color = played_color if fully_played else unplayed_color
            text = line.text
            text_width = fm.horizontalAdvance(text)
            x = (width - text_width) // 2
            y += fm.ascent()
            painter.setPen(color)
            painter.drawText(x, y, text)
            return y + fm.descent() + 8
        else:
            # No word timing — linear interpolation fallback
            return self._draw_linear_fallback(
                painter, line, fm, played_color, unplayed_color,
                current_time_ms, width, y, fully_played, fully_unplayed,
            )

    def _draw_word_level(
        self,
        painter: QPainter,
        line: WlrcLine,
        font: QFont,
        fm: QFontMetrics,
        played_color: QColor,
        unplayed_color: QColor,
        current_time_ms: int,
        width: int,
        y: int,
    ) -> int:
        """Draw a line with per-word coloring based on timestamps."""
        # Calculate total width to center the line
        word_texts = []
        total_width = 0
        space_width = fm.horizontalAdvance(" ")
        for i, word in enumerate(line.words):
            w = fm.horizontalAdvance(word.text)
            word_texts.append((word, w))
            total_width += w
            if i < len(line.words) - 1:
                total_width += space_width

        x = (width - total_width) // 2
        y += fm.ascent()

        for i, (word, w) in enumerate(word_texts):
            # Word is played if playback has reached its start
            if current_time_ms >= word.start_ms:
                painter.setPen(played_color)
            else:
                painter.setPen(unplayed_color)

            painter.drawText(x, y, word.text)
            x += w
            if i < len(word_texts) - 1:
                # Draw space with same color as next word
                next_word = word_texts[i + 1][0]
                if current_time_ms >= next_word.start_ms:
                    painter.setPen(played_color)
                else:
                    painter.setPen(unplayed_color)
                painter.drawText(x, y, " ")
                x += space_width
