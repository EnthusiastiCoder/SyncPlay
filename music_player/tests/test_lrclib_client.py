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

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = fetch_lyrics("Unknown Track", "Artist", "", 0.0)

        self.assertIsNotNone(result)
        self.assertEqual(result["plainLyrics"], "Search result lyrics")

    def test_all_stages_fail_returns_none(self):
        err_404 = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)

        def fake_urlopen(req, timeout=None):
            if "api/search" in req.full_url:
                return _search_ok([])  # empty search results
            raise err_404

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = fetch_lyrics("zzz_nonexistent", "zzz_artist", "", 0.0)
        self.assertIsNone(result)

    def test_raises_on_500_server_error(self):
        err_500 = urllib.error.HTTPError(url="", code=500, msg="Server Error", hdrs=None, fp=None)
        with patch("urllib.request.urlopen", side_effect=err_500):
            with self.assertRaises(urllib.error.HTTPError):
                fetch_lyrics("Track", "", "", 0.0)

    def test_null_plain_lyrics_skipped_uses_search(self):
        """If stage 1 returns null plainLyrics, should fall through to search."""
        stage1_payload = {"plainLyrics": None, "syncedLyrics": "[00:01.00] line"}
        search_payload = [{"plainLyrics": "Real lyrics here", "syncedLyrics": ""}]

        def fake_urlopen(req, timeout=None):
            if "api/search" in req.full_url:
                return _search_ok(search_payload)
            return _ok(stage1_payload)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = fetch_lyrics("Instrumental", "Artist", "", 120.0)
        self.assertIsNotNone(result)
        self.assertEqual(result["plainLyrics"], "Real lyrics here")

    def test_duration_zero_not_sent(self):
        captured_urls = []
        payload = {"plainLyrics": "lyrics", "syncedLyrics": ""}

        def fake_urlopen(req, timeout=None):
            captured_urls.append(req.full_url)
            return _ok(payload)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            fetch_lyrics("Track", "", "", 0.0)

        self.assertTrue(len(captured_urls) > 0)
        self.assertNotIn("duration", captured_urls[0])

    def test_stage2_skipped_when_no_album_or_duration(self):
        """Without album or duration, stage 2 is redundant so only 2 calls (get + search)."""
        payload = {"plainLyrics": None, "syncedLyrics": ""}
        search_payload = [{"plainLyrics": "search hit", "syncedLyrics": ""}]
        call_log = []

        def fake_urlopen(req, timeout=None):
            call_log.append(req.full_url)
            if "api/search" in req.full_url:
                return _search_ok(search_payload)
            return _ok(payload)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = fetch_lyrics("Track", "Artist", "", 0.0)

        get_calls = [u for u in call_log if "api/get" in u]
        self.assertEqual(len(get_calls), 1, "Stage 2 should be skipped when no album/duration")
        self.assertIsNotNone(result)

    def test_url_includes_track_name(self):
        payload = {"plainLyrics": "lyrics", "syncedLyrics": ""}
        captured_urls = []
