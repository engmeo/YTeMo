"""Versioned, append-oriented plan graph primitives."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping


@dataclass(frozen=True)
class PlanGraphNode:
    node_id: str
    plan_id: str
    version: int
    status: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        for name in ("node_id", "plan_id", "status"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be a positive integer")
        if not isinstance(self.payload, Mapping):
            raise ValueError("payload must be a mapping")
        object.__setattr__(self, "payload", dict(self.payload))


@dataclass(frozen=True)
class PlanGraphEdge:
    source_id: str
    target_id: str
    relation: str = "depends_on"

    def __post_init__(self) -> None:
        if not self.source_id or not self.target_id:
            raise ValueError("edge endpoints must be non-empty")
        if self.source_id == self.target_id:
            raise ValueError("self edges are not allowed")
        if self.relation not in {"depends_on", "supersedes", "derived_from"}:
            raise ValueError("unsupported edge relation")


@dataclass(frozen=True)
class PlanGraph:
    nodes: tuple[PlanGraphNode, ...] = ()
    edges: tuple[PlanGraphEdge, ...] = ()

    def __post_init__(self) -> None:
        nodes, edges = tuple(self.nodes), tuple(self.edges)
        if any(not isinstance(n, PlanGraphNode) for n in nodes):
            raise ValueError("nodes must contain PlanGraphNode values")
        if any(not isinstance(e, PlanGraphEdge) for e in edges):
            raise ValueError("edges must contain PlanGraphEdge values")
        ids = [n.node_id for n in nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("node_id values must be unique")
        known = set(ids)
        if any(e.source_id not in known or e.target_id not in known for e in edges):
            raise ValueError("every edge endpoint must exist")
        if len({(e.source_id, e.target_id, e.relation) for e in edges}) != len(edges):
            raise ValueError("duplicate edges are not allowed")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        self.validate_dependency_dag()

    def validate_dependency_dag(self) -> None:
        outgoing = {n.node_id: [] for n in self.nodes}
        indegree = {n.node_id: 0 for n in self.nodes}
        for edge in self.edges:
            if edge.relation != "depends_on":
                continue
            outgoing[edge.source_id].append(edge.target_id)
            indegree[edge.target_id] += 1
        ready = [node_id for node_id, degree in indegree.items() if degree == 0]
        visited = 0
        while ready:
            current = ready.pop()
            visited += 1
            for target in outgoing[current]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    ready.append(target)
        if visited != len(self.nodes):
            raise ValueError("depends_on edges must form a DAG")

    def latest_version(self, plan_id: str) -> int:
        versions = [n.version for n in self.nodes if n.plan_id == plan_id]
        return max(versions, default=0)


def append_plan_version(
    graph: PlanGraph,
    *,
    node_id: str,
    plan_id: str,
    payload: Mapping[str, object],
    status: str = "proposed",
    parent_node_id: str | None = None,
) -> PlanGraph:
    if not isinstance(graph, PlanGraph):
        raise ValueError("graph must be a PlanGraph")
    version = graph.latest_version(plan_id) + 1
    node = PlanGraphNode(node_id, plan_id, version, status, payload)
    edges = list(graph.edges)
    if parent_node_id is not None:
        parent = next((n for n in graph.nodes if n.node_id == parent_node_id), None)
        if parent is None:
            raise ValueError("parent_node_id does not exist")
        if parent.plan_id != plan_id:
            raise ValueError("parent node must belong to the same plan")
        edges.append(PlanGraphEdge(node_id, parent_node_id, "supersedes"))
    return PlanGraph(graph.nodes + (node,), tuple(edges))
