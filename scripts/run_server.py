#!/usr/bin/env python3
"""Launch the FastAPI web application."""
from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def main() -> None:
    uvicorn.run("car_img_tagger.web.app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
