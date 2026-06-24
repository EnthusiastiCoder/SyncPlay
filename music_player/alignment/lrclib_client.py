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
