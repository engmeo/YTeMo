"""Deterministic intervention and counterfactual evaluation."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from .causal import CausalModel


@dataclass(frozen=True)
class CounterfactualResult:
    baseline: Mapping[str, float]
    counterfactual: Mapping[str, float]
    deltas: Mapping[str, float]
    intervention: Mapping[str, float]

    def __post_init__(self) -> None:
        for field_name in ("baseline", "counterfactual", "deltas", "intervention"):
            values = dict(getattr(self, field_name))
            if any(not math.isfinite(float(value)) for value in values.values()):
                raise ValueError(f"{field_name} must contain finite values")
            object.__setattr__(self, field_name, values)


def evaluate_intervention(
    model: CausalModel, intervention: Mapping[str, float]
) -> CounterfactualResult:
    """Apply node-value interventions and propagate additive causal effects.

    Structural assumption: each downstream node equals its baseline value plus
    the sum of incoming coefficient * (cause - baseline cause). This is a
    transparent linear structural model, not a learned or clinically validated
    causal model.
    """
    if not isinstance(model, CausalModel):
        raise ValueError("model must be a CausalModel")
    if not isinstance(intervention, Mapping) or not intervention:
        raise ValueError("intervention must be a non-empty mapping")
    changes = {}
    for node, value in intervention.items():
        if node not in model.nodes:
            raise ValueError(f"unknown intervention node: {node}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"intervention[{node}] must be numeric")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"intervention[{node}] must be finite")
        changes[node] = value

    result = dict(model.baseline_values)
    result.update(changes)
    incoming = {node: [] for node in model.nodes}
    for edge in model.edges:
        incoming[edge.effect].append(edge)

    for node in model.topological_order():
        if node in changes:
            continue
        value = float(model.baseline_values[node])
        for edge in incoming[node]:
            value += edge.coefficient * (
                result[edge.cause] - float(model.baseline_values[edge.cause])
            )
        if not math.isfinite(value):
            raise ValueError(f"non-finite counterfactual value at node: {node}")
        result[node] = value

    baseline = dict(model.baseline_values)
    deltas = {node: result[node] - baseline[node] for node in model.nodes}
    return CounterfactualResult(
        baseline=baseline,
        counterfactual=result,
        deltas=deltas,
        intervention=changes,
    )
