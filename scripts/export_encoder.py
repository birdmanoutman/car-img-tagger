#!/usr/bin/env python3
"""Export the SigLIP encoder to ONNX/TensorRT."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from car_img_tagger.auto_tagging import CarImageTagger


def main() -> None:
    tagger = CarImageTagger()
    tagger.export_image_encoder()


if __name__ == "__main__":
    main()
