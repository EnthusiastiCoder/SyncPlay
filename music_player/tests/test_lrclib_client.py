"""Unit tests for lrclib_client module."""

import json
import unittest
from unittest.mock import patch
import urllib.error

from music_player.alignment.lrclib_client import fetch_lyrics, extract_audio_metadata


class FakeHTTPResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def _ok(payload: dict) -> FakeHTTPResponse:
    return FakeHTTPResponse(json.dumps(payload).encode("utf-8"))


def _search_ok(results: list) -> FakeHTTPResponse:
    return FakeHTTPResponse(json.dumps(results).encode("utf-8"))


class TestFetchLyrics(unittest.TestCase):

    def test_returns_plain_lyrics_on_success(self):
        payload = {"plainLyrics": "Hello world\nSecond line", "syncedLyrics": "[00:01.00] Hello world"}
        with patch("urllib.request.urlopen", return_value=_ok(payload)):
            result = fetch_lyrics("Hello", "Artist", "Album", 180.0)
        self.assertIsNotNone(result)
        self.assertEqual(result["plainLyrics"], "Hello world\nSecond line")
        # syncedLyrics must NOT be in the result
        self.assertNotIn("syncedLyrics", result)

    def test_empty_title_returns_none_without_request(self):
        """Empty track name must return None immediately (no HTTP call)."""
        with patch("urllib.request.urlopen") as mock_open:
            result = fetch_lyrics("", "Queen", "", 354.0)
        self.assertIsNone(result)
        mock_open.assert_not_called()
