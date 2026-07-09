"""Tests for LyricRenderer."""

import pytest
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QRect
from PyQt6.QtGui import QPainter, QImage

from music_player.config import ConfigManager
from music_player.models.wlrc import WlrcData, WlrcLine, WlrcWord, WlrcMetadata
from music_player.overlay.lyric_renderer import LyricRenderer

app = QApplication.instance() or QApplication([])


def make_sample_wlrc() -> WlrcData:
    return WlrcData(
        version=1,
        metadata=WlrcMetadata(title="Test", duration_ms=10000),
        lines=[
            WlrcLine(start_ms=1000, end_ms=3000, words=[
                WlrcWord("Hello", 1000, 1500),
                WlrcWord("world", 1600, 2800),
            ]),
            WlrcLine(start_ms=3500, end_ms=5000, words=[
                WlrcWord("This", 3500, 3800),
                WlrcWord("is", 3900, 4100),
                WlrcWord("a", 4200, 4300),
                WlrcWord("test", 4400, 5000),
            ]),
            WlrcLine(start_ms=6000, end_ms=8000, words=[
                WlrcWord("Final", 6000, 6500),
                WlrcWord("line", 6600, 8000),
            ]),
        ],
    )


def make_no_word_wlrc() -> WlrcData:
    """WLRC with line timing but no word timing (fallback mode)."""
    return WlrcData(
        version=1,
        metadata=WlrcMetadata(title="Test", duration_ms=10000),
        lines=[
            WlrcLine(start_ms=1000, end_ms=3000, words=[]),
            WlrcLine(start_ms=3500, end_ms=5000, words=[]),
        ],
    )


def render_to_image(renderer, wlrc, time_ms, width=800, height=200):
    """Render lyrics to a QImage and return it (for crash/smoke testing)."""
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    renderer.render(painter, QRect(0, 0, width, height), wlrc, time_ms)
    painter.end()
    return image


class TestLyricRenderer:

    def _make_renderer(self, tmp_path) -> LyricRenderer:
        config = ConfigManager(config_path=str(tmp_path / "cfg.json"))
        return LyricRenderer(config)

    def test_render_none_wlrc_no_crash(self, tmp_path):
        r = self._make_renderer(tmp_path)
        img = render_to_image(r, None, 0)
        assert img is not None

    def test_render_empty_wlrc_no_crash(self, tmp_path):
        r = self._make_renderer(tmp_path)
        wlrc = WlrcData()
        img = render_to_image(r, wlrc, 0)
        assert img is not None

    def test_render_before_first_line(self, tmp_path):
        r = self._make_renderer(tmp_path)
        wlrc = make_sample_wlrc()
        img = render_to_image(r, wlrc, 500)
        assert img is not None

    def test_render_at_first_line(self, tmp_path):
        r = self._make_renderer(tmp_path)
        wlrc = make_sample_wlrc()
        img = render_to_image(r, wlrc, 1200)
        assert img is not None

    def test_render_at_middle_line(self, tmp_path):
        r = self._make_renderer(tmp_path)
        wlrc = make_sample_wlrc()
        img = render_to_image(r, wlrc, 4000)
        assert img is not None

    def test_render_at_last_line(self, tmp_path):
        r = self._make_renderer(tmp_path)
        wlrc = make_sample_wlrc()
        img = render_to_image(r, wlrc, 7000)
        assert img is not None

    def test_render_after_all_lines(self, tmp_path):
        r = self._make_renderer(tmp_path)
        wlrc = make_sample_wlrc()
        img = render_to_image(r, wlrc, 99999)
        assert img is not None

    def test_render_no_word_timing_fallback(self, tmp_path):
        r = self._make_renderer(tmp_path)
        wlrc = make_no_word_wlrc()
        img = render_to_image(r, wlrc, 2000)
        assert img is not None

    def test_render_word_boundary_exact(self, tmp_path):
        """Render exactly at a word boundary timestamp."""
        r = self._make_renderer(tmp_path)
        wlrc = make_sample_wlrc()
        img = render_to_image(r, wlrc, 1600)  # Exactly at "world" start
        assert img is not None

    def test_render_various_sizes(self, tmp_path):
        """Render at different canvas sizes."""
        r = self._make_renderer(tmp_path)
        wlrc = make_sample_wlrc()
        for w, h in [(200, 100), (1920, 300), (400, 50)]:
            img = render_to_image(r, wlrc, 4000, width=w, height=h)
            assert img.width() == w
            assert img.height() == h
