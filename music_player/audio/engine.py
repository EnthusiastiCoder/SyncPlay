"""Audio playback engine using Qt Multimedia."""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# Supported audio extensions
SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac"}


class AudioEngine(QObject):
    """Manages audio playback via QMediaPlayer."""

    position_changed = pyqtSignal(int)   # current position in ms
    track_ended = pyqtSignal()
    state_changed = pyqtSignal(str)      # "playing", "paused", "stopped"
    duration_available = pyqtSignal(int)  # duration in ms after load
    error_occurred = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._current_file: Optional[str] = None
        self._state: str = "stopped"
        self._duration_ms: int = 0
        self._volume: float = 1.0

        # Qt Multimedia objects
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(self._volume)

        # Connect QMediaPlayer signals
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._player.errorOccurred.connect(self._on_error)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._duration_ms = duration_ms
        if duration_ms > 0:
            self.duration_available.emit(duration_ms)

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._state = "playing"
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._state = "paused"
        else:
            self._state = "stopped"
        self.state_changed.emit(self._state)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._state = "stopped"
            self.state_changed.emit(self._state)

    def _on_error(self, error: QMediaPlayer.Error, message: str) -> None:
        if error != QMediaPlayer.Error.NoError:
            self.error_occurred.emit(message)

    def load(self, file_path: str) -> bool:
        """Load an audio file. Returns True on success."""
        path = Path(file_path)
        if not path.exists():
            self.error_occurred.emit(f"File not found: {file_path}")
            return False

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            self.error_occurred.emit(f"Unsupported format: {path.suffix}")
            return False

        self.stop()
        self._current_file = file_path
        self._player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        return True

    def play(self) -> None:
        """Start or resume playback."""
        if not self._current_file:
            return
        self._player.play()

    def pause(self) -> None:
        """Pause playback."""
        if self._state == "playing":
            self._player.pause()

    def stop(self) -> None:
        """Stop playback."""
        self._player.stop()

    def seek(self, ms: int) -> None:
        """Seek to a position in milliseconds."""
        if not self._current_file:
            return
        ms = max(0, min(ms, self._duration_ms))
        self._player.setPosition(ms)

    def get_position_ms(self) -> int:
        """Get current playback position in milliseconds."""
        if self._state == "stopped":
            return 0
        return self._player.position()

    def get_duration_ms(self) -> int:
        """Get total duration in milliseconds."""
        return self._duration_ms

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)."""
        self._volume = max(0.0, min(1.0, volume))
        self._audio_output.setVolume(self._volume)

    def get_volume(self) -> float:
        return self._volume

    def is_busy(self) -> bool:
        """Check if audio is currently playing."""
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    @property
    def state(self) -> str:
        return self._state

    @property
    def current_file(self) -> Optional[str]:
        return self._current_file

    def cleanup(self) -> None:
        """Clean up resources."""
        self._player.stop()
        self._player.setSource(QUrl())
