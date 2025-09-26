"""car_img_tagger package: auto-tagging pipeline and utilities."""
from .config import PROJECT_ROOT, DATA_CONFIG, LABEL_CONFIG, MODEL_CONFIG, API_CONFIG
from .auto_tagging import CarImageTagger

__all__ = [
    "PROJECT_ROOT",
    "DATA_CONFIG",
    "LABEL_CONFIG",
    "MODEL_CONFIG",
    "API_CONFIG",
    "CarImageTagger",
]
