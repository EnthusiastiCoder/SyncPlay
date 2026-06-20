"""Forced alignment engine using stable-ts / Whisper."""

import io
import os
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from music_player.models.wlrc import WlrcData, WlrcLine, WlrcWord, WlrcMetadata, save_wlrc


class AlignmentWorker(QThread):
    """Background thread that runs stable-ts forced alignment."""

    progress = pyqtSignal(str)       # status message
    finished_ok = pyqtSignal(str)    # output .wlrc path
    failed = pyqtSignal(str)         # error message

    def __init__(
        self,
        audio_path: str,
        transcript: str,
        model_name: str = "base",
        language: str = "en",
        output_path: Optional[str] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._audio_path = audio_path
        self._transcript = transcript
        self._model_name = model_name
        self._language = language
        self._output_path = output_path or self._default_output_path()
        self._cancelled = False

    def _default_output_path(self) -> str:
        """Generate output path by replacing audio extension with .wlrc."""
        return str(Path(self._audio_path).with_suffix(".wlrc"))

    def run(self) -> None:
        # When running as a GUI app (.pyw / pythonw), sys.stdout and
        # sys.stderr are None.  stable-whisper writes progress to stdout
        # internally, which crashes with "NoneType has no attribute 'write'".
        # Redirect them to devnull so the library works silently.
        _orig_stdout = sys.stdout
        _orig_stderr = sys.stderr
        try:
            if sys.stdout is None:
                sys.stdout = open(os.devnull, "w")
            if sys.stderr is None:
                sys.stderr = open(os.devnull, "w")

            import torch
            import stable_whisper
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.progress.emit(f"Loading model on {device}...")
            model = stable_whisper.load_model(self._model_name, device=device)

            if self._cancelled:
                return

            self.progress.emit("Aligning transcript to audio...")
            result = model.align(
                self._audio_path,
                self._transcript,
                language=self._language,
            )

            if self._cancelled:
                return

            self.progress.emit("Converting to WLRC format...")
            wlrc = self._result_to_wlrc(result)
            save_wlrc(wlrc, self._output_path)

            if not self._cancelled:
                self.progress.emit("Done!")
                self.finished_ok.emit(self._output_path)

        except Exception as e:
            if not self._cancelled:
                self.failed.emit(str(e))
        finally:
            sys.stdout = _orig_stdout
            sys.stderr = _orig_stderr
