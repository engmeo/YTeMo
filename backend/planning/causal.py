"""Generic causal DAG primitives for domain-neutral planning."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from typing import Mapping


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


@dataclass(frozen=True)
class CausalEdge:
    cause: str
    effect: str
    coefficient: float
    evidence_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.cause, str) or not self.cause.strip():
            raise ValueError("cause must be a non-empty string")
        if not isinstance(self.effect, str) or not self.effect.strip():
            raise ValueError("effect must be a non-empty string")
        if self.cause == self.effect:
            raise ValueError("self-causation is not allowed")
        coefficient = _finite_number(self.coefficient, "coefficient")
        object.__setattr__(self, "coefficient", coefficient)
        if self.evidence_id is not None and (
            not isinstance(self.evidence_id, str) or not self.evidence_id.strip()
        ):
            raise ValueError("evidence_id must be a non-empty string when supplied")


@dataclass(frozen=True)
class CausalModel:
    nodes: tuple[str, ...]
    edges: tuple[CausalEdge, ...]
    baseline_values: Mapping[str, float]

    def __post_init__(self) -> None:
        nodes = tuple(self.nodes)
        edges = tuple(self.edges)
        if not nodes or any(not isinstance(n, str) or not n.strip() for n in nodes):
            raise ValueError("nodes must contain non-empty strings")
        if len(set(nodes)) != len(nodes):
            raise ValueError("nodes must be unique")
        if any(not isinstance(edge, CausalEdge) for edge in edges):
            raise ValueError("edges must contain CausalEdge values")
        if any(edge.cause not in nodes or edge.effect not in nodes for edge in edges):
            raise ValueError("every edge endpoint must exist in nodes")
        values = dict(self.baseline_values)
        if set(values) != set(nodes):
            raise ValueError("baseline_values must define every node exactly")
        normalized = {key: _finite_number(value, f"baseline_values[{key}]")
                      for key, value in values.items()}
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "baseline_values", normalized)
        self.topological_order()

    def topological_order(self) -> tuple[str, ...]:
        outgoing = {node: [] for node in self.nodes}
        indegree = {node: 0 for node in self.nodes}
        for edge in self.edges:
            outgoing[edge.cause].append(edge.effect)
            indegree[edge.effect] += 1
        queue = deque(node for node in self.nodes if indegree[node] == 0)
        ordered = []
        while queue:
            node = queue.popleft()
            ordered.append(node)
            for target in outgoing[node]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)
        if len(ordered) != len(self.nodes):
            raise ValueError("causal graph must be acyclic")
        return tuple(ordered)
