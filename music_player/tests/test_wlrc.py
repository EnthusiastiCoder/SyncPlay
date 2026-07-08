"""Tests for WLRC data model, parser, and writer."""

import json
from pathlib import Path

import pytest

from music_player.models.wlrc import (
    WlrcWord, WlrcLine, WlrcMetadata, WlrcData,
    save_wlrc, load_wlrc,
)


def make_sample_wlrc() -> WlrcData:
    """Create a sample WlrcData for testing."""
    return WlrcData(
        version=1,
        metadata=WlrcMetadata(
            title="Test Song",
            artist="Test Artist",
            audio_file="test.mp3",
            duration_ms=10000,
        ),
        lines=[
            WlrcLine(
                start_ms=1000,
                end_ms=3000,
                words=[
                    WlrcWord("Hello", 1000, 1500),
                    WlrcWord("world", 1600, 2800),
                ],
            ),
            WlrcLine(
                start_ms=3500,
                end_ms=5000,
                words=[
                    WlrcWord("This", 3500, 3800),
                    WlrcWord("is", 3900, 4100),
                    WlrcWord("a", 4200, 4300),
                    WlrcWord("test", 4400, 5000),
                ],
            ),
            WlrcLine(
                start_ms=6000,
                end_ms=8000,
                words=[
                    WlrcWord("Final", 6000, 6500),
                    WlrcWord("line", 6600, 8000),
                ],
            ),
        ],
    )


class TestWlrcWord:
    def test_valid_word(self):
        w = WlrcWord("hello", 100, 200)
        assert w.text == "hello"
        assert w.start_ms == 100
        assert w.end_ms == 200

    def test_negative_start_raises(self):
        with pytest.raises(ValueError, match="start_ms"):
            WlrcWord("bad", -1, 100)

    def test_end_before_start_raises(self):
        with pytest.raises(ValueError, match="end_ms"):
            WlrcWord("bad", 200, 100)

    def test_zero_duration_word(self):
        w = WlrcWord("ok", 100, 100)
        assert w.start_ms == w.end_ms


class TestWlrcLine:
    def test_text_property(self):
        line = WlrcLine(
            start_ms=0, end_ms=1000,
            words=[WlrcWord("Hello", 0, 500), WlrcWord("world", 600, 1000)]
        )
        assert line.text == "Hello world"

    def test_empty_words(self):
        line = WlrcLine(start_ms=0, end_ms=1000, words=[])
        assert line.text == ""
        assert not line.has_word_timing

    def test_has_word_timing(self):
        line = WlrcLine(
            start_ms=0, end_ms=1000,
            words=[WlrcWord("test", 0, 1000)]
        )
        assert line.has_word_timing


class TestWlrcData:
    def test_get_current_line_index_empty(self):
        data = WlrcData()
        assert data.get_current_line_index(0) == -1

    def test_get_current_line_index_before_first(self):
        data = make_sample_wlrc()
        assert data.get_current_line_index(0) == -1
        assert data.get_current_line_index(999) == -1

    def test_get_current_line_index_at_first(self):
        data = make_sample_wlrc()
        assert data.get_current_line_index(1000) == 0

    def test_get_current_line_index_between_lines(self):
        data = make_sample_wlrc()
        # Between line 0 (ends 3000) and line 1 (starts 3500)
        assert data.get_current_line_index(3200) == 0

    def test_get_current_line_index_at_second_line(self):
        data = make_sample_wlrc()
        assert data.get_current_line_index(3500) == 1

    def test_get_current_line_index_at_last_line(self):
        data = make_sample_wlrc()
        assert data.get_current_line_index(6000) == 2

    def test_get_current_line_index_after_last(self):
        data = make_sample_wlrc()
        assert data.get_current_line_index(99999) == 2

    def test_get_display_lines_before_first(self):
        data = make_sample_wlrc()
        prev, curr, nxt = data.get_display_lines(500)
        assert prev is None
        assert curr is None
        assert nxt is not None
        assert nxt.text == "Hello world"

    def test_get_display_lines_at_first(self):
        data = make_sample_wlrc()
        prev, curr, nxt = data.get_display_lines(1000)
        assert prev is None
        assert curr is not None
        assert curr.text == "Hello world"
        assert nxt is not None
        assert nxt.text == "This is a test"

    def test_get_display_lines_at_middle(self):
        data = make_sample_wlrc()
        prev, curr, nxt = data.get_display_lines(4000)
        assert prev is not None
        assert prev.text == "Hello world"
        assert curr is not None
        assert curr.text == "This is a test"
        assert nxt is not None
        assert nxt.text == "Final line"

    def test_get_display_lines_at_last(self):
        data = make_sample_wlrc()
        prev, curr, nxt = data.get_display_lines(7000)
        assert prev is not None
        assert prev.text == "This is a test"
        assert curr is not None
        assert curr.text == "Final line"
        assert nxt is None

    def test_add_line(self):
        data = WlrcData()
        line = WlrcLine(start_ms=0, end_ms=1000, words=[WlrcWord("test", 0, 1000)])
        data.add_line(line)
        assert len(data.lines) == 1
        assert data.get_current_line_index(500) == 0


class TestSaveLoadWlrc:
    def test_round_trip(self, tmp_path):
        original = make_sample_wlrc()
        path = str(tmp_path / "test.wlrc")
        save_wlrc(original, path)
        loaded = load_wlrc(path)

        assert loaded.version == original.version
        assert loaded.metadata.title == original.metadata.title
        assert loaded.metadata.artist == original.metadata.artist
        assert loaded.metadata.audio_file == original.metadata.audio_file
        assert loaded.metadata.duration_ms == original.metadata.duration_ms
        assert len(loaded.lines) == len(original.lines)

        for orig_line, load_line in zip(original.lines, loaded.lines):
            assert load_line.start_ms == orig_line.start_ms
            assert load_line.end_ms == orig_line.end_ms
            assert len(load_line.words) == len(orig_line.words)
            for orig_word, load_word in zip(orig_line.words, load_line.words):
                assert load_word.text == orig_word.text
                assert load_word.start_ms == orig_word.start_ms
                assert load_word.end_ms == orig_word.end_ms

    def test_save_creates_file(self, tmp_path):
        data = make_sample_wlrc()
        path = str(tmp_path / "subdir" / "test.wlrc")
        save_wlrc(data, path)
        assert Path(path).exists()

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_wlrc("nonexistent.wlrc")
