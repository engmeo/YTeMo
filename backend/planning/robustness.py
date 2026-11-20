"""Scenario-based robustness comparison for candidate plans."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    probability: float
    utilities: Mapping[str, float]

    def __post_init__(self) -> None:
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
            raise ValueError("scenario_id must be a non-empty string")
        probability = float(self.probability)
        if not math.isfinite(probability) or probability < 0:
            raise ValueError("scenario probability must be finite and non-negative")
        values = dict(self.utilities)
        if not values:
            raise ValueError("scenario utilities cannot be empty")
        for candidate, utility in values.items():
            if not isinstance(candidate, str) or not candidate.strip():
                raise ValueError("candidate IDs must be non-empty strings")
            if isinstance(utility, bool) or not isinstance(utility, (int, float)):
                raise ValueError("utilities must be numeric")
            if not math.isfinite(float(utility)):
                raise ValueError("utilities must be finite")
        object.__setattr__(self, "probability", probability)
        object.__setattr__(self, "utilities", {
            key: float(value) for key, value in values.items()
        })


@dataclass(frozen=True)
class CandidateRobustness:
    candidate_id: str
    expected_utility: float
    worst_case_utility: float
    utility_variance: float
    maximum_regret: float


def evaluate_robustness(scenarios: tuple[Scenario, ...]) -> tuple[CandidateRobustness, ...]:
    scenarios = tuple(scenarios)
    if not scenarios or any(not isinstance(s, Scenario) for s in scenarios):
        raise ValueError("at least one valid Scenario is required")
    if len({s.scenario_id for s in scenarios}) != len(scenarios):
        raise ValueError("scenario_id values must be unique")
    candidate_ids = set(scenarios[0].utilities)
    if any(set(s.utilities) != candidate_ids for s in scenarios):
        raise ValueError("every scenario must score the same candidate set")
    probability_total = sum(s.probability for s in scenarios)
    if probability_total <= 0 or not math.isfinite(probability_total):
        raise ValueError("scenario probabilities must have a positive finite sum")

    normalized = [s.probability / probability_total for s in scenarios]
    best_by_scenario = [
        max(s.utilities.values()) for s in scenarios
    ]
    results = []
    for candidate in sorted(candidate_ids):
        values = [s.utilities[candidate] for s in scenarios]
        expected = sum(p * value for p, value in zip(normalized, values))
        variance = sum(
            p * (value - expected) ** 2
            for p, value in zip(normalized, values)
        )
        regret = max(
            best - value for best, value in zip(best_by_scenario, values)
        )
        results.append(CandidateRobustness(
            candidate_id=candidate,
            expected_utility=expected,
            worst_case_utility=min(values),
            utility_variance=variance,
            maximum_regret=regret,
        ))
    return tuple(results)
