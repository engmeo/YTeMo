"""Static structural verification for proposed plans; no action execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationFinding:
    code: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class VerificationReport:
    valid: bool
    findings: tuple[VerificationFinding, ...]


def verify_plan_structure(plan: Any) -> VerificationReport:
    steps = getattr(plan, "steps", None)
    if steps is None:
        return VerificationReport(False, (VerificationFinding(
            "steps_missing", "Plan must expose a steps collection."
        ),))

    findings: list[VerificationFinding] = []
    ids: list[str] = []
    dependencies: dict[str, tuple[str, ...]] = {}
    for index, step in enumerate(steps):
        step_id = getattr(step, "id", None)
        if not isinstance(step_id, str) or not step_id.strip():
            findings.append(VerificationFinding(
                "step_id_invalid", f"Step at index {index} has no valid id."
            ))
            continue
        ids.append(step_id)
        raw_deps = getattr(step, "dependencies", ())
        try:
            dependencies[step_id] = tuple(raw_deps)
        except TypeError:
            findings.append(VerificationFinding(
                "dependencies_invalid", f"Dependencies for {step_id} are not iterable."
            ))
            dependencies[step_id] = ()

    if len(ids) != len(set(ids)):
        findings.append(VerificationFinding("duplicate_step_id", "Step identifiers must be unique."))

    known = set(ids)
    for step_id, deps in dependencies.items():
        for dependency in deps:
            if dependency not in known:
                findings.append(VerificationFinding(
                    "dependency_missing", f"{step_id} depends on unknown step {dependency}."
                ))
            if dependency == step_id:
                findings.append(VerificationFinding(
                    "self_dependency", f"{step_id} cannot depend on itself."
                ))

    # Cycle detection over known dependency edges.
    visiting: set[str] = set()
    visited: set[str] = set()
    cycle_found = False

    def visit(node: str) -> None:
        nonlocal cycle_found
        if node in visiting:
            cycle_found = True
            return
        if node in visited:
            return
        visiting.add(node)
        for dep in dependencies.get(node, ()):
            if dep in known:
                visit(dep)
        visiting.remove(node)
        visited.add(node)

    for node in known:
        visit(node)
    if cycle_found:
        findings.append(VerificationFinding("dependency_cycle", "Plan dependency graph contains a cycle."))

    return VerificationReport(not findings, tuple(findings))
