"""Simple Temporal Network (STN) consistency and bound propagation."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class TemporalConstraint:
    source: str
    target: str
    max_difference: float

    def __post_init__(self):
        if not self.source or not self.target:
            raise ValueError("temporal event names must be non-empty")
        if isinstance(self.max_difference, bool) or not isinstance(self.max_difference, (int, float)) or not isfinite(self.max_difference):
            raise ValueError("max_difference must be finite")


@dataclass(frozen=True)
class TemporalResult:
    consistent: bool
    earliest_times: dict[str, float]


def solve_temporal_network(events: Iterable[str], constraints: Iterable[TemporalConstraint]) -> TemporalResult:
    """Check constraints of form time[target] - time[source] <= max_difference.

    A consistent solution is returned relative to an arbitrary zero-time origin.
    """
    nodes = tuple(dict.fromkeys(events))
    if any(not isinstance(n, str) or not n for n in nodes):
        raise ValueError("events must be non-empty strings")
    edges = tuple(constraints)
    known = set(nodes)
    for c in edges:
        if not isinstance(c, TemporalConstraint):
            raise ValueError("constraints must contain TemporalConstraint values")
        if c.source not in known or c.target not in known:
            raise ValueError("temporal constraint references an unknown event")
    # Add a super-source with zero-weight edges to every event.
    dist = {n: 0.0 for n in nodes}
    for i in range(len(nodes)):
        changed = False
        for c in edges:
            candidate = dist[c.source] + float(c.max_difference)
            if candidate < dist[c.target] - 1e-12:
                dist[c.target] = candidate
                changed = True
        if not changed:
            return TemporalResult(True, {n: dist[n] for n in nodes})
        if i == len(nodes) - 1:
            return TemporalResult(False, {})
    return TemporalResult(True, dist)
