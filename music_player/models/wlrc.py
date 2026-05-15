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
