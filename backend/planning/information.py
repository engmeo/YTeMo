"""Explicit information-gap detection over a belief and state snapshot."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from .models import BeliefState


@dataclass(frozen=True)
class InformationGap:
    gap_id: str
    question: str
    source: str
    priority: float = 1.0

    def __post_init__(self):
        for name in ("gap_id", "question", "source"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if isinstance(self.priority, bool) or not isinstance(self.priority, (int, float)) or not isfinite(self.priority) or self.priority < 0:
            raise ValueError("priority must be a finite non-negative number")


def detect_information_gaps(belief: BeliefState) -> tuple[InformationGap, ...]:
    """Return declared unknowns and unresolved questions, deduplicated in order."""
    found = []
    seen = set()
    for source, values in (("state_unknown", belief.snapshot.unknowns), ("unresolved_question", belief.unresolved_questions)):
        for value in values:
            normalized = value.strip().casefold()
            if normalized and normalized not in seen:
                seen.add(normalized)
                found.append(InformationGap(f"gap-{len(found) + 1}", value, source))
    return tuple(found)
