"""Tests for AudioEngine (QMediaPlayer-based)."""

import time
import wave
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEventLoop, QTimer

from music_player.audio.engine import AudioEngine, SUPPORTED_EXTENSIONS

app = QApplication.instance() or QApplication([])


def _process_events(timeout_ms: int = 500) -> None:
    """Process Qt events for up to timeout_ms to let async signals fire."""
    loop = QEventLoop()
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()


def create_test_wav(path: str, duration_sec: float = 1.0, sample_rate: int = 44100) -> str:
    """Create a minimal WAV file for testing."""
    n_samples = int(sample_rate * duration_sec)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_samples)
    return path


class TestAudioEngine:

    def test_initial_state(self):
        engine = AudioEngine()
        assert engine.state == "stopped"
        assert engine.current_file is None
        assert engine.get_position_ms() == 0
        assert engine.get_duration_ms() == 0
        engine.cleanup()

    def test_load_valid_file(self, tmp_path):
        engine = AudioEngine()
        wav_path = create_test_wav(str(tmp_path / "test.wav"), duration_sec=0.5)
        assert engine.load(wav_path) is True
        assert engine.current_file == wav_path
        # QMediaPlayer reports duration asynchronously
        _process_events(800)
        assert engine.get_duration_ms() > 0
        engine.cleanup()

    def test_load_nonexistent_file(self):
        engine = AudioEngine()
        errors = []
        engine.error_occurred.connect(lambda msg: errors.append(msg))
        assert engine.load("nonexistent.wav") is False
        assert len(errors) == 1
        assert "not found" in errors[0].lower()
        engine.cleanup()

    def test_load_unsupported_format(self, tmp_path):
        engine = AudioEngine()
        errors = []
        engine.error_occurred.connect(lambda msg: errors.append(msg))
        bad_file = tmp_path / "test.xyz"
        bad_file.write_text("not audio")
        assert engine.load(str(bad_file)) is False
        assert len(errors) == 1
        assert "unsupported" in errors[0].lower()
        engine.cleanup()

    def test_play_pause_stop(self, tmp_path):
        engine = AudioEngine()
        wav_path = create_test_wav(str(tmp_path / "test.wav"), duration_sec=2.0)
        engine.load(wav_path)
        _process_events(500)

        states = []
        engine.state_changed.connect(lambda s: states.append(s))

        engine.play()
        _process_events(300)
        assert engine.state == "playing"

        engine.pause()
        _process_events(300)
        assert engine.state == "paused"

        engine.play()  # resume
        _process_events(300)
        assert engine.state == "playing"

        engine.stop()
        _process_events(300)
        assert engine.state == "stopped"

        assert "playing" in states
        assert "paused" in states
        assert "stopped" in states
        engine.cleanup()

    def test_volume(self):
        engine = AudioEngine()
        engine.set_volume(0.5)
        assert engine.get_volume() == 0.5

        engine.set_volume(-1.0)
        assert engine.get_volume() == 0.0

        engine.set_volume(2.0)
        assert engine.get_volume() == 1.0
        engine.cleanup()

    def test_play_without_load_does_nothing(self):
        engine = AudioEngine()
        engine.play()
        _process_events(200)
        assert engine.state == "stopped"
        engine.cleanup()

    def test_seek_without_load_does_nothing(self):
        engine = AudioEngine()
        engine.seek(5000)
        assert engine.state == "stopped"
        engine.cleanup()

    def test_supported_extensions(self):
        assert ".mp3" in SUPPORTED_EXTENSIONS
        assert ".wav" in SUPPORTED_EXTENSIONS
        assert ".ogg" in SUPPORTED_EXTENSIONS
        assert ".flac" in SUPPORTED_EXTENSIONS

    def test_duration_signal_emitted(self, tmp_path):
        engine = AudioEngine()
        durations = []
        engine.duration_available.connect(lambda d: durations.append(d))
        wav_path = create_test_wav(str(tmp_path / "test.wav"), duration_sec=1.0)
        engine.load(wav_path)
        _process_events(800)
        assert len(durations) >= 1
        # Duration should be approximately 1000ms (tolerance for encoding)
        assert abs(durations[-1] - 1000) < 200
        engine.cleanup()
