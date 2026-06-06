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
