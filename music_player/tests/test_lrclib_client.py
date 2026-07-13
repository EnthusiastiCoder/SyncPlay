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

    def test_whitespace_only_title_returns_none(self):
        with patch("urllib.request.urlopen") as mock_open:
            result = fetch_lyrics("   ", "Artist", "", 0.0)
        self.assertIsNone(result)
        mock_open.assert_not_called()

    def test_400_treated_as_not_found_falls_through_to_search(self):
        """Stage 1 returning 400 should not raise; search fallback should succeed."""
        err_400 = urllib.error.HTTPError(url="", code=400, msg="Bad Request", hdrs=None, fp=None)
        search_payload = [{"plainLyrics": "Found via search", "syncedLyrics": ""}]

        call_count = [0]

        def fake_urlopen(req, timeout=None):
            call_count[0] += 1
            if "api/search" in req.full_url:
                return _search_ok(search_payload)
            raise err_400

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = fetch_lyrics("Track", "Artist", "Album", 180.0)

        self.assertIsNotNone(result)
        self.assertEqual(result["plainLyrics"], "Found via search")

    def test_404_falls_through_to_search(self):
        err_404 = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
        search_payload = [{"plainLyrics": "Search result lyrics", "syncedLyrics": ""}]

        def fake_urlopen(req, timeout=None):
            if "api/search" in req.full_url:
                return _search_ok(search_payload)
            raise err_404
