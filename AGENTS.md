# Repository Guidelines

## Project Structure & Module Organization
- `web_app.py` hosts the FastAPI app, routing, and template wiring.
- Core services live in `database.py`, `ai_models.py`, and `color_detection_utils.py`; extend them before adding new modules.
- Training scripts stay at the root; helpers like `models/vision_language.py`, `active_learning.py`, and `deployment_utils.py` back advanced workflows.
- Templates and static assets remain in `templates/` + `static/`; derived data goes to `processed_data/`, `output/`, `databases/`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` — create and enter an isolated environment.
- `pip install -r requirements.txt` — provision FastAPI, PyTorch, and supporting libraries.
- `uvicorn web_app:app --reload --port 8000` — run the web UI locally with auto-reload.
- `python advanced_train_model.py` — retrain the angle classifier (set device flags first).
- `python enhanced_brand_image_tagger.py` — run the extended brand-tag pipeline.
- `python ai_models.py --max-per-brand 50` — batch auto-tag a validation slice.
- `python ai_models.py --export-encoder` — emit the SigLIP ONNX/TensorRT bundle.

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
- Call `review_queue.py`（或直接使用 `active_learning.select_for_review`）生成 `processed_data/review_queue.json`，在 Label Studio 中批量导入。
- Use stored `clip_results` for the full probability vector when auditing gear-shifter edge cases.
