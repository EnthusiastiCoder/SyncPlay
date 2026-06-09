"""Music Player tab UI with playback controls and playlist."""

import os
import random
from pathlib import Path
from typing import Optional
from enum import Enum

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QFileDialog, QListWidget, QListWidgetItem, QSizePolicy,
    QStyle,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon


class RepeatMode(Enum):
    """Repeat mode for playlist playback."""
    OFF = "off"
    ALL = "all"
    ONE = "one"

from music_player.config import ConfigManager
from music_player.audio.engine import AudioEngine, SUPPORTED_EXTENSIONS
from music_player.audio.clock import PlaybackClock
from music_player.models.wlrc import load_wlrc
from music_player.models.wlrc_embed import extract_wlrc_from_mp3
from music_player.utils.time_utils import ms_to_display
from music_player.player.widgets import ToggleSwitch
from music_player.player.visualizer_widget import VisualizerWidget


class PlayerTab(QWidget):
    """Main player tab with audio controls and playlist."""

    overlay_toggle_requested = pyqtSignal()
    wlrc_loaded = pyqtSignal(object)  # WlrcData or None

    def __init__(self, config: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._config = config

        # Audio subsystem
        self._engine = AudioEngine(self)
        self._clock = PlaybackClock(self._engine, self)

        # Track seeking state
        self._is_seeking = False
        self._playlist: list[str] = []
        self._current_index: int = -1
        
        # Playback modes
        self._repeat_mode = RepeatMode.OFF
        self._shuffle_enabled = False
        self._shuffle_history: list[int] = []

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # -- Now Playing label --
        self._now_playing_label = QLabel("No track loaded")
        self._now_playing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._now_playing_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self._now_playing_label)

        # -- Audio visualizer --
        accent = self._config.get("played_color", "#89b4fa")
        self._visualizer = VisualizerWidget(accent_color=accent, parent=self)
        layout.addWidget(self._visualizer)

        # -- Time + Seek bar --
        seek_layout = QHBoxLayout()
        self._time_current = QLabel("0:00")
        self._time_current.setFixedWidth(60)
        self._time_current.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setRange(0, 0)
        self._seek_slider.setSingleStep(1000)
        self._seek_slider.setPageStep(5000)

        self._time_total = QLabel("0:00")
        self._time_total.setFixedWidth(60)
        self._time_total.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        seek_layout.addWidget(self._time_current)
        seek_layout.addWidget(self._seek_slider)
        seek_layout.addWidget(self._time_total)
        layout.addLayout(seek_layout)

        # -- Playback controls --
        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_layout.setSpacing(6)

        style = self.style()

        self._btn_prev = QPushButton()
        self._btn_prev.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self._btn_prev.setFixedSize(40, 36)
        self._btn_prev.setToolTip("Previous")

        self._btn_play_pause = QPushButton()
        self._btn_play_pause.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self._btn_play_pause.setFixedSize(48, 36)
        self._btn_play_pause.setToolTip("Play / Pause")

        self._btn_next = QPushButton()
        self._btn_next.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        self._btn_next.setFixedSize(40, 36)
        self._btn_next.setToolTip("Next")

        self._btn_repeat = QPushButton("Repeat: Off")
        self._btn_repeat.setFixedSize(100, 36)

        self._btn_shuffle = QPushButton("Shuffle")
        self._btn_shuffle.setFixedSize(80, 36)
        self._btn_shuffle.setCheckable(True)

        # Volume
        vol_label = QLabel("Vol")
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(100)
        self._vol_slider.setFixedWidth(100)
        self._vol_slider.setToolTip("Volume")

        controls_layout.addWidget(self._btn_prev)
        controls_layout.addWidget(self._btn_play_pause)
        controls_layout.addWidget(self._btn_next)
        controls_layout.addSpacing(12)
        controls_layout.addWidget(self._btn_repeat)
        controls_layout.addWidget(self._btn_shuffle)
        controls_layout.addSpacing(20)
        controls_layout.addWidget(vol_label)
        controls_layout.addWidget(self._vol_slider)
        layout.addLayout(controls_layout)

        # -- File buttons + overlay toggle --
        file_layout = QHBoxLayout()
        file_layout.setSpacing(8)

        self._btn_open_file = QPushButton("Open File")
        self._btn_open_file.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))

        self._btn_open_folder = QPushButton("Open Folder")
        self._btn_open_folder.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))

        file_layout.addWidget(self._btn_open_file)
        file_layout.addWidget(self._btn_open_folder)
        file_layout.addStretch()

        # Overlay toggle switch
        overlay_label = QLabel("Overlay")
        self._overlay_toggle = ToggleSwitch()
        self._overlay_toggle.setToolTip("Toggle lyric overlay")
        file_layout.addWidget(overlay_label)
        file_layout.addWidget(self._overlay_toggle)
        layout.addLayout(file_layout)

        # -- Lyric status --
        self._lyric_status = QLabel("")
        self._lyric_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lyric_status.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._lyric_status)

        # -- Playlist --
        self._playlist_widget = QListWidget()
        self._playlist_widget.setAlternatingRowColors(True)
        layout.addWidget(self._playlist_widget, stretch=1)

    def _connect_signals(self) -> None:
        # Buttons
        self._btn_play_pause.clicked.connect(self._toggle_play_pause)
        self._btn_prev.clicked.connect(self._prev_track)
        self._btn_next.clicked.connect(self._next_track)
        self._btn_repeat.clicked.connect(self._cycle_repeat_mode)
        self._btn_shuffle.clicked.connect(self._toggle_shuffle)
        self._btn_open_file.clicked.connect(self._open_file)
        self._btn_open_folder.clicked.connect(self._open_folder)
        self._overlay_toggle.toggled.connect(lambda _: self.overlay_toggle_requested.emit())

        # Seek slider
        self._seek_slider.sliderPressed.connect(self._on_seek_start)
        self._seek_slider.sliderReleased.connect(self._on_seek_end)

        # Volume
        self._vol_slider.valueChanged.connect(
            lambda v: self._engine.set_volume(v / 100.0)
        )

        # Playlist double-click
        self._playlist_widget.itemDoubleClicked.connect(self._on_playlist_item_activated)

        # Clock / Engine
        self._clock.position_updated.connect(self._on_position_updated)
        self._clock.track_finished.connect(self._on_track_finished)
        self._engine.duration_available.connect(self._on_duration_available)
        self._engine.state_changed.connect(self._on_state_changed)
        self._engine.error_occurred.connect(self._on_error)

        # Update visualizer accent color when theme changes
        self._config.config_changed.connect(self._on_config_changed)

    # -- Playback control slots --

    def _toggle_play_pause(self) -> None:
        if self._engine.state == "playing":
            self._engine.pause()
        else:
            if self._engine.current_file is None and self._playlist:
                self._load_track(0)
            self._engine.play()

    def _prev_track(self) -> None:
        if self._current_index > 0:
            self._load_track(self._current_index - 1)
            self._engine.play()

    def _next_track(self) -> None:
        if self._current_index < len(self._playlist) - 1:
            self._load_track(self._current_index + 1)
            self._engine.play()

    def _on_track_finished(self) -> None:
        """Auto-advance to next track based on repeat/shuffle mode."""
        self._engine.stop()
        
        if self._repeat_mode == RepeatMode.ONE:
            # Repeat current track
            self._engine.seek(0)
            self._engine.play()
            return
        
        # Determine next track
        next_idx = self._get_next_track_index()
        if next_idx is not None:
            self._load_track(next_idx)
            self._engine.play()

    # -- Seek slots --

    def _on_seek_start(self) -> None:
        self._is_seeking = True

    def _on_seek_end(self) -> None:
        self._is_seeking = False
        self._engine.seek(self._seek_slider.value())

    # -- Position / duration --

    def _on_position_updated(self, ms: int) -> None:
        if not self._is_seeking:
            self._seek_slider.setValue(ms)
            self._time_current.setText(ms_to_display(ms))

    def _on_duration_available(self, ms: int) -> None:
        self._seek_slider.setRange(0, ms)
        self._time_total.setText(ms_to_display(ms))

    def _on_state_changed(self, state: str) -> None:
        style = self.style()
        if state == "playing":
            self._btn_play_pause.setIcon(
                style.standardIcon(QStyle.StandardPixmap.SP_MediaPause)
            )
            self._visualizer.set_playing(True)
        else:
            self._btn_play_pause.setIcon(
                style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
            )
            self._visualizer.set_playing(False)

    def _on_error(self, msg: str) -> None:
        self._now_playing_label.setText(f"Error: {msg}")

    def _on_config_changed(self, key: str, value) -> None:
        if key == "played_color":
            self._visualizer.set_accent_color(str(value))

    # -- File loading --

    def _open_file(self) -> None:
        last_dir = self._config.get("last_directory", "")
        exts = " ".join(f"*{e}" for e in SUPPORTED_EXTENSIONS)
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Audio File", last_dir, f"Audio Files ({exts})"
        )
        if file_path:
            self._config.set("last_directory", str(Path(file_path).parent))
            self._config.save()
            self._playlist = [file_path]
            self._shuffle_history = []
            self._refresh_playlist_widget()
            self._load_track(0)
            self._engine.play()

    def _open_folder(self) -> None:
        last_dir = self._config.get("last_directory", "")
        folder = QFileDialog.getExistingDirectory(self, "Open Folder", last_dir)
        if folder:
            self._config.set("last_directory", folder)
            self._config.save()
            files = sorted(
                str(p)
                for p in Path(folder).iterdir()
                if p.suffix.lower() in SUPPORTED_EXTENSIONS
            )
            if files:
                self._playlist = files
                self._shuffle_history = []
                self._refresh_playlist_widget()
                self._load_track(0)
                self._engine.play()

    def _load_track(self, index: int) -> None:
        if 0 <= index < len(self._playlist):
            self._current_index = index
            file_path = self._playlist[index]
            if self._engine.load(file_path):
                name = Path(file_path).stem
                self._now_playing_label.setText(f"Now Playing: {name}")
                self._highlight_playlist_item(index)
                self._try_load_sidecar_wlrc(file_path)

    def _try_load_sidecar_wlrc(self, audio_path: str) -> None:
        """Look for embedded WLRC data or a .wlrc file alongside the audio and load it."""
        # First, try to extract embedded WLRC from MP3
        if audio_path.lower().endswith('.mp3'):
            try:
                wlrc = extract_wlrc_from_mp3(audio_path)
                if wlrc is not None:
                    self.wlrc_loaded.emit(wlrc)
                    return
            except Exception:
                pass
        
        # Fall back to sidecar .wlrc file
        wlrc_path = Path(audio_path).with_suffix(".wlrc")
        if wlrc_path.exists():
            try:
                wlrc = load_wlrc(str(wlrc_path))
                self.wlrc_loaded.emit(wlrc)
            except Exception:
                self.wlrc_loaded.emit(None)
        else:
            self.wlrc_loaded.emit(None)

    def _refresh_playlist_widget(self) -> None:
        self._playlist_widget.clear()
        for fp in self._playlist:
            name = Path(fp).name
            self._playlist_widget.addItem(name)

    def _highlight_playlist_item(self, index: int) -> None:
        for i in range(self._playlist_widget.count()):
            item = self._playlist_widget.item(i)
            if item:
                font = item.font()
                font.setBold(i == index)
                item.setFont(font)
