"""Statistical synthesis for compatible, explicitly supplied study effects.

This module does not extract effect sizes from prose and does not decide whether
studies are clinically comparable. Those are upstream evidence-appraisal tasks.
"""
from __future__ import annotations

import math
from typing import Any


def pool_effects(studies: list[dict[str, Any]], method: str = "random") -> dict[str, Any]:
    if method not in {"fixed", "random"}:
        raise ValueError("method must be 'fixed' or 'random'")
    if len(studies) < 2:
        raise ValueError("At least two independent studies are required.")
    measures = {str(item.get("effect_measure") or "") for item in studies}
    scales = {str(item.get("effect_scale") or "linear") for item in studies}
    if len(measures) != 1 or "" in measures or len(scales) != 1:
        raise ValueError("All studies must use the same effect_measure and effect_scale.")
    if len({str(item.get("study_id")) for item in studies}) != len(studies):
        raise ValueError("Duplicate study_id values are not allowed.")
    effects, variances = [], []
    for item in studies:
        effect = float(item["effect"])
        se = float(item["standard_error"])
        if not math.isfinite(effect) or not math.isfinite(se) or se <= 0:
            raise ValueError("Effect and standard_error must be finite; standard_error must be positive.")
        effects.append(effect)
        variances.append(se * se)
    fixed_weights = [1.0 / value for value in variances]
    fixed_mean = sum(w * y for w, y in zip(fixed_weights, effects)) / sum(fixed_weights)
    q = sum(w * (y - fixed_mean) ** 2 for w, y in zip(fixed_weights, effects))
    df = len(studies) - 1
    c = sum(fixed_weights) - sum(w * w for w in fixed_weights) / sum(fixed_weights)
    tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0
    if method == "random":
        weights = [1.0 / (variance + tau2) for variance in variances]
    else:
        weights = fixed_weights
    estimate = sum(w * y for w, y in zip(weights, effects)) / sum(weights)
    standard_error = math.sqrt(1.0 / sum(weights))
    ci_low, ci_high = estimate - 1.96 * standard_error, estimate + 1.96 * standard_error
    i2 = max(0.0, (q - df) / q) * 100.0 if q > 0 else 0.0
    return {
        "method": method,
        "effect_measure": next(iter(measures)),
        "effect_scale": next(iter(scales)),
        "study_count": len(studies),
        "pooled_effect": estimate,
        "standard_error": standard_error,
        "confidence_interval_95": [ci_low, ci_high],
        "heterogeneity": {"q": q, "degrees_of_freedom": df, "i_squared_percent": i2, "tau_squared": tau2},
        "study_ids": [str(item["study_id"]) for item in studies],
        "notice": "Statistical pooling only. It does not establish clinical comparability, certainty, absence of bias, or a treatment recommendation.",
    }
