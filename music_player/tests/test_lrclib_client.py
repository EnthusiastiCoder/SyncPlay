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
