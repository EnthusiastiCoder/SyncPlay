"""Embed and extract WLRC data in MP3 ID3 tags."""

import json
from pathlib import Path
from typing import Optional

from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TXXX

from music_player.models.wlrc import WlrcData


def embed_wlrc_in_mp3(audio_path: str, wlrc: WlrcData) -> None:
    """Embed WLRC data into MP3 file as ID3 TXXX tag.
    
    Args:
        audio_path: Path to MP3 file
        wlrc: WLRC data to embed
        
    Raises:
        ValueError: If file is not an MP3
        Exception: If embedding fails
    """
    audio_path = Path(audio_path)
    
    if audio_path.suffix.lower() != '.mp3':
        raise ValueError("Only MP3 files are supported for embedding WLRC")
    
    # Load or create ID3 tags
    try:
        audio = MP3(str(audio_path), ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
    except Exception as e:
        raise Exception(f"Failed to load MP3 file: {e}")
