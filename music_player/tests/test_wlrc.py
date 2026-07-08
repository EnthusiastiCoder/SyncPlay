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
