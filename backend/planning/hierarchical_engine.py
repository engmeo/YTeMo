"""Advanced domain-neutral hierarchical planning engine.

This module extends the existing HTN primitives without modifying their
public contracts or introducing domain-specific dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .hierarchy import Task, DecompositionMethod


@dataclass(frozen=True)
class HierarchicalMethod:
    method: DecompositionMethod
    required_context: Mapping[str, object] | None = None

    def __post_init__(self):
        if not isinstance(self.method, DecompositionMethod):
            raise TypeError("method must be a DecompositionMethod")
        if self.required_context is not None and not isinstance(
            self.required_context, Mapping
        ):
            raise TypeError("required_context must be a mapping")

    def is_applicable(self, context: Mapping[str, object]) -> bool:
        if self.required_context is None:
            return True
        return all(
            context.get(key) == value
            for key, value in self.required_context.items()
        )


@dataclass(frozen=True)
class DecompositionRecord:
    parent_task_id: str
    method_id: str
    child_task_ids: tuple[str, ...]


@dataclass(frozen=True)
class HierarchicalPlanResult:
    primitive_tasks: tuple[Task, ...]
    ordered_task_ids: tuple[str, ...]
    applied_methods: tuple[str, ...]
    decomposition_trace: tuple[DecompositionRecord, ...]
    expanded_nodes: int
    dependencies: tuple[tuple[str, tuple[str, ...]], ...] = ()


def resolve_task_dependencies(
    tasks: Sequence[Task],
    dependencies: Mapping[str, Sequence[str]] | None = None,
) -> tuple[str, ...]:
    """Return deterministic topological order for primitive task IDs."""
    ids = [task.task_id for task in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate primitive task ids")

    known = set(ids)
    dependencies = dependencies or {}

    unknown_sources = set(dependencies) - known
    if unknown_sources:
        raise ValueError(
            f"dependencies reference unknown tasks: {sorted(unknown_sources)}"
        )

    incoming: dict[str, set[str]] = {task_id: set() for task_id in ids}
    outgoing: dict[str, set[str]] = {task_id: set() for task_id in ids}

    for task_id, predecessors in dependencies.items():
        for predecessor in predecessors:
            if predecessor not in known:
                raise ValueError(
                    f"task {task_id!r} depends on unknown task {predecessor!r}"
                )
            if predecessor == task_id:
                raise ValueError(f"task {task_id!r} depends on itself")
            incoming[task_id].add(predecessor)
            outgoing[predecessor].add(task_id)

    ready = [task_id for task_id in ids if not incoming[task_id]]
    result: list[str] = []

    while ready:
        current = ready.pop(0)
        result.append(current)

        for child in ids:
            if child in outgoing[current]:
                incoming[child].discard(current)
                if not incoming[child] and child not in result and child not in ready:
                    ready.append(child)

    if len(result) != len(ids):
        raise ValueError("task dependency cycle detected")

    return tuple(result)


class HierarchicalPlanner:
    """Context-aware HTN planner with traceability and dependency resolution."""

    def __init__(self, *, max_depth: int = 32, max_nodes: int = 10000):
        if max_depth < 1 or max_nodes < 1:
            raise ValueError("max_depth and max_nodes must be positive")
        self.max_depth = max_depth
        self.max_nodes = max_nodes

    def plan(
        self,
        tasks: Sequence[Task],
        methods: Sequence[DecompositionMethod | HierarchicalMethod],
        *,
        context: Mapping[str, object] | None = None,
        dependencies: Mapping[str, Sequence[str]] | None = None,
    ) -> HierarchicalPlanResult:
        context = context or {}

        by_name: dict[str, list[HierarchicalMethod]] = {}
        for item in methods:
            wrapped = (
                item if isinstance(item, HierarchicalMethod)
                else HierarchicalMethod(item)
            )
            by_name.setdefault(wrapped.method.task_name, []).append(wrapped)

        for candidates in by_name.values():
            candidates.sort(
                key=lambda item: (
                    -item.method.priority,
                    item.method.method_id,
                )
            )

        primitive: list[Task] = []
        applied: list[str] = []
        trace: list[DecompositionRecord] = []
        expanded = 0

        def visit(
            task: Task,
            stack: tuple[str, ...],
            depth: int,
        ) -> None:
            nonlocal expanded
            expanded += 1

            if expanded > self.max_nodes:
                raise ValueError("hierarchical max_nodes exceeded")

            if task.primitive:
                primitive.append(task)
                return

            if depth >= self.max_depth:
                raise ValueError("hierarchical max_depth exceeded")

            candidates = by_name.get(task.name, [])
            applicable = [
                candidate for candidate in candidates
                if candidate.is_applicable(context)
            ]

            if not applicable:
                raise ValueError(
                    f"no applicable decomposition method for {task.name!r}"
                )

            selected = applicable[0]
            method = selected.method

            if method.method_id in stack:
                raise ValueError(
                    f"hierarchical decomposition cycle at {method.method_id!r}"
                )

            child_ids = tuple(child.task_id for child in method.subtasks)
            trace.append(
                DecompositionRecord(
                    parent_task_id=task.task_id,
                    method_id=method.method_id,
                    child_task_ids=child_ids,
                )
            )
            applied.append(method.method_id)

            for child in method.subtasks:
                visit(child, stack + (method.method_id,), depth + 1)

        for task in tasks:
            if not isinstance(task, Task):
                raise TypeError("tasks must contain Task values")
            visit(task, (), 0)

        ordered_ids = resolve_task_dependencies(primitive, dependencies)
        by_id = {task.task_id: task for task in primitive}
        ordered_tasks = tuple(by_id[task_id] for task_id in ordered_ids)

        return HierarchicalPlanResult(
            primitive_tasks=ordered_tasks,
            ordered_task_ids=ordered_ids,
            applied_methods=tuple(applied),
            decomposition_trace=tuple(trace),
            expanded_nodes=expanded,
            dependencies=tuple(
                (task_id, tuple(sorted(predecessors)))
                for task_id, predecessors in sorted((dependencies or {}).items())
            ),
        )
