"""Word-Level Lyric (.wlrc) data model, parser, and writer."""

import json
from bisect import bisect_right
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional


@dataclass
class WlrcWord:
    """A single word with timing information."""
    text: str
    start_ms: int
    end_ms: int

    def __post_init__(self):
        if self.start_ms < 0:
            raise ValueError(f"start_ms must be >= 0, got {self.start_ms}")
        if self.end_ms < self.start_ms:
            raise ValueError(f"end_ms ({self.end_ms}) must be >= start_ms ({self.start_ms})")


@dataclass
class WlrcLine:
    """A lyric line containing timed words."""
    start_ms: int
    end_ms: int
    words: list[WlrcWord] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Full line text reconstructed from words."""
        return " ".join(w.text for w in self.words)

    @property
    def has_word_timing(self) -> bool:
        """Whether this line has word-level timing data."""
        return len(self.words) > 0


@dataclass
class WlrcMetadata:
    """Metadata for a WLRC file."""
    title: str = ""
    artist: str = ""
    audio_file: str = ""
    duration_ms: int = 0


@dataclass
class WlrcData:
    """Complete word-level lyric data."""
    version: int = 1
    metadata: WlrcMetadata = field(default_factory=WlrcMetadata)
    lines: list[WlrcLine] = field(default_factory=list)

    # Cached line start times for binary search
    _line_starts: list[int] = field(default_factory=list, repr=False, compare=False)

    def __post_init__(self):
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild the binary search index of line start times."""
        self._line_starts = [line.start_ms for line in self.lines]

    def add_line(self, line: WlrcLine) -> None:
        """Add a line and update the index."""
        self.lines.append(line)
        self._line_starts.append(line.start_ms)

    def get_current_line_index(self, time_ms: int) -> int:
        """Get the index of the current line for a given playback time.

        Returns the index of the line that should be displayed as "current".
        Returns -1 if before the first line.
        Returns len(lines)-1 if after the last line starts.
        """
        if not self.lines:
            return -1

        # Find the rightmost line whose start_ms <= time_ms
        idx = bisect_right(self._line_starts, time_ms) - 1
        return idx

    def get_display_lines(self, time_ms: int) -> tuple[Optional['WlrcLine'], Optional['WlrcLine'], Optional['WlrcLine']]:
        """Get (previous, current, next) lines for display at a given time.

        Returns a tuple of (prev_line, current_line, next_line).
        Any element may be None if not available.
        """
        idx = self.get_current_line_index(time_ms)

        if idx < 0:
            # Before first line
            prev_line = None
            current_line = None
            next_line = self.lines[0] if self.lines else None
        else:
            prev_line = self.lines[idx - 1] if idx > 0 else None
            current_line = self.lines[idx]
            next_line = self.lines[idx + 1] if idx < len(self.lines) - 1 else None

        return prev_line, current_line, next_line


def _wlrc_to_dict(data: WlrcData) -> dict[str, Any]:
    """Convert WlrcData to a JSON-serializable dictionary."""
    return {
        "version": data.version,
        "metadata": {
            "title": data.metadata.title,
            "artist": data.metadata.artist,
            "audio_file": data.metadata.audio_file,
            "duration_ms": data.metadata.duration_ms,
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
                ],
            }
            for line in data.lines
        ],
    }


def _dict_to_wlrc(d: dict[str, Any]) -> WlrcData:
    """Convert a dictionary to WlrcData."""
    meta_d = d.get("metadata", {})
    metadata = WlrcMetadata(
        title=meta_d.get("title", ""),
        artist=meta_d.get("artist", ""),
        audio_file=meta_d.get("audio_file", ""),
        duration_ms=meta_d.get("duration_ms", 0),
    )
