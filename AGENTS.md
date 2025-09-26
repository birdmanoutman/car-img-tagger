# Repository Guidelines

## Project Structure & Module Organization
- `web_app.py` hosts the FastAPI app, routing, and template wiring.
- Core services live in `database.py`, `ai_models.py`, and `color_detection_utils.py`; prefer extending them before new modules.
- Training and inference scripts stay at the repository root, with checkpoints in `models/` and analysis in `reports/`.
- UI assets live in `templates/` and `static/`; generated datasets and exports belong in `processed_data/`, `output/`, and `databases/`.
- Large reference images under `各标签素材/` stay untracked unless review demands them.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` — create and enter an isolated environment.
- `pip install -r requirements.txt` — provision FastAPI, PyTorch, and supporting libraries.
- `uvicorn web_app:app --reload --port 8000` — run the web UI locally with auto-reload.
- `python advanced_train_model.py` — retrain the angle classifier; confirm device settings before launch.
- `python enhanced_brand_image_tagger.py` — execute the extended brand-tag pipeline on prepared imagery.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation and meaningful docstrings on handlers or public helpers.
- Use `snake_case` for functions and variables, `PascalCase` for classes, and action-focused route names.
- Use type hints, pathlib objects, and context managers; keep imports tidy.
- Format with `black` or `ruff format` and lint via `ruff check` when available.

## Testing Guidelines
- No automated suite exists yet; add `pytest` coverage under a new `tests/` directory for non-trivial logic.
- Name files `test_<module>.py`, mock heavyweight data, and document any fixture assets drawn from `processed_data/`.
- Capture training metrics or QA notes in `reports/` and cite them in the change description.

## Commit & Pull Request Guidelines
- Git history is unavailable here; adopt conventional commits (e.g., `feat: add angle confidence filter`) for clarity.
- Keep each commit focused and explain schema, data, or model impacts in the body.
- Pull requests should outline scope, list evidence, and call out new assets or configuration steps.
- Attach screenshots or JSON snippets whenever FastAPI endpoints or UI templates change, and link tracking issues when possible.

## Data & Configuration Notes
- Review `config.py` before adjusting paths, thresholds, or model names; keep defaults in sync with scripts and templates.
- Store secrets in environment variables and document requirements in the PR summary, not the repo.
- Host large binaries externally and reference their location in `reports/` or the discussion thread rather than committing them.
