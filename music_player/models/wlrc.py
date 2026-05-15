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
