"""Alignment Tool tab UI for forced-aligning transcripts to audio."""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTextEdit, QComboBox, QProgressBar, QMessageBox,
    QGroupBox, QGridLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
