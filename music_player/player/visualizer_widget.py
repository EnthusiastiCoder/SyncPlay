"""Animated waveform bar visualizer widget for the player tab."""

import math
import random

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPen


_BAR_COUNT = 32
_TICK_MS = 33        # ~30 Hz
_DECAY_RATE = 0.08   # fraction to decay per tick when idle/paused
_RISE_RATE = 0.18    # fraction to rise per tick when playing
_MIN_HEIGHT = 0.03   # minimum bar height fraction (always visible when playing)
_MAX_HEIGHT = 0.92   # maximum bar height fraction


class VisualizerWidget(QWidget):
    """Simulated waveform-bar equalizer that pulses during playback."""

    def __init__(self, accent_color: str = "#89b4fa", parent=None):
        super().__init__(parent)
        self._accent_color = accent_color
        self._is_playing = False

        # Bar heights as floats 0.0–1.0
        self._heights = [0.0] * _BAR_COUNT
        # Target heights (random targets updated periodically)
        self._targets = [0.0] * _BAR_COUNT
        # Phase offsets for organic wave-like movement
        self._phases = [random.uniform(0, math.tau) for _ in range(_BAR_COUNT)]
        self._tick = 0

        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    def set_accent_color(self, color: str) -> None:
        self._accent_color = color
        self.update()

    def set_playing(self, playing: bool) -> None:
        self._is_playing = playing
        if not playing:
            # Randomize all targets to 0 so bars decay cleanly
            self._targets = [0.0] * _BAR_COUNT

    def _on_tick(self) -> None:
        self._tick += 1

        if self._is_playing:
            # Refresh targets every ~8 ticks (~250ms) for organic motion
            if self._tick % 8 == 0:
                self._randomize_targets()

            # Interpolate towards targets
            for i in range(_BAR_COUNT):
                diff = self._targets[i] - self._heights[i]
                if diff > 0:
                    self._heights[i] += diff * _RISE_RATE
                else:
                    self._heights[i] += diff * _DECAY_RATE
                self._heights[i] = max(_MIN_HEIGHT, min(_MAX_HEIGHT, self._heights[i]))
        else:
            # Decay all bars to 0
            changed = False
            for i in range(_BAR_COUNT):
                if self._heights[i] > 0.001:
                    self._heights[i] *= (1.0 - _DECAY_RATE)
                    changed = True
                else:
                    self._heights[i] = 0.0
            if not changed:
                return  # Nothing to repaint

        self.update()

    def _randomize_targets(self) -> None:
        """Generate new smooth random target heights with a wave-like shape."""
        t = self._tick * _TICK_MS / 1000.0
        for i in range(_BAR_COUNT):
            # Combine two sine waves for organic feel
            x = i / (_BAR_COUNT - 1)
            wave1 = 0.5 + 0.4 * math.sin(self._phases[i] + t * 1.7)
            wave2 = 0.5 + 0.3 * math.sin(self._phases[i] * 1.3 + t * 2.9)
            # Gaussian envelope — taller in the middle, shorter at edges
            envelope = 0.4 + 0.6 * math.exp(-((x - 0.5) ** 2) / 0.12)
            h = ((wave1 + wave2) / 2.0) * envelope
            self._targets[i] = max(_MIN_HEIGHT, min(_MAX_HEIGHT, h))

    def paintEvent(self, event) -> None:
        if not self._heights:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#181825"))

        bar_gap = 2
        total_gap = bar_gap * (_BAR_COUNT - 1)
        bar_w = max(2, (w - total_gap) / _BAR_COUNT)

        accent = QColor(self._accent_color)
        top_color = QColor(accent)
        top_color.setAlphaF(0.95)
        bottom_color = QColor(accent)
        bottom_color.setHsvF(
            accent.hsvHueF(),
            min(1.0, accent.hsvSaturationF() * 0.6),
            min(1.0, accent.valueF() * 0.55),
        )
        bottom_color.setAlphaF(0.5)

        for i, height_frac in enumerate(self._heights):
            if height_frac < 0.002:
                continue

            x = i * (bar_w + bar_gap)
            bar_h = max(2.0, height_frac * (h - 4))
            y = h - bar_h - 2

            rect = QRectF(x, y, bar_w, bar_h)

            grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            grad.setColorAt(0.0, top_color)
            grad.setColorAt(1.0, bottom_color)

            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            radius = min(bar_w / 2.0, 3.0)
            painter.drawRoundedRect(rect, radius, radius)

        painter.end()
