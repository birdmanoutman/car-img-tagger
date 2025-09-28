"""car_img_tagger package: auto-tagging pipeline and utilities."""
from __future__ import annotations

from typing import Any

from .config import API_CONFIG, DATA_CONFIG, LABEL_CONFIG, MODEL_CONFIG, PROJECT_ROOT

__all__ = [
    "PROJECT_ROOT",
    "DATA_CONFIG",
    "LABEL_CONFIG",
    "MODEL_CONFIG",
    "API_CONFIG",
    "CarImageTagger",
]


def __getattr__(name: str) -> Any:  # pragma: no cover - convenience import
    if name == "CarImageTagger":
        from .auto_tagging import CarImageTagger as _CarImageTagger

        return _CarImageTagger
    raise AttributeError(f"module 'car_img_tagger' has no attribute {name!r}")
