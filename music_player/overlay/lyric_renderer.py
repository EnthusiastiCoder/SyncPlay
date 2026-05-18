"""QPainter-based word-level lyric renderer for the overlay."""

from typing import Optional

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QFont, QFontMetrics, QColor

from music_player.config import ConfigManager
from music_player.models.wlrc import WlrcData, WlrcLine


class LyricRenderer:
    """Renders 3 lyric lines with word-level coloring via QPainter.
