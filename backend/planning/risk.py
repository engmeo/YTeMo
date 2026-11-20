"""Domain-neutral risk scoring and policy checks."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable


def _unit_interval(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be between 0 and 1")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return number


@dataclass(frozen=True)
class RiskItem:
    risk_id: str
    probability: float
    impact: float
    description: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.risk_id, str) or not self.risk_id.strip():
            raise ValueError("risk_id must be a non-empty string")
        object.__setattr__(self, "probability",
                           _unit_interval(self.probability, "probability"))
        object.__setattr__(self, "impact", _unit_interval(self.impact, "impact"))
        if not isinstance(self.description, str):
            raise ValueError("description must be a string")

    @property
    def expected_loss(self) -> float:
        return self.probability * self.impact


@dataclass(frozen=True)
class RiskAssessment:
    items: tuple[RiskItem, ...]
    total_expected_loss: float
    highest_single_risk: float
    within_threshold: bool


def assess_risks(
    items: Iterable[RiskItem], max_expected_loss: float = 1.0
) -> RiskAssessment:
    risks = tuple(items)
    if any(not isinstance(item, RiskItem) for item in risks):
        raise ValueError("items must contain RiskItem values")
    if len({item.risk_id for item in risks}) != len(risks):
        raise ValueError("risk_id values must be unique")
    threshold = _unit_interval(max_expected_loss, "max_expected_loss")
    # Sum is intentionally not clipped: multiple risks can exceed 1.
    total = sum(item.expected_loss for item in risks)
    highest = max((item.expected_loss for item in risks), default=0.0)
    return RiskAssessment(
        items=risks,
        total_expected_loss=total,
        highest_single_risk=highest,
        within_threshold=total <= threshold,
    )
