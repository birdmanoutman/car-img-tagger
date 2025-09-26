#!/usr/bin/env python3
"""Build an active-learning review queue from model predictions."""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pandas as pd

from car_img_tagger.active_learning import select_for_review
from car_img_tagger.config import DATA_CONFIG, MODEL_CONFIG


def _coerce_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    if isinstance(value, str) and not value.strip():
        return {}
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return {}
        return parsed if isinstance(parsed, dict) else {}


def _coerce_sequence(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    if isinstance(value, str) and not value.strip():
        return []
    try:
        data = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        try:
            data = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return []
    return data if isinstance(data, list) else []


def build_samples(df: pd.DataFrame) -> List[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        uncertainty_all = _coerce_mapping(row.get("uncertainty"))
        angle_unc = uncertainty_all.get("angles", {}) if isinstance(uncertainty_all, dict) else {}
        sample_uncertainty = {
            "entropy": float(angle_unc.get("entropy", 0.0) or 0.0),
            "margin": float(angle_unc.get("margin", 1.0) or 1.0),
            "max_confidence": float(angle_unc.get("max_confidence", 0.0) or 0.0),
        }

        clip_results = _coerce_mapping(row.get("clip_results"))
        samples.append(
            {
                "image_id": row.get("image_id"),
                "image_path": row.get("image_path"),
                "brand": row.get("brand"),
                "angle": row.get("angle"),
                "style": row.get("style"),
                "interior_part": row.get("interior_part"),
                "confidence": float(row.get("confidence", 0.0) or 0.0),
                "auto_tags": _coerce_sequence(row.get("auto_tags")),
                "clip_results": clip_results,
                "uncertainty": sample_uncertainty,
                "uncertainty_all": uncertainty_all,
            }
        )
    return samples


def summarise_sample(sample: Dict[str, Any]) -> Dict[str, Any]:
    clip_results = sample.get("clip_results", {})

    def _top_label(category: str) -> Dict[str, Any]:
        payload = clip_results.get(category, {})
        if not isinstance(payload, dict) or not payload:
            return {}
        label, score = max(payload.items(), key=lambda item: item[1])
        return {"label": label, "score": score}

    return {
        "image_id": sample.get("image_id"),
        "image_path": sample.get("image_path"),
        "confidence": sample.get("confidence"),
        "angle": sample.get("angle"),
        "brand": sample.get("brand"),
        "style": sample.get("style"),
        "interior_part": sample.get("interior_part"),
        "auto_tags": sample.get("auto_tags", []),
        "uncertainty": sample.get("uncertainty", {}),
        "best_angle": _top_label("angles"),
        "best_brand": _top_label("brands"),
        "best_style": _top_label("styles"),
        "best_interior": _top_label("interior_parts"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a low-confidence review queue")
    parser.add_argument("predictions", type=Path, help="Path to the auto_annotated_dataset.csv file")
    default_output = DATA_CONFIG["processed_data"] / "review_queue.json"
    parser.add_argument("--output", type=Path, default=default_output, help="Where to write the review queue JSON")
    parser.add_argument("--max-items", type=int, default=200, help="Maximum number of samples to emit")
    parser.add_argument("--entropy-threshold", type=float, default=None, help="Override entropy threshold; defaults to config setting")
    args = parser.parse_args()

    df = pd.read_csv(args.predictions)
    samples = build_samples(df)

    cfg = MODEL_CONFIG.get("active_learning", {})
    entropy_threshold = args.entropy_threshold
    if entropy_threshold is None:
        entropy_threshold = float(cfg.get("entropy_threshold", 1.1))

    review_candidates = select_for_review(samples, entropy_threshold=entropy_threshold, max_items=args.max_items)
    summary_payload = [summarise_sample(sample) for sample in review_candidates]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fp:
        json.dump(
            {
                "metadata": {
                    "source": str(args.predictions),
                    "count": len(summary_payload),
                    "entropy_threshold": entropy_threshold,
                },
                "samples": summary_payload,
            },
            fp,
            ensure_ascii=False,
            indent=2,
        )

    print(f"📄 Review queue saved to {args.output} (samples: {len(summary_payload)})")


if __name__ == "__main__":
    main()
