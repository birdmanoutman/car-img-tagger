"""Utilities for ranking predictions that need manual review."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

import numpy as np


@dataclass
class UncertaintyScores:
    entropy: float
    margin: float
    max_confidence: float


def probability_entropy(probabilities: Sequence[float]) -> float:
    clipped = np.clip(np.asarray(probabilities, dtype=np.float64), 1e-8, 1.0)
    return float(-np.sum(clipped * np.log(clipped)))


def margin_confidence(probabilities: Sequence[float]) -> float:
    sorted_probs = np.sort(np.asarray(probabilities, dtype=np.float64))[::-1]
    if sorted_probs.size < 2:
        return float(sorted_probs.max(initial=0.0))
    return float(sorted_probs[0] - sorted_probs[1])


def compute_uncertainty(probabilities: Sequence[float]) -> UncertaintyScores:
    probs = np.asarray(probabilities, dtype=np.float64)
    return UncertaintyScores(
        entropy=probability_entropy(probs),
        margin=margin_confidence(probs),
        max_confidence=float(probs.max(initial=0.0)),
    )


def select_for_review(predictions: Iterable[dict], entropy_threshold: float, max_items: int = 100) -> List[dict]:
    queue: List[tuple[float, dict]] = []
    for sample in predictions:
        uncertainty = sample.get("uncertainty", {})
        entropy = uncertainty.get("entropy", 0.0)
        if entropy >= entropy_threshold:
            queue.append((entropy, sample))
    queue.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in queue[:max_items]]
