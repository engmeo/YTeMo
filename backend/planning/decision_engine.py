"""Domain-neutral contracts for uncertainty-aware decision making.

Contracts only: no implicit evidence collection, probability inference,
action execution, or domain-specific behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Mapping, Any


class DecisionStatus(str, Enum):
    SELECTED = "selected"
    HUMAN_REVIEW = "human_review"
    ABSTAINED = "abstained"
    NO_FEASIBLE_ACTION = "no_feasible_action"


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _unit(value: Any, name: str) -> float:
    value = _number(value, name)
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class DecisionCandidate:
    """Candidate action with caller-defined utility per hypothesis."""
    action_id: str
    description: str
    utilities: Mapping[str, float]
    cost: float = 0.0
    risk: float = 0.0
    uncertainty: float = 0.0
    preconditions_satisfied: bool | None = None
    requires_human_approval: bool = False
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self):
        _text(self.action_id, "action_id")
        _text(self.description, "description")
        if not isinstance(self.utilities, Mapping) or not self.utilities:
            raise ValueError("utilities must be a non-empty mapping")
        values = {
            _text(key, "hypothesis_id"): _number(value, f"utilities[{key}]")
            for key, value in self.utilities.items()
        }
        object.__setattr__(self, "utilities", MappingProxyType(values))
        object.__setattr__(self, "cost", _number(self.cost, "cost"))
        if self.cost < 0:
            raise ValueError("cost must be non-negative")
        object.__setattr__(self, "risk", _unit(self.risk, "risk"))
        object.__setattr__(self, "uncertainty", _unit(self.uncertainty, "uncertainty"))
        if self.preconditions_satisfied is not None and not isinstance(self.preconditions_satisfied, bool):
            raise ValueError("preconditions_satisfied must be bool or None")
        if not isinstance(self.requires_human_approval, bool):
            raise ValueError("requires_human_approval must be bool")
        refs = tuple(self.evidence_refs)
        for ref in refs:
            _text(ref, "evidence_ref")
        object.__setattr__(self, "evidence_refs", refs)


@dataclass(frozen=True)
class DecisionPolicy:
    """Explicit scoring weights and safety thresholds."""
    cost_weight: float = 1.0
    risk_weight: float = 1.0
    uncertainty_weight: float = 1.0
    max_risk: float = 1.0
    max_uncertainty: float = 1.0
    min_belief_confidence: float = 0.0
    human_review_risk_threshold: float = 1.0
    human_review_uncertainty_threshold: float = 1.0
    require_known_preconditions: bool = True

    def __post_init__(self):
        for name in ("cost_weight", "risk_weight", "uncertainty_weight"):
            value = _number(getattr(self, name), name)
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
            object.__setattr__(self, name, value)
        for name in (
            "max_risk",
            "max_uncertainty",
            "min_belief_confidence",
            "human_review_risk_threshold",
            "human_review_uncertainty_threshold",
        ):
            object.__setattr__(self, name, _unit(getattr(self, name), name))
        if not isinstance(self.require_known_preconditions, bool):
            raise ValueError("require_known_preconditions must be bool")


@dataclass(frozen=True)
class DecisionEvaluation:
    """Auditable score breakdown for one candidate."""
    action_id: str
    expected_utility: float
    cost_penalty: float
    risk_penalty: float
    uncertainty_penalty: float
    score: float
    feasible: bool
    reasons: tuple[str, ...] = ()

    def __post_init__(self):
        _text(self.action_id, "action_id")
        for name in ("expected_utility", "cost_penalty", "risk_penalty", "uncertainty_penalty", "score"):
            object.__setattr__(self, name, _number(getattr(self, name), name))
        for name in ("cost_penalty", "risk_penalty", "uncertainty_penalty"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if not isinstance(self.feasible, bool):
            raise ValueError("feasible must be bool")
        reasons = tuple(self.reasons)
        for reason in reasons:
            _text(reason, "reason")
        object.__setattr__(self, "reasons", reasons)


@dataclass(frozen=True)
class DecisionTrace:
    """Provenance needed to review and reproduce a decision."""
    status: DecisionStatus
    belief_revision: int
    world_revision: int | None
    selected_action_id: str | None
    rationale: str
    assumptions: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.status, DecisionStatus):
            raise ValueError("status must be DecisionStatus")
        if isinstance(self.belief_revision, bool) or not isinstance(self.belief_revision, int) or self.belief_revision < 0:
            raise ValueError("belief_revision must be a non-negative integer")
        if self.world_revision is not None and (
            isinstance(self.world_revision, bool) or not isinstance(self.world_revision, int) or self.world_revision < 0
        ):
            raise ValueError("world_revision must be None or a non-negative integer")
        if self.selected_action_id is not None:
            _text(self.selected_action_id, "selected_action_id")
        _text(self.rationale, "rationale")
        assumptions, refs = tuple(self.assumptions), tuple(self.evidence_refs)
        for item in assumptions:
            _text(item, "assumption")
        for item in refs:
            _text(item, "evidence_ref")
        object.__setattr__(self, "assumptions", assumptions)
        object.__setattr__(self, "evidence_refs", refs)
        needs_candidate = self.status in (DecisionStatus.SELECTED, DecisionStatus.HUMAN_REVIEW)
        if needs_candidate != (self.selected_action_id is not None):
            raise ValueError("selected_action_id is required only for selected/review decisions")


@dataclass(frozen=True)
class DecisionResult:
    """Final outcome, candidate evaluations, and provenance."""
    status: DecisionStatus
    selected_action_id: str | None
    evaluations: tuple[DecisionEvaluation, ...]
    trace: DecisionTrace

    def __post_init__(self):
        if not isinstance(self.status, DecisionStatus):
            raise ValueError("status must be DecisionStatus")
        evaluations = tuple(self.evaluations)
        ids = [item.action_id for item in evaluations]
        if len(ids) != len(set(ids)):
            raise ValueError("evaluation action ids must be unique")
        if self.status != self.trace.status or self.selected_action_id != self.trace.selected_action_id:
            raise ValueError("result and trace fields must agree")
        if self.selected_action_id is not None and self.selected_action_id not in ids:
            raise ValueError("selected action must exist in evaluations")
        object.__setattr__(self, "evaluations", evaluations)
from .models import BeliefState


def _belief_distribution(belief: BeliefState) -> tuple[dict[str, float], float]:
    """Return normalized hypothesis probabilities and entropy-derived concentration.

    Concentration is a mathematical summary, not a calibrated probability
    that a hypothesis is true.
    """
    if not isinstance(belief, BeliefState):
        raise TypeError("belief must be a BeliefState")
    if not belief.hypotheses:
        raise ValueError("belief must contain at least one hypothesis")

    raw = {}
    for item in belief.hypotheses:
        probability = _number(item.probability, "hypothesis probability")
        if probability < 0:
            raise ValueError("hypothesis probabilities must be non-negative")
        raw[item.hypothesis_id] = probability

    total = sum(raw.values())
    if not isfinite(total) or total <= 0:
        raise ValueError("hypothesis probabilities must have positive total")

    probabilities = {key: value / total for key, value in raw.items()}

    positive = [p for p in probabilities.values() if p > 0]
    entropy = -sum(p * __import__("math").log2(p) for p in positive)

    count = len(probabilities)
    concentration = 1.0 if count == 1 else max(
        0.0, min(1.0, 1.0 - entropy / __import__("math").log2(count))
    )
    return probabilities, concentration


def evaluate_candidate(
    belief: BeliefState,
    candidate: DecisionCandidate,
    policy: DecisionPolicy | None = None,
) -> DecisionEvaluation:
    """Evaluate one action using expected utility and explicit penalties."""
    if not isinstance(candidate, DecisionCandidate):
        raise TypeError("candidate must be a DecisionCandidate")

    policy = policy or DecisionPolicy()
    if not isinstance(policy, DecisionPolicy):
        raise TypeError("policy must be a DecisionPolicy")

    probabilities, belief_confidence = _belief_distribution(belief)
    if set(candidate.utilities) != set(probabilities):
        raise ValueError(
            "candidate utilities must cover exactly the belief hypothesis ids"
        )

    expected_utility = sum(
        probabilities[h] * candidate.utilities[h]
        for h in probabilities
    )

    cost_penalty = policy.cost_weight * candidate.cost
    risk_penalty = policy.risk_weight * candidate.risk
    uncertainty_penalty = policy.uncertainty_weight * candidate.uncertainty

    score = (
        expected_utility
        - cost_penalty
        - risk_penalty
        - uncertainty_penalty
    )

    reasons = []

    if candidate.preconditions_satisfied is False:
        reasons.append("preconditions are not satisfied")
    elif candidate.preconditions_satisfied is None and policy.require_known_preconditions:
        reasons.append("preconditions are unknown")

    if candidate.risk > policy.max_risk:
        reasons.append("risk exceeds policy maximum")

    if candidate.uncertainty > policy.max_uncertainty:
        reasons.append("uncertainty exceeds policy maximum")

    if belief_confidence < policy.min_belief_confidence:
        reasons.append("belief concentration is below policy minimum")

    return DecisionEvaluation(
        action_id=candidate.action_id,
        expected_utility=expected_utility,
        cost_penalty=cost_penalty,
        risk_penalty=risk_penalty,
        uncertainty_penalty=uncertainty_penalty,
        score=score,
        feasible=not reasons,
        reasons=tuple(reasons),
    )


def evaluate_candidates(
    belief: BeliefState,
    candidates: tuple[DecisionCandidate, ...],
    policy: DecisionPolicy | None = None,
) -> tuple[DecisionEvaluation, ...]:
    """Evaluate a candidate set without selecting or executing an action."""
    candidates = tuple(candidates)

    if not candidates:
        raise ValueError("at least one candidate is required")

    ids = [item.action_id for item in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate action ids must be unique")

    return tuple(
        evaluate_candidate(belief, candidate, policy)
        for candidate in candidates
    )
from dataclasses import replace as _replace

from .world_model import WorldPrediction


def select_decision(
    belief: BeliefState,
    candidates: tuple[DecisionCandidate, ...],
    policy: DecisionPolicy | None = None,
    *,
    world_predictions: tuple[WorldPrediction, ...] = (),
    world_revision: int | None = None,
    tie_tolerance: float = 1e-9,
) -> DecisionResult:
    """Select a feasible action without executing it.

    When predictions are supplied, each candidate must have a matching
    prediction. Inapplicable or stale predictions make that candidate
    infeasible. Prediction uncertainty is combined conservatively using max.
    """
    candidates = tuple(candidates)
    world_predictions = tuple(world_predictions)

    if not candidates:
        raise ValueError("at least one candidate is required")
    if not isfinite(tie_tolerance) or tie_tolerance < 0:
        raise ValueError("tie_tolerance must be finite and non-negative")

    policy = policy or DecisionPolicy()
    if not isinstance(policy, DecisionPolicy):
        raise TypeError("policy must be a DecisionPolicy")

    candidate_ids = [item.action_id for item in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("candidate action ids must be unique")

    predictions_by_action = {}
    for prediction in world_predictions:
        if not isinstance(prediction, WorldPrediction):
            raise TypeError("world_predictions must contain WorldPrediction items")
        action_id = prediction.action
        if action_id in predictions_by_action:
            raise ValueError("duplicate world predictions for an action")
        predictions_by_action[action_id] = prediction

    prediction_revisions = {
        item.source_revision for item in world_predictions
    }
    if world_revision is None and len(prediction_revisions) == 1:
        world_revision = next(iter(prediction_revisions))
    elif len(prediction_revisions) > 1 and world_revision is None:
        raise ValueError("world predictions must share one source revision")

    evaluations = []
    effective_uncertainties = {}
    for candidate in candidates:
        prediction = predictions_by_action.get(candidate.action_id)

        if world_predictions and prediction is None:
            effective_uncertainties[candidate.action_id] = candidate.uncertainty
            result = evaluate_candidate(belief, candidate, policy)
            evaluations.append(_replace(
                result,
                feasible=False,
                reasons=result.reasons + ("world prediction is missing",),
            ))
            continue

        evaluated_candidate = candidate
        extra_reasons = []

        if prediction is not None:
            applicable = getattr(
                prediction,
                "applicable",
                getattr(prediction, "applicability", False),
            )
            if not applicable:
                extra_reasons.append("world prediction is not applicable")

            if (
                world_revision is not None
                and prediction.source_revision != world_revision
            ):
                extra_reasons.append("world prediction is stale")

            prediction_uncertainty = _number(
                prediction.uncertainty, "prediction uncertainty"
            )
            if not 0 <= prediction_uncertainty <= 1:
                raise ValueError("prediction uncertainty must be in [0, 1]")

            evaluated_candidate = _replace(
                candidate,
                uncertainty=max(candidate.uncertainty, prediction_uncertainty),
            )

        effective_uncertainties[candidate.action_id] = evaluated_candidate.uncertainty
        result = evaluate_candidate(belief, evaluated_candidate, policy)
        if extra_reasons:
            result = _replace(
                result,
                feasible=False,
                reasons=result.reasons + tuple(extra_reasons),
            )
        evaluations.append(result)

    evaluations = tuple(evaluations)
    feasible = [item for item in evaluations if item.feasible]

    belief_revision = belief.snapshot.revision

    if not feasible:
        status = DecisionStatus.NO_FEASIBLE_ACTION
        selected_id = None
        rationale = "No candidate satisfies the current decision policy."
        evidence_refs = ()
    else:
        ranked = sorted(feasible, key=lambda item: item.score, reverse=True)
        best = ranked[0]

        tied = [
            item for item in ranked
            if abs(item.score - best.score) <= tie_tolerance
        ]

        if len(tied) > 1:
            status = DecisionStatus.ABSTAINED
            selected_id = None
            rationale = (
                "Multiple feasible candidates have indistinguishable scores; "
                "the engine abstains instead of choosing arbitrarily."
            )
            evidence_refs = tuple(dict.fromkeys(
                ref
                for item in candidates
                if item.action_id in {entry.action_id for entry in tied}
                for ref in item.evidence_refs
            ))
        else:
            chosen = next(
                item for item in candidates
                if item.action_id == best.action_id
            )
            selected_id = chosen.action_id
            evidence_refs = chosen.evidence_refs

            if (
                chosen.requires_human_approval
                or chosen.risk >= policy.human_review_risk_threshold
                or effective_uncertainties.get(
                    chosen.action_id, chosen.uncertainty
                ) >= policy.human_review_uncertainty_threshold
            ):
                status = DecisionStatus.HUMAN_REVIEW
                rationale = (
                    "Best feasible candidate requires human approval "
                    "or meets the human-review risk threshold."
                )
            else:
                status = DecisionStatus.SELECTED
                rationale = "Selected the highest-scoring feasible candidate."

    trace = DecisionTrace(
        status=status,
        belief_revision=belief_revision,
        world_revision=world_revision,
        selected_action_id=selected_id,
        rationale=rationale,
        evidence_refs=tuple(evidence_refs),
    )

    return DecisionResult(
        status=status,
        selected_action_id=selected_id,
        evaluations=evaluations,
        trace=trace,
    )

