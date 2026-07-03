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
        
        # Set window icon
        icon_path = Path(__file__).parent / "resources" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Central tab widget
        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        # Add tabs
        self._player_tab = PlayerTab(config, self)
        self._alignment_tab = AlignmentTab(config, self)
        self._theme_tab = ThemeTab(config, self)
        self._subtitle_tab = SubtitleViewerTab(config, self)
        self._tabs.addTab(self._player_tab, "Player")
        self._tabs.addTab(self._alignment_tab, "Alignment Tool")
        self._tabs.addTab(self._theme_tab, "Themes")
        self._tabs.addTab(self._subtitle_tab, "Subtitle Viewer")

        # Overlay window
        self._overlay = OverlayWindow(config)
        self._overlay.hide_requested.connect(self._hide_overlay)
        self._overlay.settings_requested.connect(self._show_settings)

        # Connect player overlay toggle
        self._player_tab.overlay_toggle_requested.connect(self._toggle_overlay)

        # Connect alignment tab open-in-player
        self._alignment_tab.open_in_player_requested.connect(self._open_aligned_in_player)

        # Connect player wlrc loading
        self._player_tab.wlrc_loaded.connect(self._on_wlrc_loaded)
        
        # Connect theme changes
        self._theme_tab.theme_changed.connect(lambda theme: self._overlay.update())
        
        # Connect subtitle viewer load-in-player
        self._subtitle_tab.load_in_player_requested.connect(self._load_from_subtitle_viewer)

        # Connect playback clock to overlay
        self._player_tab.clock.position_updated.connect(self._overlay.update_time)
        self._player_tab.engine.state_changed.connect(self._on_playback_state_changed)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Space"), self, self._player_tab._toggle_play_pause)
        QShortcut(QKeySequence("Ctrl+O"), self, self._player_tab._open_file)
        QShortcut(QKeySequence("Ctrl+L"), self, self._toggle_overlay)
        QShortcut(QKeySequence("Ctrl+D"), self, self._overlay.toggle_edit_mode)
        QShortcut(QKeySequence("Ctrl+,"), self, self._show_settings)
        QShortcut(QKeySequence("Ctrl+Right"), self, self._player_tab._next_track)
        QShortcut(QKeySequence("Ctrl+Left"), self, self._player_tab._prev_track)

        # System tray
        self._setup_tray_icon()

    def _setup_tray_icon(self) -> None:
        """Create system tray icon with playback controls."""
        icon_path = Path(__file__).parent / "resources" / "icon.ico"
        tray_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
        
        self._tray_icon = QSystemTrayIcon(tray_icon, self)
        self._tray_icon.setToolTip("SyncPlay")
        
        # Tray menu
        tray_menu = QMenu()
        
        # Play/Pause action
        self._tray_play_pause_action = QAction("Play", self)
        self._tray_play_pause_action.triggered.connect(self._player_tab._toggle_play_pause)
        tray_menu.addAction(self._tray_play_pause_action)
        
        # Previous/Next
        prev_action = QAction("Previous", self)
        prev_action.triggered.connect(self._player_tab._prev_track)
        tray_menu.addAction(prev_action)
        
        next_action = QAction("Next", self)
        next_action.triggered.connect(self._player_tab._next_track)
        tray_menu.addAction(next_action)
        
        tray_menu.addSeparator()
