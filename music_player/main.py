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
