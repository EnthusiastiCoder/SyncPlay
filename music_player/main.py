"""Music Player with Lyric Overlay — Main Entry Point."""

import multiprocessing
import os
import sys
import logging
import subprocess
import traceback

# Prevent torch from spawning duplicate processes on Windows
multiprocessing.freeze_support()
