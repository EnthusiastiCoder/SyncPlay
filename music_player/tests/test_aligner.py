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

    def test_model_info(self):
        info = ModelManager.model_info("base")
        assert "size_mb" in info
        assert "params" in info

    def test_model_info_unknown(self):
        info = ModelManager.model_info("nonexistent")
        assert info == {}

    def test_is_model_cached_false(self, tmp_path):
        mm = ModelManager(cache_dir=tmp_path)
        assert not mm.is_model_cached("base")

    def test_is_model_cached_true(self, tmp_path):
        mm = ModelManager(cache_dir=tmp_path)
        (tmp_path / "base.pt").write_bytes(b"fake model data")
        assert mm.is_model_cached("base")

    def test_cached_models(self, tmp_path):
        mm = ModelManager(cache_dir=tmp_path)
        (tmp_path / "tiny.pt").write_bytes(b"fake")
        (tmp_path / "base.pt").write_bytes(b"fake")
        cached = mm.cached_models()
        assert "tiny" in cached
        assert "base" in cached
        assert "small" not in cached

    def test_delete_model(self, tmp_path):
        mm = ModelManager(cache_dir=tmp_path)
        (tmp_path / "base.pt").write_bytes(b"fake")
        assert mm.delete_model("base")
        assert not mm.is_model_cached("base")

    def test_delete_model_not_found(self, tmp_path):
        mm = ModelManager(cache_dir=tmp_path)
        assert not mm.delete_model("base")

    def test_cache_size(self, tmp_path):
        mm = ModelManager(cache_dir=tmp_path)
        (tmp_path / "base.pt").write_bytes(b"x" * 1048576)  # 1 MB
        size = mm.cache_size_mb()
        assert abs(size - 1.0) < 0.1
