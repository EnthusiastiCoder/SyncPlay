"""Tests for WLRC data model, parser, and writer."""

import json
from pathlib import Path

import pytest

from music_player.models.wlrc import (
    WlrcWord, WlrcLine, WlrcMetadata, WlrcData,
    save_wlrc, load_wlrc,
)
