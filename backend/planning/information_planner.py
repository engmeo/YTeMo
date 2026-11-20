"""Convert declared information gaps into non-executing plan-step proposals."""
from __future__ import annotations
import re
from .information import InformationGap
from .models import PlanStep, StepRisk


def build_information_steps(gaps: tuple[InformationGap, ...], *, prefix: str = "information") -> tuple[PlanStep, ...]:
    if not isinstance(prefix, str) or not prefix.strip():
        raise ValueError("prefix must be non-empty")
    steps = []
    seen = set()
    for index, gap in enumerate(gaps, start=1):
        if gap.gap_id in seen:
            raise ValueError(f"Duplicate information gap id: {gap.gap_id}")
        seen.add(gap.gap_id)
        safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", gap.gap_id).strip("-") or str(index)
        steps.append(PlanStep(
            step_id=f"{prefix}-{safe_id}",
            action="collect_information",
            description=f"Resolve information gap: {gap.question}",
            risk=StepRisk.LOW,
            metadata={"information_gap_id": gap.gap_id, "information_source": gap.source,
                      "priority": gap.priority, "proposal_only": True,
                      "requires_authorized_collection": True},
        ))
    return tuple(steps)
