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

    settings_requested = pyqtSignal()
    hide_requested = pyqtSignal()
    edit_mode_changed = pyqtSignal(bool)  # True when entering edit mode

    def __init__(self, config: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._config = config

        # Display state
        self._lines: list[tuple[str, bool]] = []  # (text, is_current)
        self._wlrc: Optional[WlrcData] = None
        self._current_time_ms: int = 0
        
        # Interaction state
        self._edit_mode = False      # user-toggled edit mode
        self._drag_active = False    # currently dragging
        self._drag_start: Optional[QPoint] = None
        
        # Resize state
        self._resize_mode = False
        self._resize_start_height: int = 0
        self._resize_start_y: int = 0
        self._resize_grip_size = 20
        
        # Auto-lock timer: exit edit mode after 4s of no interaction
        self._edit_idle_timer = QTimer(self)
        self._edit_idle_timer.setSingleShot(True)
        self._edit_idle_timer.setInterval(4000)  # 4 seconds
        self._edit_idle_timer.timeout.connect(self._on_edit_idle_timeout)
        
        # Fade animation
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0)
        
        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_animation.setDuration(500)  # 500ms fade
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Auto-hide timer for pause state
        self._pause_hide_timer = QTimer(self)
        self._pause_hide_timer.setSingleShot(True)
        self._pause_hide_timer.timeout.connect(self._fade_out)
        self._pause_hide_timer.setInterval(5000)  # 5 seconds

        # Lyric renderer
        self._renderer = LyricRenderer(config)

        # Refresh timer for smooth updates (30 Hz)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(33)
        self._refresh_timer.timeout.connect(self.update)

        # Line transition animation
        self._ANIM_DURATION_MS = 300
        self._last_line_index: int = -1
        self._anim_slots: list[_AnimSlot] = []
        self._anim_elapsed = QElapsedTimer()
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60fps for smooth animation
        self._anim_timer.timeout.connect(self._on_anim_tick)

        self._setup_window()
        self._apply_config()
