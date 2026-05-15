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
