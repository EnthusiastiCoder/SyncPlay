"""Tests for Aligner and ModelManager (with mocked stable-ts)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

from music_player.alignment.model_manager import ModelManager, MODEL_INFO
from music_player.alignment.aligner import AlignmentWorker
from music_player.models.wlrc import load_wlrc, WlrcData

app = QApplication.instance() or QApplication([])


# -- ModelManager tests --

class TestModelManager:

    def test_available_models(self):
        models = ModelManager.available_models()
        assert "tiny" in models
        assert "base" in models
        assert "small" in models
        assert "medium" in models
