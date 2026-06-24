"""Client for the lrclib.net lyrics API."""

import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Optional


_USER_AGENT = "SyncPlay/1.0 (https://github.com/user/syncplay)"
_API_GET = "https://lrclib.net/api/get"
_API_SEARCH = "https://lrclib.net/api/search"


def _get(url: str, timeout: int) -> Optional[dict]:
    """GET a URL and return parsed JSON, or None on 404. Raises on other errors."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (404, 400):
            return None
        raise


def fetch_lyrics(
    track_name: str,
    artist_name: str = "",
    album_name: str = "",
    duration_sec: float = 0.0,
    timeout: int = 10,
) -> Optional[dict]:
    """Fetch plain lyrics from lrclib.net using a 3-stage fallback strategy.

    Stage 1: GET /api/get with track + artist + album + duration (most precise).
    Stage 2: GET /api/get with track + artist only (no album/duration).
    Stage 3: GET /api/search?q=<track artist> and take the first result.

    Returns a dict with key 'plainLyrics' (str, may be empty), or None if
    nothing was found.  The 'syncedLyrics' key is intentionally omitted.
    """
    track_name = track_name.strip()
    if not track_name:
        return None

    artist_name = artist_name.strip()
    album_name = album_name.strip()
