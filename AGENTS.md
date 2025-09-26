# Repository Guidelines

## Project Structure & Module Organization
- `src/car_img_tagger/` holds the package code: `auto_tagging.py` for the SigLIP pipeline, `config.py` for shared paths, `database.py` for persistence, `color_detection.py` for HSV helpers, and `deployment.py` for ONNX/TensorRT export.
- `src/car_img_tagger/modeling/vision_language.py` wraps CLIP/SigLIP backbones; `src/car_img_tagger/web/app.py` exposes the FastAPI app.
- CLI entry points live in `scripts/` (`auto_tag.py`, `build_review_queue.py`, `run_server.py`, `train_angle_classifier.py`, `run_enhanced_brand_tagger.py`).
- Templates and static assets remain in `templates/` + `static/`; derived data stays in `processed_data/`, `output/`, `databases/`, while model weights continue under `models/`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` — create and enter an isolated environment.
- `pip install -r requirements.txt` — provision FastAPI, PyTorch, and supporting libraries.
- `python scripts/run_server.py` — launch the FastAPI web UI with reload.
- `python scripts/auto_tag.py --max-per-brand 50` — batch auto-tag a validation slice.
- `python scripts/auto_tag.py --export-encoder` — export the SigLIP ONNX/TensorRT bundle.
- `python scripts/build_review_queue.py processed_data/auto_annotated_dataset.csv` — emit a Label Studio-ready review queue.
- `python scripts/train_angle_classifier.py` — kick off the EfficientNet angle classifier training loop.
- `python scripts/run_enhanced_brand_tagger.py` — execute the legacy ensemble brand tagger when needed.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation, meaningful docstrings, and type hints on public helpers.
- Keep `snake_case` for functions/vars, `PascalCase` for classes, and action-oriented routes.
- Format with `black` or `ruff format`, then lint via `ruff check`; prune unused imports.

## Testing Guidelines
- Add `pytest` coverage in `tests/` for new logic; name files `test_<module>.py` and mock heavy data.
- Drop evaluation artifacts or QA notes in `reports/` and cite them in change descriptions.

## Commit & Pull Request Guidelines
- Use conventional commits (e.g., `feat: add angle confidence filter`) while history stays local-only.
- Keep commits scoped and explain schema/data/model impacts in the body.
- Pull requests need scope, evidence (tests, metrics, screenshots), and any asset or config callouts.

## Data & Configuration Notes
- Review `config.py` when changing paths, thresholds, or model IDs; keep scripts aligned.
- Keep secrets in env vars and note requirements in PRs; host large binaries externally and reference their location.

## Active Learning & Review Loop
- Tune `MODEL_CONFIG["active_learning"]` thresholds to balance reviewer load vs. precision.
- Run `python scripts/build_review_queue.py processed_data/auto_annotated_dataset.csv`（或直接使用 `active_learning.select_for_review`）生成 `processed_data/review_queue.json`，在 Label Studio 中批量导入。
- Use stored `clip_results` for the full probability vector when auditing gear-shifter edge cases.
