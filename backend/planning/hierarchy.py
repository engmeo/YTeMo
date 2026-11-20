"""Domain-neutral Hierarchical Task Network (HTN) decomposition."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Task:
    task_id: str
    name: str
    primitive: bool = False
    payload: Mapping[str, object] | None = None

    def __post_init__(self):
        if not isinstance(self.task_id, str) or not self.task_id.strip():
            raise ValueError("task_id must be non-empty")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("task name must be non-empty")
        if self.payload is not None and not isinstance(self.payload, Mapping):
            raise ValueError("payload must be a mapping")


@dataclass(frozen=True)
class DecompositionMethod:
    method_id: str
    task_name: str
    subtasks: tuple[Task, ...]
    priority: int = 0

    def __post_init__(self):
        if not self.method_id or not self.task_name:
            raise ValueError("method_id and task_name must be non-empty")
        object.__setattr__(self, "subtasks", tuple(self.subtasks))
        if any(not isinstance(t, Task) for t in self.subtasks):
            raise ValueError("subtasks must contain Task values")


@dataclass(frozen=True)
class HTNResult:
    primitive_tasks: tuple[Task, ...]
    applied_methods: tuple[str, ...]
    expanded_nodes: int


def decompose_tasks(tasks: Sequence[Task], methods: Sequence[DecompositionMethod], *, max_depth: int = 32, max_nodes: int = 10000) -> HTNResult:
    """Deterministically decompose compound tasks; never executes primitive tasks."""
    if max_depth < 1 or max_nodes < 1:
        raise ValueError("max_depth and max_nodes must be positive")
    by_name: dict[str, list[DecompositionMethod]] = {}
    for method in methods:
        by_name.setdefault(method.task_name, []).append(method)
    for values in by_name.values():
        values.sort(key=lambda m: (-m.priority, m.method_id))
    output: list[Task] = []
    applied: list[str] = []
    expanded = 0

    def visit(task: Task, stack: tuple[str, ...], depth: int) -> None:
        nonlocal expanded
        expanded += 1
        if expanded > max_nodes:
            raise ValueError("HTN max_nodes exceeded")
        if task.primitive:
            output.append(task)
            return
        if depth >= max_depth:
            raise ValueError("HTN max_depth exceeded")
        candidates = by_name.get(task.name, [])
        if not candidates:
            raise ValueError(f"no decomposition method for compound task {task.name!r}")
        # The first deterministic applicable method is selected. Context-sensitive
        # applicability can be added by domain adapters in a later extension.
        method = candidates[0]
        if method.method_id in stack:
            raise ValueError(f"HTN decomposition cycle detected at {method.method_id!r}")
        applied.append(method.method_id)
        for subtask in method.subtasks:
            visit(subtask, stack + (method.method_id,), depth + 1)

    for task in tasks:
        if not isinstance(task, Task):
            raise ValueError("tasks must contain Task values")
        visit(task, (), 0)
    ids = [t.task_id for t in output]
    if len(ids) != len(set(ids)):
        raise ValueError("decomposition produced duplicate primitive task ids")
    return HTNResult(tuple(output), tuple(applied), expanded)
