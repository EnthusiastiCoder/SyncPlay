"""PyInstaller build helper — run with: python build_config.py"""

import PyInstaller.__main__
import os

HERE = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    os.path.join(HERE, "music_player", "main.py"),
    "--name", "MusicPlayerOverlay",
    "--onedir",
    "--windowed",
    "--add-data", os.path.join(HERE, "music_player", "resources") + os.pathsep + "music_player/resources",
    "--hidden-import", "pygame",
    "--hidden-import", "stable_whisper",
    "--noconfirm",
])
