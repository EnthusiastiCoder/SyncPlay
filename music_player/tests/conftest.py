"""Pytest conftest — preload torch before Qt Multimedia to avoid DLL conflicts on Windows."""

try:
    import torch  # noqa: F401
except ImportError:
    pass
