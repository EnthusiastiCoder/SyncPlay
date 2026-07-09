"""Tests for Aligner and ModelManager (with mocked stable-ts)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication
