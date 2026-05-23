"""Transparent always-on-top overlay window for lyric display."""

import ctypes
import ctypes.wintypes
from typing import Optional

from PyQt6.QtWidgets import QWidget, QMenu, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPoint, QElapsedTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QFont, QColor, QFontMetrics, QAction

from music_player.config import ConfigManager
from music_player.models.wlrc import WlrcData
from music_player.overlay.lyric_renderer import LyricRenderer

# Win32 constants for click-through
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080

user32 = ctypes.windll.user32


class _AnimSlot:
    """Animation slot for a transitioning lyric line."""
    __slots__ = ('line', 'cy0', 'cy1', 'sz0', 'sz1', 'a0', 'a1', 'w0', 'w1', 'active', 'played')

    def __init__(self, line, cy0, cy1, sz0, sz1, a0, a1, w0, w1, active, played):
        self.line = line        # WlrcLine or None
        self.cy0 = float(cy0)  # start center-y
        self.cy1 = float(cy1)  # end center-y
        self.sz0 = float(sz0)  # start font size
        self.sz1 = float(sz1)  # end font size
        self.a0 = float(a0)    # start opacity
        self.a1 = float(a1)    # end opacity
        self.w0 = float(w0)    # start font weight (e.g. 400=Normal, 700=Bold)
        self.w1 = float(w1)    # end font weight
        self.active = active   # True = word-level coloring (current line)
        self.played = played   # True = played color, False = unplayed


class OverlayWindow(QWidget):
    """Frameless, transparent, always-on-top overlay for lyrics."""
