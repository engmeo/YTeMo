"""Additive healthcare orchestration layer.

This module does not replace AgentCore, AgentRegistry, or existing specialist
implementations. Applications inject approved specialist callables explicitly.
It performs deterministic routing only; it does not make clinical decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class OrchestrationPlan:
    intent: str
    specialist_keys: tuple[str, ...]
    requires_human_review: bool
    reason: str


@dataclass
class OrchestrationResult:
    status: str
    plan: OrchestrationPlan
    specialist_results: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    safety_flags: list[str] = field(default_factory=list)
    next_action: str = "review"
    disclaimer: str = (
        "Thong tin ho tro tham khao; khong thay the chan doan, ke don "
        "hoac quyet dinh cua nhan vien y te."
    )


class HealthcareOrchestrator:
    """Small, deterministic coordinator around already-approved specialists."""

    ROUTES = {
        "cost": ("cost_intelligence",),
        "medication": ("medication_support",),
        "lab": ("lab_result",),
        "bhyt": ("bhyt_support",),
        "comprehensive": (
            "cost_intelligence", "medication_support", "lab_result", "bhyt_support"
        ),
    }

    HIGH_RISK_TERMS = (
         "cap cuu", "khong tho duoc", "dau nguc", "dot quy",
        "tu sat", "qua lieu", "sốc phản vệ", "suy ho hap",
        "chest pain", "shortness of breath", "stroke", "overdose",
    )

    def __init__(
        self,
        specialists: Mapping[str, Callable[[Mapping[str, Any]], Any]],
        *,
        allowed_specialists: Sequence[str] | None = None,
    ) -> None:
        self._specialists = dict(specialists)
        self._allowed = set(allowed_specialists or self.ROUTES["comprehensive"])
        unknown = self._allowed.difference(self._specialists)
        if unknown:
            raise ValueError("Allowed specialists are not registered: " + ", ".join(sorted(unknown)))

    @classmethod
    def plan(cls, request: Mapping[str, Any]) -> OrchestrationPlan:
        text = " ".join(
            str(request.get(k, "")) for k in ("intent", "question", "document_type", "task")
        ).lower()
        explicit = str(request.get("intent", "")).strip().lower()
        if any(term in text for term in cls.HIGH_RISK_TERMS):
            return OrchestrationPlan(
                "urgent_safety", (), True,
                "Phat hien dau hieu co the nguy cap; dung dieu phoi tu dong va chuyen nguoi that."
            )
        if explicit in cls.ROUTES:
            intent = explicit
        elif any(x in text for x in ("thuoc", "don thuoc", "lieu dung", "medication")):
            intent = "medication"
        elif any(x in text for x in ("xet nghiem", "chi so", "lab", "ket qua")):
            intent = "lab"
        elif any(x in text for x in ("bhyt", "bao hiem y te", "quyen loi")):
            intent = "bhyt"
        elif any(x in text for x in ("chi phi", "vien phi", "gia tien", "cost")):
            intent = "cost"
        else:
            intent = "comprehensive"
        return OrchestrationPlan(
            intent, cls.ROUTES[intent], False,
            "Chon specialist theo intent; khong tu suy dien chan doan."
        )

    def run(self, request: Mapping[str, Any]) -> OrchestrationResult:
        plan = self.plan(request)
        if plan.requires_human_review:
            return OrchestrationResult(
                "needs_human_review", plan,
                safety_flags=["possible_urgent_condition"],
                next_action="contact_local_emergency_services_or_qualified_clinician",
            )

        results: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for key in plan.specialist_keys:
            if key not in self._allowed or key not in self._specialists:
                errors[key] = "Specialist is not approved or not registered."
                continue
            try:
                # Only caller-provided, consent-filtered request context is passed through.
                output = self._specialists[key](dict(request))
                results[key] = output
            except Exception as exc:
                # Avoid returning exception text that may contain patient data or secrets.
                errors[key] = type(exc).__name__

        if errors:
            status, action = "partial_or_failed", "human_review_required"
        elif not results:
            status, action = "not_executed", "human_review_required"
        else:
            status, action = "completed_for_review", "review_evidence_and_human_approval"

        return OrchestrationResult(
            status, plan, results, errors,
            safety_flags=["clinical_decision_not_performed"],
            next_action=action,
        )