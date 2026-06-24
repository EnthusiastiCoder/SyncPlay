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
