"""Domain-neutral meta-cognitive intelligence primitives.

This module evaluates planning strategies from verified outcomes,
maintains bounded online statistics, and produces auditable recommendations.

It does not execute strategies, modify safety policies, or persist application data.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite, log, sqrt
from typing import Optional, Sequence


class MetaDecisionStatus(str, Enum):
    SELECTED = "selected"
    HUMAN_REVIEW = "human_review"
    NO_FEASIBLE_STRATEGY = "no_feasible_strategy"


class ReasoningAction(str, Enum):
    CONTINUE_SEARCH = "continue_search"
    EVALUATE = "evaluate"
    STOP = "stop"
    HUMAN_REVIEW = "human_review"


@dataclass(frozen=True)
class StrategyProfile:
    """Bounded online statistics for one planning strategy."""

    strategy_id: str
    trials: int = 0
    verified_trials: int = 0
    failures: int = 0
    mean_reward: float = 0.0
    reward_m2: float = 0.0
    mean_cost: float = 0.0
    mean_latency_ms: float = 0.0
    last_evidence_id: Optional[str] = None

    @property
    def reward_variance(self) -> float:
        if self.verified_trials < 2:
            return 0.0
        return self.reward_m2 / (self.verified_trials - 1)

    def updated(self, evidence: "OutcomeEvidence") -> "StrategyProfile":
        n = self.verified_trials + 1
        delta = evidence.observed_utility - self.mean_reward
        new_mean = self.mean_reward + delta / n
        delta_after = evidence.observed_utility - new_mean
        new_m2 = self.reward_m2 + delta * delta_after

        cost_n = self.trials + 1
        new_cost = self.mean_cost + (
            evidence.resource_cost - self.mean_cost
        ) / cost_n
        new_latency = self.mean_latency_ms + (
            evidence.latency_ms - self.mean_latency_ms
        ) / cost_n

        failed = evidence.failure_class is not None

        return StrategyProfile(
            strategy_id=self.strategy_id,
            trials=self.trials + 1,
            verified_trials=n,
            failures=self.failures + int(failed),
            mean_reward=new_mean,
            reward_m2=new_m2,
            mean_cost=new_cost,
            mean_latency_ms=new_latency,
            last_evidence_id=evidence.evidence_id,
        )


@dataclass(frozen=True)
class MetaCognitiveState:
    """Compact state; deliberately stores profiles, not full event history."""

    profiles: tuple[StrategyProfile, ...] = ()
    revision: int = 0

    def get_profile(self, strategy_id: str) -> Optional[StrategyProfile]:
        for profile in self.profiles:
            if profile.strategy_id == strategy_id:
                return profile
        return None


@dataclass(frozen=True)
class OutcomeEvidence:
    evidence_id: str
    strategy_id: str
    expected_utility: float
    observed_utility: float
    verified: bool
    resource_cost: float = 0.0
    latency_ms: float = 0.0
    failure_class: Optional[str] = None
    safety_violation: bool = False
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.strategy_id.strip():
            raise ValueError("evidence_id and strategy_id must not be empty")
        for name in (
            "expected_utility",
            "observed_utility",
            "resource_cost",
            "latency_ms",
        ):
            value = getattr(self, name)
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.resource_cost < 0 or self.latency_ms < 0:
            raise ValueError("resource_cost and latency_ms cannot be negative")


@dataclass(frozen=True)
class EvidenceUpdateResult:
    state: MetaCognitiveState
    accepted: bool
    reason: str


def record_verified_outcome(
    state: MetaCognitiveState,
    evidence: OutcomeEvidence,
) -> EvidenceUpdateResult:
    """Update online statistics only from verified, safety-clean evidence."""

    if not evidence.verified:
        return EvidenceUpdateResult(state, False, "evidence_not_verified")
    if evidence.safety_violation:
        return EvidenceUpdateResult(state, False, "safety_violation")
    if state.get_profile(evidence.strategy_id) is not None:
        existing = state.get_profile(evidence.strategy_id)
        if existing.last_evidence_id == evidence.evidence_id:
            return EvidenceUpdateResult(state, False, "duplicate_evidence")

    profiles = list(state.profiles)
    current = state.get_profile(evidence.strategy_id)

    if current is None:
        current = StrategyProfile(strategy_id=evidence.strategy_id)

    updated = current.updated(evidence)
    replaced = False

    for index, profile in enumerate(profiles):
        if profile.strategy_id == evidence.strategy_id:
            profiles[index] = updated
            replaced = True
            break

    if not replaced:
        profiles.append(updated)

    profiles.sort(key=lambda item: item.strategy_id)

    return EvidenceUpdateResult(
        MetaCognitiveState(
            profiles=tuple(profiles),
            revision=state.revision + 1,
        ),
        True,
        "verified_evidence_recorded",
    )


@dataclass(frozen=True)
class FailureAnalysis:
    strategy_id: str
    expected_utility: float
    observed_utility: float
    utility_delta: float
    failure_class: Optional[str]
    evidence_verified: bool
    evidence_refs: tuple[str, ...]


def analyze_outcome(evidence: OutcomeEvidence) -> FailureAnalysis:
    return FailureAnalysis(
        strategy_id=evidence.strategy_id,
        expected_utility=evidence.expected_utility,
        observed_utility=evidence.observed_utility,
        utility_delta=evidence.observed_utility - evidence.expected_utility,
        failure_class=evidence.failure_class,
        evidence_verified=evidence.verified,
        evidence_refs=evidence.evidence_refs,
    )


@dataclass(frozen=True)
class StrategyCandidate:
    strategy_id: str
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    safety_eligible: bool = True
    requires_human_approval: bool = False

    def __post_init__(self) -> None:
        if not self.strategy_id.strip():
            raise ValueError("strategy_id must not be empty")
        if not isfinite(self.estimated_cost) or self.estimated_cost < 0:
            raise ValueError("estimated_cost must be finite and non-negative")
        if (
            not isfinite(self.estimated_latency_ms)
            or self.estimated_latency_ms < 0
        ):
            raise ValueError(
                "estimated_latency_ms must be finite and non-negative"
            )


@dataclass(frozen=True)
class MetaPolicy:
    """Immutable meta-level limits; not a replacement for the safety policy."""

    policy_version: str = "1"
    exploration_coefficient: float = 1.0
    cost_weight: float = 0.1
    latency_weight: float = 0.001
    failure_penalty: float = 0.25
    max_resource_cost: float = 100.0
    max_latency_ms: float = 30000.0
    allow_bounded_exploration: bool = True
    min_verified_trials: int = 1

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version must not be empty")
        for name in (
            "exploration_coefficient",
            "cost_weight",
            "latency_weight",
            "failure_penalty",
            "max_resource_cost",
            "max_latency_ms",
        ):
            value = getattr(self, name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.min_verified_trials < 1:
            raise ValueError("min_verified_trials must be at least 1")


@dataclass(frozen=True)
class StrategyAssessment:
    strategy_id: str
    eligible: bool
    score: Optional[float]
    reasons: tuple[str, ...]
    verified_trials: int


@dataclass(frozen=True)
class IntrospectionTrace:
    policy_version: str
    state_revision: int
    assessments: tuple[StrategyAssessment, ...]
    selected_strategy_id: Optional[str]
    decision_reasons: tuple[str, ...]


@dataclass(frozen=True)
class MetaDecision:
    status: MetaDecisionStatus
    selected_strategy_id: Optional[str]
    assessments: tuple[StrategyAssessment, ...]
    trace: IntrospectionTrace


def select_strategy(
    candidates: Sequence[StrategyCandidate],
    state: MetaCognitiveState,
    policy: MetaPolicy = MetaPolicy(),
) -> MetaDecision:
    """Recommend a strategy using verified performance and bounded exploration.

    This function never executes the selected strategy.
    """

    if len({item.strategy_id for item in candidates}) != len(candidates):
        raise ValueError("candidate strategy_id values must be unique")

    total_trials = sum(p.verified_trials for p in state.profiles)
    assessments = []

    for candidate in candidates:
        reasons = []
        profile = state.get_profile(candidate.strategy_id)

        if not candidate.safety_eligible:
            reasons.append("excluded_by_external_safety_gate")
        if candidate.requires_human_approval:
            reasons.append("human_approval_required")
        if candidate.estimated_cost > policy.max_resource_cost:
            reasons.append("resource_budget_exceeded")
        if candidate.estimated_latency_ms > policy.max_latency_ms:
            reasons.append("latency_budget_exceeded")

        eligible = not reasons
        score = None
        verified_trials = profile.verified_trials if profile else 0

        if eligible:
            if profile is None or profile.verified_trials == 0:
                if policy.allow_bounded_exploration:
                    score = (
                        -policy.cost_weight * candidate.estimated_cost
                        -policy.latency_weight * candidate.estimated_latency_ms
                    )
                    reasons.append("bounded_cold_start_exploration")
                else:
                    eligible = False
                    reasons.append("no_verified_performance_evidence")
            else:
                exploration = policy.exploration_coefficient * sqrt(
                    log(total_trials + 1) / profile.verified_trials
                )
                failure_rate = profile.failures / max(profile.trials, 1)
                score = (
                    profile.mean_reward
                    + exploration
                    - policy.cost_weight * candidate.estimated_cost
                    - policy.latency_weight * candidate.estimated_latency_ms
                    - policy.failure_penalty * failure_rate
                )
                reasons.append("score_uses_verified_online_statistics")

        assessments.append(
            StrategyAssessment(
                strategy_id=candidate.strategy_id,
                eligible=eligible,
                score=score,
                reasons=tuple(reasons),
                verified_trials=verified_trials,
            )
        )

    eligible_assessments = [item for item in assessments if item.eligible]

    if not eligible_assessments:
        status = (
            MetaDecisionStatus.HUMAN_REVIEW
            if any(item.requires_human_approval for item in candidates)
            else MetaDecisionStatus.NO_FEASIBLE_STRATEGY
        )
        selected = None
        decision_reasons = ("no_candidate_passed_meta_level_constraints",)
    else:
        # Stable deterministic tie-break: score, then strategy identifier.
        winner = sorted(
            eligible_assessments,
            key=lambda item: (-float(item.score), item.strategy_id),
        )[0]
        selected = winner.strategy_id
        status = MetaDecisionStatus.SELECTED
        decision_reasons = (
            "highest_meta_score_among_eligible_candidates",
            "recommendation_only_no_execution_performed",
        )

    trace = IntrospectionTrace(
        policy_version=policy.policy_version,
        state_revision=state.revision,
        assessments=tuple(assessments),
        selected_strategy_id=selected,
        decision_reasons=decision_reasons,
    )

    return MetaDecision(
        status=status,
        selected_strategy_id=selected,
        assessments=tuple(assessments),
        trace=trace,
    )


@dataclass(frozen=True)
class ReasoningBudget:
    max_iterations: int
    used_iterations: int = 0
    max_compute_units: float = 0.0
    used_compute_units: float = 0.0
    max_latency_ms: float = 0.0
    used_latency_ms: float = 0.0

    def __post_init__(self) -> None:
        if self.max_iterations < 0 or self.used_iterations < 0:
            raise ValueError("iteration counts cannot be negative")
        if self.used_iterations > self.max_iterations:
            raise ValueError("used_iterations exceeds max_iterations")
        for name in (
            "max_compute_units",
            "used_compute_units",
            "max_latency_ms",
            "used_latency_ms",
        ):
            value = getattr(self, name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.used_compute_units > self.max_compute_units:
            raise ValueError("used_compute_units exceeds budget")
        if self.used_latency_ms > self.max_latency_ms:
            raise ValueError("used_latency_ms exceeds budget")


@dataclass(frozen=True)
class ReasoningAssessment:
    action: ReasoningAction
    reasons: tuple[str, ...]
    remaining_iterations: int
    remaining_compute_units: float
    remaining_latency_ms: float


def assess_reasoning_budget(
    budget: ReasoningBudget,
    expected_value_of_more_reasoning: float,
    estimated_next_compute_units: float = 0.0,
    estimated_next_latency_ms: float = 0.0,
    requires_human_review: bool = False,
) -> ReasoningAssessment:
    """Decide whether to continue reasoning, evaluate, stop, or escalate."""

    values = (
        expected_value_of_more_reasoning,
        estimated_next_compute_units,
        estimated_next_latency_ms,
    )
    if any(not isfinite(value) for value in values):
        raise ValueError("reasoning estimates must be finite")
    if estimated_next_compute_units < 0 or estimated_next_latency_ms < 0:
        raise ValueError("estimated next resource use cannot be negative")

    remaining_iterations = budget.max_iterations - budget.used_iterations
    remaining_compute = budget.max_compute_units - budget.used_compute_units
    remaining_latency = budget.max_latency_ms - budget.used_latency_ms

    if requires_human_review:
        action = ReasoningAction.HUMAN_REVIEW
        reasons = ("human_review_required_by_caller",)
    elif remaining_iterations <= 0:
        action = ReasoningAction.STOP
        reasons = ("iteration_budget_exhausted",)
    elif (
        estimated_next_compute_units > remaining_compute
        or estimated_next_latency_ms > remaining_latency
    ):
        action = ReasoningAction.STOP
        reasons = ("remaining_resource_budget_insufficient",)
    elif expected_value_of_more_reasoning <= 0:
        action = ReasoningAction.EVALUATE
        reasons = ("no_positive_expected_value_from_more_reasoning",)
    else:
        action = ReasoningAction.CONTINUE_SEARCH
        reasons = ("expected_value_justifies_bounded_more_reasoning",)

    return ReasoningAssessment(
        action=action,
        reasons=reasons,
        remaining_iterations=remaining_iterations,
        remaining_compute_units=remaining_compute,
        remaining_latency_ms=remaining_latency,
    )
