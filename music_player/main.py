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
        
        # Repeat submenu
        repeat_menu = QMenu("Repeat", self)
        self._repeat_off_action = QAction("Off", self, checkable=True, checked=True)
        self._repeat_all_action = QAction("All", self, checkable=True)
        self._repeat_one_action = QAction("One", self, checkable=True)
        
        # Wire up repeat actions
        from music_player.player.player_tab import RepeatMode
        self._repeat_off_action.triggered.connect(lambda: self._set_repeat_mode(RepeatMode.OFF))
        self._repeat_all_action.triggered.connect(lambda: self._set_repeat_mode(RepeatMode.ALL))
        self._repeat_one_action.triggered.connect(lambda: self._set_repeat_mode(RepeatMode.ONE))
        
        repeat_menu.addAction(self._repeat_off_action)
        repeat_menu.addAction(self._repeat_all_action)
        repeat_menu.addAction(self._repeat_one_action)
        tray_menu.addMenu(repeat_menu)
        
        tray_menu.addSeparator()
        
        # Overlay edit mode
        self._tray_edit_overlay_action = QAction("Edit Overlay Position", self)
        self._tray_edit_overlay_action.triggered.connect(self._overlay.toggle_edit_mode)
        tray_menu.addAction(self._tray_edit_overlay_action)
        
        # Update tray text when edit mode changes
        self._overlay.edit_mode_changed.connect(self._on_overlay_edit_mode_changed)
        
        tray_menu.addSeparator()
        
        # Show window
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self._show_from_tray)
        tray_menu.addAction(show_action)
        
        # Quit
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)
        
        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()
        
        # Update play/pause text based on state
        self._player_tab.engine.state_changed.connect(self._update_tray_play_pause)

    def _update_tray_play_pause(self, state: str) -> None:
        """Update tray play/pause action text based on playback state."""
        if state == "playing":
            self._tray_play_pause_action.setText("Pause")
        else:
            self._tray_play_pause_action.setText("Play")

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation (double-click to show window)."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        """Show and raise the main window."""
        self.show()
        self.raise_()
        self.activateWindow()

    def _set_repeat_mode(self, mode) -> None:
        """Set repeat mode from tray menu."""
        self._player_tab.set_repeat_mode(mode)
        # Update checkmarks
        from music_player.player.player_tab import RepeatMode
        self._repeat_off_action.setChecked(mode == RepeatMode.OFF)
        self._repeat_all_action.setChecked(mode == RepeatMode.ALL)
        self._repeat_one_action.setChecked(mode == RepeatMode.ONE)

    def _on_overlay_edit_mode_changed(self, editing: bool) -> None:
        """Update tray menu text when overlay edit mode changes."""
        if editing:
            self._tray_edit_overlay_action.setText("Lock Overlay Position")
        else:
            self._tray_edit_overlay_action.setText("Edit Overlay Position")

    def _quit_app(self) -> None:
        """Actually quit the application — stop playback, close overlay, terminate."""
        self._player_tab.engine.stop()
        self._player_tab.engine.cleanup()
        self._overlay.close()
        self._tray_icon.hide()
        self._force_quit = True
        QApplication.quit()

    def closeEvent(self, event) -> None:
        """Minimize to tray instead of quitting (unless force-quit)."""
        if getattr(self, '_force_quit', False):
            event.accept()
            return
        event.ignore()
        self.hide()
        self._tray_icon.showMessage(
            "SyncPlay",
            "Application minimized to system tray",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def _toggle_overlay(self) -> None:
        visible = not self._overlay.isVisible()
        if visible:
            self._overlay.show()
        else:
            self._overlay.hide()
        self._player_tab._overlay_toggle.setChecked(visible)

    def _hide_overlay(self) -> None:
        self._overlay.hide()
        self._player_tab._overlay_toggle.setChecked(False)

    def _on_playback_state_changed(self, state: str) -> None:
        """Handle overlay visibility and animations based on playback state."""
        if state == "playing":
            if not self._overlay.isVisible():
                self._overlay.show()
            self._overlay.on_playback_resumed()
        elif state == "paused":
            self._overlay.on_playback_paused()
        elif state == "stopped":
            self._overlay.on_playback_stopped()

    def _on_wlrc_loaded(self, wlrc) -> None:
        """Handle wlrc auto-detection from player tab."""
        if wlrc is not None:
            self._overlay.set_wlrc(wlrc)
        else:
            self._overlay.set_wlrc(None)
            self._overlay.set_display_text("", "No lyrics loaded", "")

    def _open_aligned_in_player(self, audio_path: str, wlrc_path: str) -> None:
        """Load aligned audio + lyrics into the player."""
        try:
            from music_player.models.wlrc_embed import extract_wlrc_from_mp3
