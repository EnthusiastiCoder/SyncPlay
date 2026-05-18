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
    
    # Convert WLRC to JSON
    wlrc_dict = {
        "metadata": {
            "audio_file": wlrc.metadata.audio_file,
            "duration_ms": wlrc.metadata.duration_ms,
        },
        "lines": [
            {
                "start_ms": line.start_ms,
                "end_ms": line.end_ms,
                "words": [
                    {
                        "text": word.text,
                        "start_ms": word.start_ms,
                        "end_ms": word.end_ms,
                    }
                    for word in line.words
                ]
            }
            for line in wlrc.lines
        ]
    }
    
    wlrc_json = json.dumps(wlrc_dict, ensure_ascii=False)
    
    # Create or update TXXX:WLRC tag
    audio.tags.delall("TXXX:WLRC")  # Remove existing WLRC tag
    audio.tags.add(TXXX(encoding=3, desc="WLRC", text=wlrc_json))
    
    # Save tags
    try:
        audio.save()
    except Exception as e:
        raise Exception(f"Failed to save MP3 tags: {e}")


def extract_wlrc_from_mp3(audio_path: str) -> Optional[WlrcData]:
    """Extract WLRC data from MP3 file ID3 TXXX tag.
    
    Args:
        audio_path: Path to MP3 file
        
    Returns:
        WlrcData if found, None otherwise
        
    Raises:
        ValueError: If file is not an MP3
        Exception: If extraction fails
    """
    audio_path = Path(audio_path)
    
    if audio_path.suffix.lower() != '.mp3':
        raise ValueError("Only MP3 files are supported for extracting WLRC")
    
    # Load ID3 tags
    try:
        audio = MP3(str(audio_path), ID3=ID3)
        if audio.tags is None:
            return None
    except Exception:
        return None
    
    # Find TXXX:WLRC tag
    wlrc_tag = None
    for tag in audio.tags.getall("TXXX"):
        if tag.desc == "WLRC":
            wlrc_tag = tag
            break
    
    if wlrc_tag is None:
        return None
    
    # Parse JSON
    try:
        wlrc_json = wlrc_tag.text[0] if isinstance(wlrc_tag.text, list) else wlrc_tag.text
        wlrc_dict = json.loads(wlrc_json)
    except Exception:
        return None
    
    # Convert to WlrcData
    try:
        from music_player.models.wlrc import WlrcMetadata, WlrcLine, WlrcWord
        
        metadata = WlrcMetadata(
            audio_file=wlrc_dict["metadata"]["audio_file"],
            duration_ms=wlrc_dict["metadata"]["duration_ms"],
        )
        
        lines = []
        for line_dict in wlrc_dict["lines"]:
            words = [
                WlrcWord(
                    text=word_dict["text"],
                    start_ms=word_dict["start_ms"],
                    end_ms=word_dict["end_ms"],
                )
                for word_dict in line_dict["words"]
            ]
            lines.append(WlrcLine(
                start_ms=line_dict["start_ms"],
                end_ms=line_dict["end_ms"],
                words=words,
            ))
        
        return WlrcData(metadata=metadata, lines=lines)
    except Exception:
        return None


def has_embedded_wlrc(audio_path: str) -> bool:
    """Check if MP3 file has embedded WLRC data.
    
    Args:
        audio_path: Path to MP3 file
        
    Returns:
        True if WLRC data is embedded, False otherwise
    """
    try:
        return extract_wlrc_from_mp3(audio_path) is not None
    except Exception:
        return False


def remove_wlrc_from_mp3(audio_path: str) -> None:
    """Remove WLRC data from MP3 file.
    
    Args:
        audio_path: Path to MP3 file
        
    Raises:
        ValueError: If file is not an MP3
        Exception: If removal fails
    """
    audio_path = Path(audio_path)
