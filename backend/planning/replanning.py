"""Replanning triggers and transparent candidate comparison."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping


@dataclass(frozen=True)
class ReplanDecision:
    should_replan: bool
    reasons: tuple[str, ...]
    affected_step_ids: tuple[str, ...]


def assess_replan(
    *,
    changed_fact_keys: Iterable[str],
    step_fact_dependencies: Mapping[str, Iterable[str]],
    explicit_trigger: str | None = None,
    risk_limit_exceeded: bool = False,
) -> ReplanDecision:
    changed = set(changed_fact_keys)
    if any(not isinstance(k, str) or not k for k in changed):
        raise ValueError("changed fact keys must be non-empty strings")
    if not isinstance(step_fact_dependencies, Mapping):
        raise ValueError("step_fact_dependencies must be a mapping")
    affected = []
    for step_id, dependencies in step_fact_dependencies.items():
        if not isinstance(step_id, str) or not step_id:
            raise ValueError("step IDs must be non-empty strings")
        deps = set(dependencies)
        if any(not isinstance(k, str) or not k for k in deps):
            raise ValueError("dependency keys must be non-empty strings")
        if changed.intersection(deps):
            affected.append(step_id)
    reasons = []
    if affected:
        reasons.append("relevant_state_changed")
    if explicit_trigger is not None:
        if not isinstance(explicit_trigger, str) or not explicit_trigger.strip():
            raise ValueError("explicit_trigger must be a non-empty string")
        reasons.append(f"explicit:{explicit_trigger.strip()}")
    if risk_limit_exceeded:
        reasons.append("risk_limit_exceeded")
    return ReplanDecision(bool(reasons), tuple(reasons), tuple(sorted(affected)))


@dataclass(frozen=True)
class PlanCandidateScore:
    candidate_id: str
    expected_utility: float
    expected_loss: float
    execution_cost: float


def rank_plan_candidates(
    candidates: Iterable[PlanCandidateScore],
    *,
    utility_weight: float = 1.0,
    risk_weight: float = 1.0,
    cost_weight: float = 1.0,
) -> tuple[tuple[str, float], ...]:
    candidates = tuple(candidates)
    weights = (utility_weight, risk_weight, cost_weight)
    if any(isinstance(w, bool) or not isinstance(w, (int, float))
           or not math.isfinite(float(w)) or float(w) < 0 for w in weights):
        raise ValueError("weights must be finite non-negative numbers")
    if any(not isinstance(c, PlanCandidateScore) for c in candidates):
        raise ValueError("candidates must contain PlanCandidateScore values")
    if len({c.candidate_id for c in candidates}) != len(candidates):
        raise ValueError("candidate IDs must be unique")
    for c in candidates:
        if not c.candidate_id:
            raise ValueError("candidate_id must be non-empty")
        for value in (c.expected_utility, c.expected_loss, c.execution_cost):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError("candidate metrics must be finite numbers")
        if c.expected_loss < 0 or c.execution_cost < 0:
            raise ValueError("loss and cost must be non-negative")
    uw, rw, cw = map(float, weights)
    scored = [
        (c.candidate_id,
         uw * float(c.expected_utility)
         - rw * float(c.expected_loss)
         - cw * float(c.execution_cost))
        for c in candidates
    ]
    return tuple(sorted(scored, key=lambda item: (-item[1], item[0])))
