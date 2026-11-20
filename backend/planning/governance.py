"""Domain-neutral approval and governance gates for proposed plans."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"


@dataclass(frozen=True)
class GovernanceRequest:
    plan_id: str
    risk_level: float
    required_approvals: int = 0
    approvals: int = 0
    consent_granted: bool = True
    evidence_satisfied: bool = True
    policy_allowed: bool = True

    def __post_init__(self) -> None:
        if not self.plan_id.strip():
            raise ValueError("plan_id must not be empty")
        if not 0.0 <= self.risk_level <= 1.0:
            raise ValueError("risk_level must be between 0 and 1")
        if self.required_approvals < 0 or self.approvals < 0:
            raise ValueError("approval counts must be non-negative")


@dataclass(frozen=True)
class GovernanceDecision:
    status: ApprovalStatus
    reasons: tuple[str, ...]
    executable: bool = False


def evaluate_governance(
    request: GovernanceRequest,
    *,
    mandatory_human_review_threshold: float = 0.75,
) -> GovernanceDecision:
    """Evaluate gates only; this function never executes a plan."""
    if not 0.0 <= mandatory_human_review_threshold <= 1.0:
        raise ValueError("mandatory_human_review_threshold must be between 0 and 1")

    reasons: list[str] = []
    if not request.policy_allowed:
        reasons.append("domain_policy_denied")
    if not request.consent_granted:
        reasons.append("consent_missing_or_revoked")
    if not request.evidence_satisfied:
        reasons.append("evidence_requirements_not_met")
    if request.risk_level >= mandatory_human_review_threshold:
        if request.approvals < max(1, request.required_approvals):
            reasons.append("human_review_required")
    elif request.approvals < request.required_approvals:
        reasons.append("required_approvals_missing")

    if "domain_policy_denied" in reasons or "consent_missing_or_revoked" in reasons:
        status = ApprovalStatus.REJECTED
    elif reasons:
        status = ApprovalStatus.PENDING
    else:
        status = ApprovalStatus.APPROVED
    # Approval is not execution authorization; runtime must enforce its own gates.
    return GovernanceDecision(status=status, reasons=tuple(reasons), executable=False)
