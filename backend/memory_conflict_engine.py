"""Conflict detection and evidence tracking for Y TE MO.

Framework-neutral module. It does not decide clinical truth, call an LLM,
or write to Supabase. It preserves competing claims and their provenance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Optional
import hashlib
import json
import re


def _utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _norm(value: Any) -> str:
    if isinstance(value, str):
        value = re.sub(r"\s+", " ", value.strip().casefold())
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


class ClaimStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    DISPUTED = "DISPUTED"
    RETRACTED = "RETRACTED"


class ConflictKind(str, Enum):
    VALUE_MISMATCH = "VALUE_MISMATCH"
    TEMPORAL_OVERLAP = "TEMPORAL_OVERLAP"


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source_type: str
    source_ref: Optional[str] = None
    source_label: Optional[str] = None
    observed_at: Optional[datetime] = None
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    excerpt_hash: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_source(cls, source_type: str, source_ref: Optional[str] = None,
                    source_label: Optional[str] = None,
                    observed_at: Optional[datetime] = None,
                    excerpt: Optional[str] = None,
                    metadata: Optional[dict[str, Any]] = None) -> "Evidence":
        raw = "|".join([source_type, source_ref or "", source_label or "", excerpt or ""])
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return cls(
            evidence_id=digest[:24], source_type=source_type,
            source_ref=source_ref, source_label=source_label,
            observed_at=_utc(observed_at),
            excerpt_hash=hashlib.sha256(excerpt.encode("utf-8")).hexdigest() if excerpt else None,
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class MemoryClaim:
    memory_id: str
    owner_id: str
    subject_key: str
    predicate: str
    value: Any
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    status: ClaimStatus = ClaimStatus.ACTIVE
    verification_state: str = "UNVERIFIED"
    source_agent: Optional[str] = None
    evidence_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.memory_id or not self.owner_id or not self.subject_key or not self.predicate:
            raise ValueError("memory_id, owner_id, subject_key va predicate la bat buoc")
        start, end = _utc(self.valid_from), _utc(self.valid_until)
        if start and end and end <= start:
            raise ValueError("valid_until phai sau valid_from")
        object.__setattr__(self, "valid_from", start)
        object.__setattr__(self, "valid_until", end)


@dataclass(frozen=True)
class MemoryConflict:
    conflict_id: str
    owner_id: str
    claim_ids: tuple[str, ...]
    subject_key: str
    predicate: str
    kind: ConflictKind
    explanation: str
    requires_human_review: bool = True
    status: str = "OPEN"


class EvidenceStore:
    """Small in-memory evidence registry; replaceable by a DB adapter."""
    def __init__(self):
        self._items: dict[str, Evidence] = {}

    def add(self, evidence: Evidence) -> Evidence:
        existing = self._items.get(evidence.evidence_id)
        if existing and existing != evidence:
            raise ValueError("Evidence ID collision")
        self._items[evidence.evidence_id] = evidence
        return evidence

    def get(self, evidence_id: str) -> Optional[Evidence]:
        return self._items.get(evidence_id)

    def for_claim(self, claim: MemoryClaim) -> list[Evidence]:
        return [self._items[x] for x in claim.evidence_ids if x in self._items]


class ConflictDetector:
    """Deterministic conflict candidate detector; never selects the truth."""
    def detect(self, claims: Iterable[MemoryClaim]) -> list[MemoryConflict]:
        rows = [c for c in claims if c.status in (ClaimStatus.ACTIVE, ClaimStatus.DISPUTED)]
        groups: dict[tuple[str, str, str], list[MemoryClaim]] = {}
        for c in rows:
            groups.setdefault((c.owner_id, c.subject_key, c.predicate), []).append(c)

        conflicts: list[MemoryConflict] = []
        for (owner, subject, predicate), group in groups.items():
            for i, left in enumerate(group):
                for right in group[i + 1:]:
                    if _norm(left.value) == _norm(right.value):
                        continue
                    if not self._overlap(left, right):
                        continue
                    ids = tuple(sorted((left.memory_id, right.memory_id)))
                    raw = "|".join([owner, subject, predicate, *ids])
                    cid = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
                    conflicts.append(MemoryConflict(
                        conflict_id=cid, owner_id=owner, claim_ids=ids,
                        subject_key=subject, predicate=predicate,
                        kind=ConflictKind.VALUE_MISMATCH,
                        explanation="Different values for the same subject and predicate have overlapping validity periods.",
                    ))
        # Stable output and no duplicate conflict records.
        unique = {c.conflict_id: c for c in conflicts}
        return sorted(unique.values(), key=lambda x: x.conflict_id)

    @staticmethod
    def _overlap(a: MemoryClaim, b: MemoryClaim) -> bool:
        # Missing bounds mean unknown/open-ended, not proof of non-overlap.
        a_start = a.valid_from or datetime.min.replace(tzinfo=timezone.utc)
        b_start = b.valid_from or datetime.min.replace(tzinfo=timezone.utc)
        a_end = a.valid_until or datetime.max.replace(tzinfo=timezone.utc)
        b_end = b.valid_until or datetime.max.replace(tzinfo=timezone.utc)
        return max(a_start, b_start) < min(a_end, b_end)


class MemoryConflictEngine:
    def __init__(self, evidence_store: Optional[EvidenceStore] = None):
        self.evidence = evidence_store or EvidenceStore()
        self.detector = ConflictDetector()

    def attach_evidence(self, evidence: Evidence) -> Evidence:
        return self.evidence.add(evidence)

    def detect_conflicts(self, claims: Iterable[MemoryClaim]) -> list[MemoryConflict]:
        return self.detector.detect(claims)

    def explain_claim(self, claim: MemoryClaim) -> dict[str, Any]:
        return {
            "memory_id": claim.memory_id,
            "owner_id": claim.owner_id,
            "subject_key": claim.subject_key,
            "predicate": claim.predicate,
            "value": claim.value,
            "verification_state": claim.verification_state,
            "evidence": [
                {
                    "evidence_id": e.evidence_id,
                    "source_type": e.source_type,
                    "source_ref": e.source_ref,
                    "source_label": e.source_label,
                    "observed_at": e.observed_at.isoformat() if e.observed_at else None,
                    "excerpt_hash": e.excerpt_hash,
                }
                for e in self.evidence.for_claim(claim)
            ],
        }
