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

        # React to config changes
        self._config.config_changed.connect(self._on_config_changed)

    def _setup_window(self) -> None:
        """Configure window flags for overlay behavior."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # hides from taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Remove click-through initially to allow interaction
        self.setMouseTracking(True)

    def _apply_config(self) -> None:
        """Apply position and size from config."""
        x = self._config.get("overlay_x", -1)
        y = self._config.get("overlay_y", -1)
        h = self._config.get("overlay_height", 200)
        
        # Center on screen if position is unset (-1)
        if x < 0 or y < 0:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                x = geo.x() + (geo.width() - 400) // 2
                y = geo.y() + (geo.height() - h) // 2
            else:
                x, y = 400, 400
        
        # Width will be auto-calculated based on content
        self.move(x, y)
        self.setFixedHeight(h)

    def _on_config_changed(self, key: str, value) -> None:
        """React to live config changes."""
        if key in ("overlay_x", "overlay_y", "overlay_height"):
            self._apply_config()
        if key in ("played_color", "unplayed_color", "font_family",
                    "font_size_base", "font_ratio_side_lines"):
            self.update()

    def showEvent(self, event) -> None:
        """Apply click-through after the window is shown and has a valid HWND."""
        super().showEvent(event)
        if not self._edit_mode:
            QTimer.singleShot(50, self._set_click_through)

    def _set_click_through(self) -> None:
        """Make the window click-through using Win32 API."""
        if self._edit_mode:
            return
        hwnd = int(self.winId())
        try:
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                ex_style | WS_EX_TRANSPARENT | WS_EX_LAYERED
            )
        except Exception:
            pass  # Graceful fallback — overlay still works, just not click-through

    def _remove_click_through(self) -> None:
        """Remove click-through to allow dragging."""
        hwnd = int(self.winId())
        try:
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style = ex_style & ~WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
        except Exception:
            pass

    # -- Toggle edit mode (replaces broken click-and-hold) --

    def toggle_edit_mode(self) -> None:
        """Toggle between edit mode (draggable/resizable) and normal click-through mode."""
        if self._edit_mode:
            self.exit_edit_mode()
        else:
            self.enter_edit_mode()

    def enter_edit_mode(self) -> None:
        """Enter edit mode — overlay becomes interactive for drag/resize."""
        self._edit_mode = True
        self._remove_click_through()
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self._edit_idle_timer.start()  # Start 4s auto-lock countdown
        self.edit_mode_changed.emit(True)
        self.update()

    def exit_edit_mode(self) -> None:
        """Exit edit mode — save position and re-enable click-through."""
        self._edit_idle_timer.stop()
        self._edit_mode = False
        self._drag_active = False
        self._resize_mode = False
        self._drag_start = None
        self._save_position()
        self._save_height()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._set_click_through()
        self.edit_mode_changed.emit(False)
        self.update()

    def _on_edit_idle_timeout(self) -> None:
        """Auto-lock overlay after 4 seconds of no interaction."""
        if self._edit_mode and not self._drag_active and not self._resize_mode:
            self.exit_edit_mode()

    def _save_position(self) -> None:
        """Save overlay position to config."""
        saved_x, saved_y = self.x(), self.y()
        self._config.config_changed.disconnect(self._on_config_changed)
        self._config.set("overlay_x", saved_x)
        self._config.set("overlay_y", saved_y)
        self._config.config_changed.connect(self._on_config_changed)
        self._config.save()

    def _save_height(self) -> None:
        """Save overlay height to config."""
        self._config.config_changed.disconnect(self._on_config_changed)
        self._config.set("overlay_height", self.height())
        self._config.config_changed.connect(self._on_config_changed)
        self._config.save()

    def _is_in_resize_grip(self, pos: QPoint) -> bool:
        """Check if position is in the resize grip area (bottom-right corner)."""
        return (pos.x() >= self.width() - self._resize_grip_size and
                pos.y() >= self.height() - self._resize_grip_size)

    def mousePressEvent(self, event) -> None:
        if not self._edit_mode:
            super().mousePressEvent(event)
            return
        
        # Reset idle timer on any interaction
        self._edit_idle_timer.start()
        
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            
            # Check if clicking resize grip
            if self._is_in_resize_grip(pos):
                self._resize_mode = True
                self._resize_start_height = self.height()
                self._resize_start_y = event.globalPosition().toPoint().y()
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                event.accept()
                return
            
            # Start dragging
            self._drag_active = True
            self._drag_start = event.globalPosition().toPoint() - self.pos()
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            # Right-click exits edit mode
            self.exit_edit_mode()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not self._edit_mode:
            super().mouseMoveEvent(event)
            return
        
        pos = event.pos()
