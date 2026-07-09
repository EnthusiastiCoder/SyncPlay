"""Tests for PlaybackClock."""

import wave
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEventLoop, QTimer

from music_player.audio.engine import AudioEngine
from music_player.audio.clock import PlaybackClock

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


class TestPlaybackClock:

    def test_initial_state(self):
        engine = AudioEngine()
        clock = PlaybackClock(engine)
        assert clock.last_position == 0
        engine.cleanup()

    def test_clock_starts_on_play(self, tmp_path):
        engine = AudioEngine()
        clock = PlaybackClock(engine)
        wav_path = create_test_wav(str(tmp_path / "test.wav"), duration_sec=2.0)
        engine.load(wav_path)
        _process_events(500)
        engine.play()
        _process_events(500)
        assert clock._timer.isActive()
        engine.stop()
        _process_events(200)
        engine.cleanup()

    def test_clock_stops_on_pause(self, tmp_path):
        engine = AudioEngine()
        clock = PlaybackClock(engine)
        wav_path = create_test_wav(str(tmp_path / "test.wav"), duration_sec=2.0)
        engine.load(wav_path)
        _process_events(500)
        engine.play()
        _process_events(300)
        engine.pause()
        _process_events(300)
        assert not clock._timer.isActive()
        engine.cleanup()

    def test_clock_stops_on_stop(self, tmp_path):
        engine = AudioEngine()
        clock = PlaybackClock(engine)
        wav_path = create_test_wav(str(tmp_path / "test.wav"), duration_sec=2.0)
        engine.load(wav_path)
        _process_events(500)
        engine.play()
        _process_events(300)
        engine.stop()
        _process_events(300)
        assert not clock._timer.isActive()
        engine.cleanup()

    def test_position_updated_signal_emitted(self, tmp_path):
        engine = AudioEngine()
        clock = PlaybackClock(engine)
        positions = []
        clock.position_updated.connect(lambda p: positions.append(p))

        wav_path = create_test_wav(str(tmp_path / "test.wav"), duration_sec=2.0)
        engine.load(wav_path)
        _process_events(500)
        engine.play()
        _process_events(300)

        # Manually trigger tick
        clock._on_tick()

        assert len(positions) >= 1
        engine.stop()
        _process_events(200)
        engine.cleanup()

    def test_manual_start_stop(self):
        engine = AudioEngine()
        clock = PlaybackClock(engine)
        clock.start()
        assert clock._timer.isActive()
        clock.stop()
        assert not clock._timer.isActive()
        engine.cleanup()

    def test_tick_interval(self):
        engine = AudioEngine()
        clock = PlaybackClock(engine)
        assert clock.TICK_INTERVAL_MS == 33
        assert clock._timer.interval() == 33
        engine.cleanup()
