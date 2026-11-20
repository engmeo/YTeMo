"""Generic extension contracts for domain-specific planning policies."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from .models import StepRisk

@dataclass(frozen=True)
class DomainPolicy:
    """Declarative domain rules consumed by the domain-neutral core."""
    domain_id: str
    required_evidence_risks: frozenset[StepRisk] = frozenset()
    required_human_approval_risks: frozenset[StepRisk] = frozenset()

    def __post_init__(self):
        if not isinstance(self.domain_id, str) or not self.domain_id.strip():
            raise ValueError("DomainPolicy.domain_id must be non-empty.")
        object.__setattr__(self, "required_evidence_risks", frozenset(StepRisk(x) for x in self.required_evidence_risks))
        object.__setattr__(self, "required_human_approval_risks", frozenset(StepRisk(x) for x in self.required_human_approval_risks))

@runtime_checkable
class PlanningDomainAdapter(Protocol):
    def get_policy(self) -> DomainPolicy:
        """Return this adapter's declarative domain policy."""
        ...
