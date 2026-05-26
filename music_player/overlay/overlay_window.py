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
        
        # Update cursor based on position
        if not self._drag_active and not self._resize_mode:
            if self._is_in_resize_grip(pos):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeAllCursor)
        
        # Handle resize
        if self._resize_mode:
            delta_y = event.globalPosition().toPoint().y() - self._resize_start_y
            new_height = max(100, self._resize_start_height + delta_y)
            self.setFixedHeight(new_height)
            event.accept()
            return
        
        # Handle drag
        if self._drag_active and self._drag_start is not None:
            self.move(event.globalPosition().toPoint() - self._drag_start)
            event.accept()
            return
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if not self._edit_mode:
            super().mouseReleaseEvent(event)
            return
        
        # Reset idle timer after interaction ends
        self._edit_idle_timer.start()
        
        if self._resize_mode:
            self._resize_mode = False
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            event.accept()
            return
        
        if self._drag_active:
            self._drag_active = False
            self._drag_start = None
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            event.accept()
            return
        
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        """Escape exits edit mode."""
        if self._edit_mode and event.key() == Qt.Key.Key_Escape:
            self.exit_edit_mode()
            event.accept()
        else:
            super().keyPressEvent(event)

    # -- WLRC data and timing --

    def set_wlrc(self, wlrc: Optional[WlrcData]) -> None:
        """Set the word-level lyric data for rendering."""
        self._wlrc = wlrc
        self._lines = []
        self._last_line_index = -1
        self._anim_slots = []
        self._anim_timer.stop()
        self.update()
    
    def update_time(self, time_ms: int) -> None:
        """Update current playback time and refresh display."""
        self._current_time_ms = time_ms
        if self._wlrc is not None:
            self._lines = []
            prev, curr, nxt = self._wlrc.get_display_lines(time_ms)
            if prev:
                self._lines.append((prev.text, False))
            if curr:
                self._lines.append((curr.text, True))
            if nxt:
                self._lines.append((nxt.text, False))
            
            # Detect line change and trigger transition animation
            new_idx = self._wlrc.get_current_line_index(time_ms)
            if new_idx != self._last_line_index:
                self._start_line_transition(new_idx)
                self._last_line_index = new_idx
            
            # Auto-resize width to fit content
            self._auto_resize_width()
        
        # Trigger repaint so word-level coloring updates
        self.update()
    
    def _auto_resize_width(self) -> None:
        """Automatically resize overlay width to fit content."""
        if self._wlrc is None:
            return
        
        required_width = self._renderer.calculate_required_width(
            self._wlrc,
            self._current_time_ms
        )
        
        # Only resize if not in edit mode
        if not self._edit_mode:
            current_width = self.width()
            if abs(current_width - required_width) > 10:  # Avoid jitter
                # Keep the overlay centered on its current x position
                center_x = self.x() + current_width // 2
                new_x = center_x - required_width // 2
                self.setGeometry(new_x, self.y(), required_width, self.height())
    
    # -- Line transition animation --

    def _calc_stable_centers(self):
        """Calculate vertical center-y positions for the 3-line layout."""
        font_family = self._config.get("font_family", "Segoe UI")
        base_size = self._config.get("font_size_base", 28)
        ratio = self._config.get("font_ratio_side_lines", 0.75)
        side_size = max(8, int(base_size * ratio))

        base_font = QFont(font_family, base_size, QFont.Weight.Bold)
        side_font = QFont(font_family, side_size)

        base_h = QFontMetrics(base_font).height() + 8
        side_h = QFontMetrics(side_font).height() + 8

        total = side_h + base_h + side_h
        h = self.height()
        start = (h - total) / 2.0

        return {
            'prev': start + side_h / 2.0,
            'curr': start + side_h + base_h / 2.0,
            'next': start + side_h + base_h + side_h / 2.0,
            'exit': start - side_h / 2.0,
            'enter': start + total + side_h / 2.0,
            'base_size': base_size,
            'side_size': side_size,
        }

    @staticmethod
    def _lines_at_index(idx, lines):
        """Get (prev, curr, next) WlrcLine objects for a given line index."""
        n = len(lines)
        if idx < 0:
            return None, None, lines[0] if lines else None
        prev = lines[idx - 1] if idx > 0 else None
        curr = lines[idx] if idx < n else None
        nxt = lines[idx + 1] if idx < n - 1 else None
        return prev, curr, nxt

    def _start_line_transition(self, new_idx):
        """Build animation slots for the line transition."""
        old_idx = self._last_line_index
        centers = self._calc_stable_centers()
        base_sz = centers['base_size']
        side_sz = centers['side_size']
        lines = self._wlrc.lines if self._wlrc else []

        old_prev, old_curr, old_next = self._lines_at_index(old_idx, lines)
        new_prev, new_curr, new_next = self._lines_at_index(new_idx, lines)

        self._anim_slots = []

        W_BOLD = 700
        W_NORM = 400

        if new_idx == old_idx + 1:
            # Normal forward by 1 — smooth transition
            if old_prev is not None:
                self._anim_slots.append(_AnimSlot(
                    old_prev,
                    centers['prev'], centers['exit'],
                    side_sz, side_sz, 1.0, 0.0,
                    W_NORM, W_NORM,
                    False, True))
            if old_curr is not None:
                self._anim_slots.append(_AnimSlot(
                    old_curr,
                    centers['curr'], centers['prev'],
                    base_sz, side_sz, 1.0, 1.0,
                    W_BOLD, W_NORM,
                    False, True))
            if new_curr is not None:
                self._anim_slots.append(_AnimSlot(
                    new_curr,
                    centers['next'], centers['curr'],
                    side_sz, base_sz, 1.0, 1.0,
                    W_NORM, W_BOLD,
                    True, False))
            if new_next is not None:
                self._anim_slots.append(_AnimSlot(
                    new_next,
                    centers['enter'], centers['next'],
                    side_sz, side_sz, 0.0, 1.0,
                    W_NORM, W_NORM,
                    False, False))
        else:
            # Jump/seek — cross-fade old out, new in
            if old_prev is not None:
                self._anim_slots.append(_AnimSlot(
                    old_prev,
                    centers['prev'], centers['prev'],
                    side_sz, side_sz, 1.0, 0.0,
                    W_NORM, W_NORM,
                    False, True))
            if old_curr is not None:
                self._anim_slots.append(_AnimSlot(
                    old_curr,
                    centers['curr'], centers['curr'],
                    base_sz, base_sz, 1.0, 0.0,
                    W_BOLD, W_NORM,
                    False, True))
            if old_next is not None:
                self._anim_slots.append(_AnimSlot(
                    old_next,
                    centers['next'], centers['next'],
                    side_sz, side_sz, 1.0, 0.0,
                    W_NORM, W_NORM,
                    False, False))
            if new_prev is not None:
                self._anim_slots.append(_AnimSlot(
                    new_prev,
                    centers['prev'], centers['prev'],
                    side_sz, side_sz, 0.0, 1.0,
                    W_NORM, W_NORM,
                    False, True))
            if new_curr is not None:
                self._anim_slots.append(_AnimSlot(
                    new_curr,
                    centers['curr'], centers['curr'],
                    base_sz, base_sz, 0.0, 1.0,
                    W_NORM, W_BOLD,
                    True, False))
            if new_next is not None:
                self._anim_slots.append(_AnimSlot(
                    new_next,
                    centers['next'], centers['next'],
                    side_sz, side_sz, 0.0, 1.0,
                    W_NORM, W_NORM,
                    False, False))

        self._anim_elapsed.start()
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _on_anim_tick(self):
        """Advance animation timer and trigger repaint."""
        elapsed = self._anim_elapsed.elapsed()
        if elapsed >= self._ANIM_DURATION_MS:
            self._anim_timer.stop()
            self._anim_slots = []
        self.update()

    @staticmethod
    def _ease_in_out(t: float) -> float:
        """Linear easing for smooth, uniform animation."""
        return t

    def _paint_animated(self, painter: QPainter) -> None:
        """Draw lyric lines during a transition animation."""
        raw_t = min(1.0, self._anim_elapsed.elapsed() / self._ANIM_DURATION_MS)
        t = self._ease_in_out(raw_t)
        font_family = self._config.get("font_family", "Segoe UI")
        w = self.width()

        for slot in self._anim_slots:
            center_y = slot.cy0 + (slot.cy1 - slot.cy0) * t
            font_size = slot.sz0 + (slot.sz1 - slot.sz0) * t
            opacity = slot.a0 + (slot.a1 - slot.a0) * t
            font_weight = int(slot.w0 + (slot.w1 - slot.w0) * t)

            fs = max(8, int(font_size))
            font = QFont(font_family, fs)
            font.setWeight(QFont.Weight(font_weight))
            fm = QFontMetrics(font)
            y_top = int(center_y - (fm.height() + 8) / 2.0)

            self._renderer.draw_line_at(
                painter, slot.line, fs, y_top, w, opacity,
                self._current_time_ms, slot.active, slot.played,
                font_weight=font_weight,
            )

    def _paint_stable(self, painter: QPainter) -> None:
        """Draw lyric lines in the stable state (no transition)."""
        if self._wlrc is None:
            return

        prev, curr, nxt = self._wlrc.get_display_lines(self._current_time_ms)
        centers = self._calc_stable_centers()
        font_family = self._config.get("font_family", "Segoe UI")
        base_sz = centers['base_size']
        side_sz = centers['side_size']
        w = self.width()

        for line, size, active, played, pos_key in [
            (prev, side_sz, False, True, 'prev'),
            (curr, base_sz, True, False, 'curr'),
            (nxt, side_sz, False, False, 'next'),
        ]:
            if line is None:
                continue
            font = QFont(font_family, size,
                         QFont.Weight.Bold if active else QFont.Weight.Normal)
            fm = QFontMetrics(font)
            y_top = int(centers[pos_key] - (fm.height() + 8) / 2.0)
            self._renderer.draw_line_at(
                painter, line, size, y_top, w, 1.0,
                self._current_time_ms, active, played,
            )

    def set_display_text(self, prev_text: str, current_text: str, next_text: str) -> None:
        """Set display text for simple text mode (fallback when no WLRC)."""
        self._wlrc = None
        self._lines = [
            (prev_text, False),
            (current_text, True),
            (next_text, False),
        ]
        self.update()
    
    # -- Playback state handlers --
    
    def on_playback_paused(self) -> None:
        """Called when playback is paused - start auto-hide timer."""
        self._pause_hide_timer.start()
    
    def on_playback_resumed(self) -> None:
        """Called when playback is resumed - cancel auto-hide and fade in."""
        self._pause_hide_timer.stop()
        self._fade_in()
    
    def on_playback_stopped(self) -> None:
        """Called when playback is stopped - show overlay with upcoming lyrics."""
        self._pause_hide_timer.stop()
        self._fade_in()
    
    def _fade_out(self) -> None:
        """Fade overlay to transparent."""
        self._fade_animation.stop()
        self._fade_animation.setStartValue(self._opacity_effect.opacity())
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.start()
    
    def _fade_in(self) -> None:
        """Fade overlay to fully visible."""
        self._fade_animation.stop()
        self._fade_animation.setStartValue(self._opacity_effect.opacity())
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.start()

    # -- Painting --

    def paintEvent(self, event) -> None:
        """Draw the lyric lines on the transparent background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Draw edit-mode indicator
        if self._edit_mode:
            painter.setPen(QColor(100, 200, 255, 150))
            painter.setBrush(QColor(100, 200, 255, 20))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
            painter.setPen(QColor(255, 255, 255, 180))
            painter.drawText(self.rect().adjusted(8, 4, -8, 0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop, "Drag to move | Right-click or Esc to lock")
        
        # Draw resize grip indicator (bottom-right corner) only in edit mode
        if self._edit_mode and not self._resize_mode:
            grip_rect = self.rect()
            grip_x = grip_rect.width() - self._resize_grip_size
            grip_y = grip_rect.height() - self._resize_grip_size
            
            painter.setPen(QColor(255, 255, 255, 80))
            for i in range(3):
                offset = i * 4
                painter.drawLine(
                    grip_x + offset + 10, grip_y + self._resize_grip_size - 2,
                    grip_x + self._resize_grip_size - 2, grip_y + offset + 10
                )

        # Use animated or stable rendering if WLRC data is loaded
        if self._wlrc is not None:
            if self._anim_slots:
                self._paint_animated(painter)
            else:
                self._paint_stable(painter)
            painter.end()
            return

        # Fallback: simple text lines
        if not self._lines:
            painter.end()
            return

        font_family = self._config.get("font_family", "Segoe UI")
        base_size = self._config.get("font_size_base", 28)
        ratio = self._config.get("font_ratio_side_lines", 0.75)
        played_color = QColor(self._config.get("played_color", "#00FF00"))
        unplayed_color = QColor(self._config.get("unplayed_color", "#FFFFFF"))
        side_size = int(base_size * ratio)

        w = self.width()
        y_offset = 10

        for i, (text, is_current) in enumerate(self._lines):
            if not text:
                font_size = side_size if not is_current else base_size
                y_offset += font_size + 8
                continue

            if is_current:
                font = QFont(font_family, base_size, QFont.Weight.Bold)
                color = played_color
            else:
                font = QFont(font_family, side_size)
                color = unplayed_color

            painter.setFont(font)
            painter.setPen(color)
            fm = QFontMetrics(font)
            text_rect = fm.boundingRect(text)
            x = (w - text_rect.width()) // 2
            y_offset += fm.ascent()
            painter.drawText(x, y_offset, text)
            y_offset += fm.descent() + 8
