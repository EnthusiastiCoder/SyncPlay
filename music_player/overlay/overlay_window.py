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
