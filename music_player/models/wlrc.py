"""Word-Level Lyric (.wlrc) data model, parser, and writer."""

import json
from bisect import bisect_right
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional
