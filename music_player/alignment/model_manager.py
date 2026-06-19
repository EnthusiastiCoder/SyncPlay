"""Whisper model download/cache management for stable-ts alignment."""

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal


# Standard Whisper model sizes and approximate download sizes (MB)
MODEL_INFO = {
    "tiny": {"size_mb": 75, "params": "39M"},
    "base": {"size_mb": 142, "params": "74M"},
    "small": {"size_mb": 466, "params": "244M"},
    "medium": {"size_mb": 1500, "params": "769M"},
}

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "whisper"


class ModelDownloadWorker(QThread):
    """Background thread for downloading a Whisper model."""

    progress = pyqtSignal(str)  # status message
    finished_ok = pyqtSignal(str)  # model name
    failed = pyqtSignal(str)  # error message

    def __init__(self, model_name: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._model_name = model_name
        self._cancelled = False

    def run(self) -> None:
        try:
            self.progress.emit(f"Loading model '{self._model_name}'...")
            import stable_whisper
            stable_whisper.load_model(self._model_name)
            if not self._cancelled:
                self.finished_ok.emit(self._model_name)
        except Exception as e:
            if not self._cancelled:
                self.failed.emit(str(e))

    def cancel(self) -> None:
        self._cancelled = True


class ModelManager:
    """Manages Whisper model availability and caching."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    @staticmethod
    def available_models() -> list[str]:
        """Return list of supported model names."""
        return list(MODEL_INFO.keys())

    @staticmethod
    def model_info(name: str) -> dict:
        """Return size/params info for a model."""
        return MODEL_INFO.get(name, {})

    def is_model_cached(self, name: str) -> bool:
        """Check if a model is already downloaded."""
        # Whisper caches models as .pt files in the cache dir
        model_file = self._cache_dir / f"{name}.pt"
        return model_file.exists()

    def cached_models(self) -> list[str]:
        """Return list of cached model names."""
        return [
            name for name in MODEL_INFO
            if self.is_model_cached(name)
        ]

    def delete_model(self, name: str) -> bool:
        """Delete a cached model. Returns True if deleted."""
        model_file = self._cache_dir / f"{name}.pt"
        if model_file.exists():
            model_file.unlink()
            return True
        return False

    def cache_size_mb(self) -> float:
        """Total size of cached models in MB."""
        total = 0
        if self._cache_dir.exists():
            for f in self._cache_dir.iterdir():
                if f.suffix == ".pt":
                    total += f.stat().st_size
        return total / (1024 * 1024)
