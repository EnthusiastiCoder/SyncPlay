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
