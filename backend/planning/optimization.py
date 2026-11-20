"""Pareto filtering for planning candidates; no hidden execution or tuning."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class PlanningOption:
    option_id: str
    utility: float
    latency_ms: float
    compute_cost: float
    risk: float

    def __post_init__(self) -> None:
        if not self.option_id.strip():
            raise ValueError("option_id must not be empty")
        for name in ("utility", "latency_ms", "compute_cost", "risk"):
            value = getattr(self, name)
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.latency_ms < 0 or self.compute_cost < 0 or not 0 <= self.risk <= 1:
            raise ValueError("latency/cost must be non-negative and risk must be in [0, 1]")


def pareto_frontier(options: Iterable[PlanningOption]) -> tuple[PlanningOption, ...]:
    """Maximize utility; minimize latency, compute cost and risk."""
    items = tuple(options)
    if len({item.option_id for item in items}) != len(items):
        raise ValueError("option_id values must be unique")

    def dominates(a: PlanningOption, b: PlanningOption) -> bool:
        no_worse = (
            a.utility >= b.utility
            and a.latency_ms <= b.latency_ms
            and a.compute_cost <= b.compute_cost
            and a.risk <= b.risk
        )
        strictly_better = (
            a.utility > b.utility
            or a.latency_ms < b.latency_ms
            or a.compute_cost < b.compute_cost
            or a.risk < b.risk
        )
        return no_worse and strictly_better

    frontier = [candidate for candidate in items
                if not any(other is not candidate and dominates(other, candidate) for other in items)]
    return tuple(sorted(frontier, key=lambda item: item.option_id))
