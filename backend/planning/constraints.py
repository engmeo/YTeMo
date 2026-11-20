"""Small deterministic finite-domain constraint satisfaction solver."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence


@dataclass(frozen=True)
class BinaryConstraint:
    left: str
    right: str
    predicate: Callable[[object, object], bool]

    def __post_init__(self):
        if not self.left or not self.right or self.left == self.right:
            raise ValueError("constraint variables must be distinct non-empty names")
        if not callable(self.predicate):
            raise ValueError("predicate must be callable")


@dataclass(frozen=True)
class ConstraintResult:
    solved: bool
    assignment: Mapping[str, object]
    explored_nodes: int


def solve_constraints(domains: Mapping[str, Sequence[object]], constraints: Sequence[BinaryConstraint], *, max_nodes: int = 100000) -> ConstraintResult:
    """Solve a finite CSP with MRV variable ordering and forward checking."""
    if not domains or max_nodes < 1:
        raise ValueError("domains must be non-empty and max_nodes positive")
    current = {}
    for name, values in domains.items():
        if not isinstance(name, str) or not name:
            raise ValueError("variable names must be non-empty strings")
        vals = tuple(values)
        if not vals:
            raise ValueError(f"domain for {name!r} is empty")
        current[name] = vals
    links = tuple(constraints)
    for c in links:
        if not isinstance(c, BinaryConstraint) or c.left not in current or c.right not in current:
            raise ValueError("constraint references an unknown variable")

    explored = 0
    def compatible(name, value, assigned):
        for c in links:
            if c.left == name and c.right in assigned and not c.predicate(value, assigned[c.right]):
                return False
            if c.right == name and c.left in assigned and not c.predicate(assigned[c.left], value):
                return False
        return True

    def search(assigned):
        nonlocal explored
        explored += 1
        if explored > max_nodes:
            raise ValueError("CSP max_nodes exceeded")
        if len(assigned) == len(current):
            return dict(assigned)
        remaining = [n for n in current if n not in assigned]
        name = min(remaining, key=lambda n: (sum(compatible(n, v, assigned) for v in current[n]), n))
        for value in current[name]:
            if compatible(name, value, assigned):
                assigned[name] = value
                result = search(assigned)
                if result is not None:
                    return result
                del assigned[name]
        return None

    solution = search({})
    return ConstraintResult(solution is not None, solution or {}, explored)
