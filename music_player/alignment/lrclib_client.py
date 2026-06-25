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

    def _extract_plain(data: Optional[dict]) -> Optional[dict]:
        if not data:
            return None
        plain = data.get("plainLyrics") or ""
        if not plain.strip():
            return None
        return {"plainLyrics": plain}

    # Stage 1: full params with duration
    params: dict = {"track_name": track_name}
    if artist_name:
        params["artist_name"] = artist_name
    if album_name:
        params["album_name"] = album_name
    if duration_sec > 0:
        params["duration"] = int(duration_sec)

    url = _API_GET + "?" + urllib.parse.urlencode(params)
    result = _extract_plain(_get(url, timeout))
    if result:
        return result

    # Stage 2: track + artist only (drop album and duration)
    if album_name or duration_sec > 0:
        params2: dict = {"track_name": track_name}
        if artist_name:
            params2["artist_name"] = artist_name
        url2 = _API_GET + "?" + urllib.parse.urlencode(params2)
        result = _extract_plain(_get(url2, timeout))
        if result:
            return result

    # Stage 3: free-text search
    q = " ".join(p for p in [track_name, artist_name] if p)
    url3 = _API_SEARCH + "?" + urllib.parse.urlencode({"q": q})
    req3 = urllib.request.Request(url3, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req3, timeout=timeout) as resp:
            hits = json.loads(resp.read().decode("utf-8"))
    except Exception:
        hits = []

    for hit in hits:
        result = _extract_plain(hit)
        if result:
            return result

    return None


def extract_audio_metadata(audio_path: str) -> dict:
    """Extract track metadata from an audio file using mutagen.
