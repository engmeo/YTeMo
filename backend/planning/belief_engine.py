"""Bayesian belief updates with explicit, auditable likelihood inputs."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from math import isfinite, log2
from types import MappingProxyType
from typing import Mapping

from .models import BeliefHypothesis, BeliefState


def _timestamp(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("observed_at must be a non-empty ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise ValueError("observed_at must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("observed_at must include a timezone")


@dataclass(frozen=True)
class EvidenceLikelihood:
    evidence_id: str
    source_type: str
    source_id: str
    observed_at: str
    likelihoods: Mapping[str, float]
    reliability: float = 1.0

    def __post_init__(self) -> None:
        for name in ("evidence_id", "source_type", "source_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        _timestamp(self.observed_at)
        if isinstance(self.reliability, bool) or not isinstance(self.reliability, (int, float)) or not isfinite(self.reliability) or not 0 <= self.reliability <= 1:
            raise ValueError("reliability must be a finite number between 0 and 1")
        copied = {}
        for key, value in self.likelihoods.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("likelihood hypothesis ids must be non-empty")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 <= value <= 1:
                raise ValueError("likelihood values must be finite numbers between 0 and 1")
            copied[key] = float(value)
        if not copied:
            raise ValueError("at least one likelihood is required")
        object.__setattr__(self, "likelihoods", MappingProxyType(copied))


@dataclass(frozen=True)
class BeliefUpdateResult:
    belief: BeliefState
    evidence_id: str
    prior_entropy_bits: float
    posterior_entropy_bits: float
    entropy_reduction_bits: float


def entropy_bits(probabilities) -> float:
    return -sum(p * log2(p) for p in probabilities if p > 0)


def update_belief(belief: BeliefState, evidence: EvidenceLikelihood) -> BeliefUpdateResult:
    """Apply one likelihood update; no evidence is inferred or fetched implicitly.

    Reliability tempers each likelihood toward the neutral multiplier 1.0.
    A zero reliability therefore leaves the prior unchanged.
    """
    hypotheses = belief.hypotheses
    if not hypotheses:
        raise ValueError("BeliefState requires at least one hypothesis")
    ids = {item.hypothesis_id for item in hypotheses}
    unknown = set(evidence.likelihoods) - ids
    if unknown:
        raise ValueError(f"Evidence references unknown hypotheses: {sorted(unknown)}")
    if any(evidence.evidence_id in item.evidence_refs for item in hypotheses):
        raise ValueError("Evidence has already been applied to this belief state")
    prior_total = sum(item.probability for item in hypotheses)
    if prior_total <= 0:
        raise ValueError("Prior hypothesis probabilities must sum to a positive value")
    priors = [item.probability / prior_total for item in hypotheses]
    prior_entropy = entropy_bits(priors)
    weighted = []
    for item, prior in zip(hypotheses, priors):
        likelihood = evidence.likelihoods.get(item.hypothesis_id, 1.0)
        tempered = likelihood ** float(evidence.reliability)
        weighted.append(prior * tempered)
    total = sum(weighted)
    if not isfinite(total) or total <= 0:
        raise ValueError("Evidence makes every hypothesis impossible; belief update rejected")
    posterior = [value / total for value in weighted]
    updated = tuple(
        replace(item, probability=probability, evidence_refs=item.evidence_refs + (evidence.evidence_id,))
        for item, probability in zip(hypotheses, posterior)
    )
    new_belief = replace(belief, hypotheses=updated)
    posterior_entropy = entropy_bits(posterior)
    return BeliefUpdateResult(new_belief, evidence.evidence_id, prior_entropy, posterior_entropy, prior_entropy - posterior_entropy)
