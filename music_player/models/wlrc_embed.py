"""Embed and extract WLRC data in MP3 ID3 tags."""

import json
from pathlib import Path
from typing import Optional

from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TXXX

from music_player.models.wlrc import WlrcData
