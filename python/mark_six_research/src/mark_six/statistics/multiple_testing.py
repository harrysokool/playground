"""Deterministic multiple-testing corrections."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def benjamini_hochberg(p_values: list[float], q: float = 0.05) -> tuple[list[float], list[bool]]:
    """Return BH-adjusted p-values and rejection flags in original order."""

    if not 0 < q < 1:
        raise ValueError("q must be between zero and one")
    if not p_values:
        return [], []
    values = _validated(p_values)
    order = np.argsort(values, kind="stable")
    ranked = values[order]
    count = len(ranked)
    adjusted_ranked = np.minimum.accumulate((ranked * count / np.arange(1, count + 1))[::-1])[::-1]
    adjusted_ranked = np.minimum(adjusted_ranked, 1.0)
    adjusted = np.empty(count, dtype=np.float64)
    adjusted[order] = adjusted_ranked
    return adjusted.tolist(), (adjusted <= q).tolist()


def holm(p_values: list[float], alpha: float = 0.05) -> tuple[list[float], list[bool]]:
    """Return Holm-adjusted p-values and family-wise rejection flags."""

    if not 0 < alpha < 1:
        raise ValueError("alpha must be between zero and one")
    if not p_values:
        return [], []
    values = _validated(p_values)
    order = np.argsort(values, kind="stable")
    ranked = values[order]
    count = len(ranked)
    adjusted_ranked = np.maximum.accumulate(ranked * np.arange(count, 0, -1))
    adjusted_ranked = np.minimum(adjusted_ranked, 1.0)
    adjusted = np.empty(count, dtype=np.float64)
    adjusted[order] = adjusted_ranked
    return adjusted.tolist(), (adjusted <= alpha).tolist()


def _validated(p_values: list[float]) -> NDArray[np.float64]:
    values = np.asarray(p_values, dtype=np.float64)
    if np.any(~np.isfinite(values)) or np.any(values < 0) or np.any(values > 1):
        raise ValueError("p-values must be finite values from zero through one")
    return values
