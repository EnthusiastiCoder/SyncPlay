# SyncPlay - Music Player with Synchronized Lyrics

A modern Windows desktop music player with synchronized word-level lyric overlay, theme customization, and offline forced-alignment tools.

<!-- Screenshot: the player tab with the lyric overlay highlighting the current word. -->
_Screenshot coming soon._

No audio or lyrics are bundled with this repository: bring your own files.

## Features

### 🎵 Music Player
- **Multi-format Support** — MP3, WAV, OGG, FLAC playback with QMediaPlayer
- **Playlist Management** — Repeat modes (Off/All/One), shuffle, folder loading
- **System Tray Integration** — Minimize to tray, playback controls in tray menu
- **Modern Dark UI** — Beautiful dark theme with smooth animations

### 🎤 Lyric Overlay
- **Transparent Overlay** — Always-on-top, auto-sizing overlay with word-level highlighting
- **Click-and-Hold Drag** — Hold for 300ms to drag, resize grip in bottom-right corner
- **Auto-Width** — Dynamically adjusts width to fit longest lyric line
- **Smooth Animations** — Fade in/out on pause/resume, auto-hide after 5s on pause
- **Embedded WLRC** — Lyrics stored directly in MP3 ID3 tags (TXXX:WLRC)

### 🎨 Theme System
- **6 Built-in Presets** — Spotify Green, Neon Blue, Warm Sunset, Monochrome, Cyberpunk, Classic Green
- **Custom Themes** — Create and save custom themes with color and opacity controls
- **Live Preview** — See theme changes in real-time on the overlay

### 🔧 Alignment Tool
- **Offline Forced Alignment** — Uses stable-ts (Whisper) to align transcripts to audio
- **GPU Acceleration** — CUDA support for faster alignment
- **Auto-Embed** — Automatically embeds WLRC data into MP3 files after alignment
- **Multiple Languages** — Support for 99+ languages via Whisper

### 📄 Subtitle Viewer
- **WLRC Inspector** — View and manage .wlrc files with detailed timing information
- **Word-Level Details** — Inspect individual word timings for each line
- **Extract from MP3** — Extract embedded WLRC data from MP3 files
- **Load in Player** — Quickly load subtitles into the player

## Known limitations

- The audio visualizer on the player tab animates decorative bars; it is not driven by the audio
  spectrum yet.

## Requirements

- Python 3.11+ (tested with 3.12)
- Windows 10/11

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python -m music_player.main
```

## Test

```bash
pytest music_player/tests/ -v
```

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Space` | Play / Pause |
| `Ctrl+O` | Open audio file |
| `Ctrl+L` | Toggle lyric overlay |
| `Ctrl+,` | Open settings |
| `Ctrl+Right` | Next track |
| `Ctrl+Left` | Previous track |

## Overlay Usage

- The overlay is **click-through** by default — mouse events pass to windows beneath it.
- **Click and hold** (300ms) anywhere on the overlay to enter drag mode and reposition it.
- **Resize grip** in the bottom-right corner allows height adjustment.
- Width automatically adjusts to fit the longest lyric line.
- Overlay fades out after 5 seconds when playback is paused.

## WLRC Format

`.wlrc` is a custom JSON format for word-level lyric timestamps:

```json
{
  "version": 1,
  "metadata": { "title": "Song", "artist": "Artist", "duration_ms": 180000 },
  "lines": [
    {
      "start_ms": 1000, "end_ms": 3000,
      "words": [
        { "text": "Hello", "start_ms": 1000, "end_ms": 1500 },
        { "text": "world", "start_ms": 1600, "end_ms": 2800 }
      ]
    }
  ]
}
```

## Packaging (PyInstaller)

```bash
pip install pyinstaller
python build_config.py
```

Output will be in `dist/MusicPlayerOverlay/`.

## Project Structure

```
music_player/
├── main.py              # Entry point, MainWindow, system tray, shortcuts
├── config.py            # JSON config manager with PyQt signals
├── models/
│   ├── wlrc.py          # WLRC dataclasses, parser, writer, binary search
│   └── wlrc_embed.py    # MP3 ID3 tag embedding/extraction (mutagen)
├── audio/
│   ├── engine.py        # QMediaPlayer audio engine
│   └── clock.py         # 30 Hz playback clock
├── player/
│   ├── player_tab.py    # Player UI, playlist, repeat/shuffle
│   └── settings_dialog.py # Settings with color pickers, font, position
├── overlay/
│   ├── overlay_window.py  # Transparent overlay with drag/resize (Win32)
│   └── lyric_renderer.py  # QPainter word-level lyric rendering
├── alignment/
│   ├── aligner.py       # stable-ts forced alignment worker (GPU)
│   ├── alignment_tab.py # Alignment tool UI with auto-embed
│   └── model_manager.py # Whisper model cache management
├── themes/
│   ├── theme_manager.py # Theme presets and custom theme storage
│   └── theme_tab.py     # Theme selection and customization UI
├── subtitle/
│   └── subtitle_viewer_tab.py # WLRC file viewer and inspector
├── utils/
│   └── time_utils.py    # ms ↔ timestamp conversions
├── resources/
│   ├── default_config.json
│   ├── dark_theme.qss   # Dark theme stylesheet
│   ├── icon.ico         # SyncPlay application icon
│   └── create_icon.py   # Icon generator script
└── tests/               # 118 unit tests (100% passing)
```

## Copyright

© Arpan Mandal. All Rights Reserved.

See [`COPYRIGHT`](./COPYRIGHT) for the terms.
