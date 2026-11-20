"""Conversion from hierarchical planning results to core Plan contracts."""
from __future__ import annotations

from typing import Any, Mapping

from .hierarchical_engine import HierarchicalPlanResult
from .models import (
    Goal,
    Plan,
    PlanStep,
    StateSnapshot,
    StepRisk,
)
from .validation import (
    PlanningPolicy,
    PlanValidationResult,
    validate_plan,
)


def hierarchical_result_to_plan(
    goal: Goal,
    state: StateSnapshot,
    result: HierarchicalPlanResult,
    *,
    task_payload_defaults: Mapping[str, Mapping[str, Any]] | None = None,
    policy: PlanningPolicy | None = None,
) -> tuple[Plan, PlanValidationResult]:
    """Convert an HTN result into a validated, non-executable core Plan.

    Task payload conventions:
      action: action identifier (defaults to task.name)
      description: human-readable description (defaults to task.name)
      preconditions: sequence of strings
      effects: mapping
      risk: StepRisk value or enum string
      requires_human_approval: bool
      expected_duration_seconds: non-negative integer or None
      resource_requirements: mapping
      evidence_refs: sequence of strings

    Dependencies are taken from the explicit HTN dependency graph.
    """

    if not isinstance(goal, Goal) or not isinstance(state, StateSnapshot):
        raise TypeError("goal and state must use core planning models")
    if not isinstance(result, HierarchicalPlanResult):
        raise TypeError("result must be a HierarchicalPlanResult")
    if goal.domain.casefold() != state.domain.casefold():
        raise ValueError("goal and state domains must match")

    dependency_map = dict(result.dependencies)
    task_ids = {task.task_id for task in result.primitive_tasks}

    if set(result.ordered_task_ids) != task_ids:
        raise ValueError("HTN task ordering does not match primitive tasks")

    steps: list[PlanStep] = []

    for task in result.primitive_tasks:
        payload = dict(task.payload or {})
        payload.update((task_payload_defaults or {}).get(task.task_id, {}))

        raw_risk = payload.get("risk", StepRisk.LOW)
        try:
            risk = raw_risk if isinstance(raw_risk, StepRisk) else StepRisk(raw_risk)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"invalid risk for hierarchical task {task.task_id!r}"
            ) from exc

        description = payload.get("description", task.name)
        action = payload.get("action", task.name)

        steps.append(
            PlanStep(
                step_id=task.task_id,
                action=action,
                description=description,
                depends_on=tuple(dependency_map.get(task.task_id, ())),
                preconditions=tuple(payload.get("preconditions", ())),
                effects=payload.get("effects", {}),
                risk=risk,
                requires_human_approval=bool(
                    payload.get("requires_human_approval", False)
                ),
                expected_duration_seconds=payload.get(
                    "expected_duration_seconds"
                ),
                resource_requirements=payload.get(
                    "resource_requirements", {}
                ),
                evidence_refs=tuple(payload.get("evidence_refs", ())),
                metadata={
                    "hierarchical_task_id": task.task_id,
                    "hierarchical_task_name": task.name,
                    "hierarchical_primitive": task.primitive,
                },
            )
        )

    plan = Plan.create(
        goal,
        state,
        tuple(steps),
        rationale="Generated from a domain-neutral hierarchical decomposition.",
        assumptions=(),
    )

    metadata = dict(plan.metadata)
    metadata["hierarchical_planning"] = {
        "applied_methods": list(result.applied_methods),
        "ordered_task_ids": list(result.ordered_task_ids),
        "decomposition_trace": [
            {
                "parent_task_id": record.parent_task_id,
                "method_id": record.method_id,
                "child_task_ids": list(record.child_task_ids),
            }
            for record in result.decomposition_trace
        ],
        "expanded_nodes": result.expanded_nodes,
        "dependencies": {
            task_id: list(predecessors)
            for task_id, predecessors in result.dependencies
        },
    }

    from dataclasses import replace
    plan = replace(plan, metadata=metadata)

    validation = validate_plan(plan, policy=policy)
    return plan, validation
