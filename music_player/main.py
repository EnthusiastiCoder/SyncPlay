"""Music Player with Lyric Overlay — Main Entry Point."""

import multiprocessing
import os
import sys
import logging
import subprocess
import traceback

# Prevent torch from spawning duplicate processes on Windows
multiprocessing.freeze_support()

# --- GUI-mode safety: ensure stdout/stderr are never None ---------------
# When launched via pythonw.exe or .pyw, Python sets stdout/stderr to None.
# Many libraries (stable-whisper, tqdm, logging) call .write() on them and
# crash with "'NoneType' object has no attribute 'write'".
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# --- Suppress extra console windows on Windows -------------------------
# Torch / ffmpeg may spawn subprocesses that pop up a blank terminal.
# Override the default Popen flags so every subprocess is hidden.
_original_popen_init = subprocess.Popen.__init__

def _patched_popen_init(self, *args, **kwargs):
    if sys.platform == "win32":
        kwargs.setdefault("creationflags", 0)
        kwargs["creationflags"] |= subprocess.CREATE_NO_WINDOW
    _original_popen_init(self, *args, **kwargs)

subprocess.Popen.__init__ = _patched_popen_init

# Preload torch before Qt Multimedia to avoid DLL conflicts on Windows.
# Qt Multimedia bundles its own FFmpeg; if torch loads after, c10.dll fails.
try:
    import torch  # noqa: F401
except ImportError:
    pass

from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QMessageBox, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon, QAction

from pathlib import Path

from music_player.config import ConfigManager
from music_player.player.player_tab import PlayerTab
from music_player.overlay.overlay_window import OverlayWindow
from music_player.alignment.alignment_tab import AlignmentTab
from music_player.themes.app_theme_manager import AppThemeManager
from music_player.models.wlrc import load_wlrc
from music_player.player.settings_dialog import SettingsDialog
from music_player.themes.theme_tab import ThemeTab
from music_player.subtitle.subtitle_viewer_tab import SubtitleViewerTab

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with tabbed interface."""

    def __init__(self, config: ConfigManager):
        super().__init__()
        self._config = config
        self.setWindowTitle("SyncPlay")
        self.setMinimumSize(800, 500)
