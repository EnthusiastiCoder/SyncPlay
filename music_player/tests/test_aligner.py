"""Tests for Aligner and ModelManager (with mocked stable-ts)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

from music_player.alignment.model_manager import ModelManager, MODEL_INFO
from music_player.alignment.aligner import AlignmentWorker
from music_player.models.wlrc import load_wlrc, WlrcData

app = QApplication.instance() or QApplication([])


# -- ModelManager tests --

class TestModelManager:

    def test_available_models(self):
        models = ModelManager.available_models()
        assert "tiny" in models
        assert "base" in models
        assert "small" in models
        assert "medium" in models

    def test_model_info(self):
        info = ModelManager.model_info("base")
        assert "size_mb" in info
        assert "params" in info

    def test_model_info_unknown(self):
        info = ModelManager.model_info("nonexistent")
        assert info == {}

    def test_is_model_cached_false(self, tmp_path):
        mm = ModelManager(cache_dir=tmp_path)
        assert not mm.is_model_cached("base")

    def test_is_model_cached_true(self, tmp_path):
        mm = ModelManager(cache_dir=tmp_path)
        (tmp_path / "base.pt").write_bytes(b"fake model data")
        assert mm.is_model_cached("base")

    def test_cached_models(self, tmp_path):
        mm = ModelManager(cache_dir=tmp_path)
        (tmp_path / "tiny.pt").write_bytes(b"fake")
        (tmp_path / "base.pt").write_bytes(b"fake")
        cached = mm.cached_models()
        assert "tiny" in cached
        assert "base" in cached
        assert "small" not in cached

    def test_delete_model(self, tmp_path):
        mm = ModelManager(cache_dir=tmp_path)
        (tmp_path / "base.pt").write_bytes(b"fake")
        assert mm.delete_model("base")
        assert not mm.is_model_cached("base")

    def test_delete_model_not_found(self, tmp_path):
        mm = ModelManager(cache_dir=tmp_path)
        assert not mm.delete_model("base")

    def test_cache_size(self, tmp_path):
        mm = ModelManager(cache_dir=tmp_path)
        (tmp_path / "base.pt").write_bytes(b"x" * 1048576)  # 1 MB
        size = mm.cache_size_mb()
        assert abs(size - 1.0) < 0.1


# -- AlignmentWorker tests (mocked stable-ts) --

class MockWord:
    def __init__(self, word, start, end):
        self.word = word
        self.start = start
        self.end = end


class MockSegment:
    def __init__(self, words):
        self.words = words


class MockResult:
    def __init__(self, segments):
        self.segments = segments


def make_mock_result():
    """Create a mock stable-ts alignment result."""
    return MockResult([
        MockSegment([
            MockWord("Hello", 1.0, 1.5),
            MockWord("world", 1.6, 2.8),
        ]),
        MockSegment([
            MockWord("This", 3.5, 3.8),
            MockWord("is", 3.9, 4.1),
            MockWord("a", 4.2, 4.3),
            MockWord("test", 4.4, 5.0),
        ]),
    ])


class TestAlignmentWorker:

    def test_result_to_wlrc_conversion(self, tmp_path):
        """Test that mock stable-ts result converts to valid WLRC."""
        audio_path = str(tmp_path / "test.mp3")
        Path(audio_path).write_bytes(b"fake audio")

        worker = AlignmentWorker(
            audio_path=audio_path,
            transcript="Hello world This is a test",
            model_name="base",
            language="en",
            output_path=str(tmp_path / "test.wlrc"),
        )

        result = make_mock_result()
        wlrc = worker._result_to_wlrc(result)

        assert isinstance(wlrc, WlrcData)
        assert len(wlrc.lines) == 2
        assert len(wlrc.lines[0].words) == 2
        assert len(wlrc.lines[1].words) == 4

        # Check word timestamps
        assert wlrc.lines[0].words[0].text == "Hello"
        assert wlrc.lines[0].words[0].start_ms == 1000
        assert wlrc.lines[0].words[0].end_ms == 1500

        assert wlrc.lines[1].words[3].text == "test"
        assert wlrc.lines[1].words[3].start_ms == 4400
        assert wlrc.lines[1].words[3].end_ms == 5000

    def test_result_to_wlrc_line_boundaries(self, tmp_path):
        """Line start/end derived from first/last word."""
        audio_path = str(tmp_path / "test.mp3")
        Path(audio_path).write_bytes(b"fake audio")

        worker = AlignmentWorker(audio_path=audio_path, transcript="x", model_name="base")
        result = make_mock_result()
        wlrc = worker._result_to_wlrc(result)

        assert wlrc.lines[0].start_ms == 1000
        assert wlrc.lines[0].end_ms == 2800
        assert wlrc.lines[1].start_ms == 3500
        assert wlrc.lines[1].end_ms == 5000

    def test_result_to_wlrc_empty_words_skipped(self, tmp_path):
        """Words with empty text after strip are skipped."""
        audio_path = str(tmp_path / "test.mp3")
        Path(audio_path).write_bytes(b"fake audio")

        worker = AlignmentWorker(audio_path=audio_path, transcript="x", model_name="base")
        result = MockResult([
            MockSegment([
                MockWord("Hello", 1.0, 1.5),
                MockWord("  ", 1.6, 1.7),  # whitespace-only, should be skipped
                MockWord("world", 1.8, 2.0),
            ])
        ])
        wlrc = worker._result_to_wlrc(result)
        assert len(wlrc.lines[0].words) == 2

    def test_default_output_path(self, tmp_path):
        worker = AlignmentWorker(
            audio_path=str(tmp_path / "song.mp3"),
            transcript="text",
        )
        assert worker.output_path == str(tmp_path / "song.wlrc")

    def test_cancel_flag(self):
        worker = AlignmentWorker(audio_path="x.mp3", transcript="text")
        assert not worker._cancelled
        worker.cancel()
        assert worker._cancelled
