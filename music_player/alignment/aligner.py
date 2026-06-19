"""Forced alignment engine using stable-ts / Whisper."""

import io
import os
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from music_player.models.wlrc import WlrcData, WlrcLine, WlrcWord, WlrcMetadata, save_wlrc
