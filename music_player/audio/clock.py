"""Playback clock that emits position updates at regular intervals."""

from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from music_player.audio.engine import AudioEngine


class PlaybackClock(QObject):
    """High-frequency timer that polls AudioEngine position and emits updates."""

    position_updated = pyqtSignal(int)  # current position in ms
    track_finished = pyqtSignal()

    TICK_INTERVAL_MS = 33  # ~30 Hz

    def __init__(self, engine: AudioEngine, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._engine = engine
        self._timer = QTimer(self)
        self._timer.setInterval(self.TICK_INTERVAL_MS)
        self._timer.timeout.connect(self._on_tick)
        self._last_position = 0

        # Connect to engine state changes
        self._engine.state_changed.connect(self._on_state_changed)

    def _on_state_changed(self, state: str) -> None:
        """Start or stop the clock based on playback state."""
        if state == "playing":
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
            # Emit final position on pause/stop
            pos = self._engine.get_position_ms()
            self._last_position = pos
            self.position_updated.emit(pos)

    def _on_tick(self) -> None:
        """Poll engine position and emit update."""
        if not self._engine.is_busy() and self._engine.state == "playing":
            # Track ended naturally
            self._timer.stop()
            self.track_finished.emit()
            return

        pos = self._engine.get_position_ms()
        self._last_position = pos
        self.position_updated.emit(pos)

    @property
    def last_position(self) -> int:
        return self._last_position

    def start(self) -> None:
        """Manually start the clock."""
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        """Manually stop the clock."""
        self._timer.stop()
