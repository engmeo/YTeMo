"""Derivation lineage, consolidation candidates and hybrid retrieval primitives.

Deterministic reference implementation. No LLM-generated facts, clinical
adjudication, database writes, or cross-user retrieval.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
import hashlib
import re


def _tokens(value: Any) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", str(value).casefold()))


@dataclass(frozen=True)
class DerivedMemory:
    memory_id: str
    owner_id: str
    content: str
    source_memory_ids: tuple[str, ...]
    derivation_method: str
    created_by: str
    verification_state: str = "UNVERIFIED"

    def __post_init__(self):
        if not self.memory_id or not self.owner_id or not self.content.strip():
            raise ValueError("memory_id, owner_id va content la bat buoc")
        if not self.source_memory_ids:
            raise ValueError("Derived memory phai co it nhat mot nguon")
        if not self.derivation_method or not self.created_by:
            raise ValueError("derivation_method va created_by la bat buoc")


class DerivationGraph:
    """Tracks source -> derived edges and prevents cycles / owner leakage."""
    def __init__(self):
        self._owners: dict[str, str] = {}
        self._edges: dict[str, set[str]] = {}
        self._derived: dict[str, DerivedMemory] = {}

    def register_source(self, memory_id: str, owner_id: str) -> None:
        if not memory_id or not owner_id:
            raise ValueError("memory_id va owner_id la bat buoc")
        existing = self._owners.get(memory_id)
        if existing and existing != owner_id:
            raise PermissionError("Memory ID da duoc dang ky cho owner khac")
        self._owners[memory_id] = owner_id
        self._edges.setdefault(memory_id, set())

    def add_derivation(self, item: DerivedMemory) -> None:
        if item.memory_id in self._owners:
            raise ValueError("Derived memory ID da ton tai")
        for source_id in item.source_memory_ids:
            if self._owners.get(source_id) != item.owner_id:
                raise PermissionError("Nguon khong ton tai hoac khac owner")
        self._owners[item.memory_id] = item.owner_id
        self._edges.setdefault(item.memory_id, set())
        for source_id in item.source_memory_ids:
            self._edges.setdefault(source_id, set()).add(item.memory_id)
        self._derived[item.memory_id] = item

    def lineage(self, memory_id: str, owner_id: str) -> list[str]:
        if self._owners.get(memory_id) != owner_id:
            return []
        visited: set[str] = set()
        ordered: list[str] = []

        def walk(node: str):
            for parent in sorted(self._parents(node)):
                if parent not in visited:
                    visited.add(parent)
                    walk(parent)
                    ordered.append(parent)

        walk(memory_id)
        return ordered

    def _parents(self, target: str) -> set[str]:
        return {src for src, children in self._edges.items() if target in children}

    def get_derived(self, memory_id: str, owner_id: str) -> Optional[DerivedMemory]:
        item = self._derived.get(memory_id)
        return item if item and item.owner_id == owner_id else None


@dataclass(frozen=True)
class ConsolidationCandidate:
    owner_id: str
    memory_ids: tuple[str, ...]
    reason: str
    suggested_action: str = "REVIEW_FOR_MERGE"
    requires_review: bool = True


class MemoryConsolidator:
    """Finds deterministic candidates; never merges or deletes automatically."""
    def find_duplicates(self, records: Iterable[dict[str, Any]]) -> list[ConsolidationCandidate]:
        groups: dict[tuple[str, str], list[str]] = {}
        for row in records:
            owner = row.get("owner_id")
            content = " ".join(str(row.get("content", "")).casefold().split())
            memory_id = row.get("memory_id")
            if not owner or not memory_id or not content:
                continue
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            groups.setdefault((owner, digest), []).append(memory_id)
        result = []
        for (owner, _), ids in groups.items():
            if len(ids) > 1:
                result.append(ConsolidationCandidate(
                    owner_id=owner, memory_ids=tuple(sorted(set(ids))),
                    reason="Exact normalized content duplicate within one owner scope.",
                ))
        return sorted(result, key=lambda x: (x.owner_id, x.memory_ids))

    def find_expired(self, records: Iterable[dict[str, Any]],
                     now: Optional[datetime] = None) -> list[ConsolidationCandidate]:
        point = now or datetime.now(timezone.utc)
        result = []
        for row in records:
            expiry = row.get("expires_at")
            if not row.get("owner_id") or not row.get("memory_id") or not expiry:
                continue
            if isinstance(expiry, str):
                expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry <= point:
                result.append(ConsolidationCandidate(
                    owner_id=row["owner_id"], memory_ids=(row["memory_id"],),
                    reason="Memory expiry time has passed.",
                    suggested_action="REVIEW_FOR_ARCHIVE",
                ))
        return result


@dataclass(frozen=True)
class RetrievalDocument:
    memory_id: str
    owner_id: str
    content: str
    memory_type: str = "SEMANTIC"
    status: str = "ACTIVE"
    verification_state: str = "UNVERIFIED"
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    source_ref: Optional[str] = None


@dataclass(frozen=True)
class RetrievalHit:
    document: RetrievalDocument
    score: float
    matched_terms: tuple[str, ...]


class HybridMemoryRetriever:
    """Owner-scoped lexical + structured + recency retrieval baseline.

    Vector similarity is intentionally an injectable future layer; this class
    does not pretend lexical scoring is semantic embedding retrieval.
    """
    def search(self, documents: Iterable[RetrievalDocument], query: str,
               owner_id: str, limit: int = 10,
               memory_types: Optional[set[str]] = None,
               as_of: Optional[datetime] = None) -> list[RetrievalHit]:
        if not owner_id:
            raise ValueError("owner_id la bat buoc")
        if limit < 1:
            raise ValueError("limit phai >= 1")
        terms = _tokens(query)
        if not terms:
            return []
        point = as_of or datetime.now(timezone.utc)
        if point.tzinfo is None:
            point = point.replace(tzinfo=timezone.utc)
        hits = []
        for doc in documents:
            if doc.owner_id != owner_id or doc.status != "ACTIVE":
                continue
            if memory_types and doc.memory_type not in memory_types:
                continue
            start = doc.valid_from
            end = doc.valid_until
            if start and start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end and end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if start and point < start:
                continue
            if end and point >= end:
                continue
            matched = terms & _tokens(doc.content)
            if not matched:
                continue
            score = len(matched) / max(len(terms), 1)
            if doc.verification_state in ("REVIEWED", "VERIFIED"):
                score += 0.10
            if doc.recorded_at.tzinfo is None:
                recorded = doc.recorded_at.replace(tzinfo=timezone.utc)
            else:
                recorded = doc.recorded_at
            age_days = max((point - recorded).total_seconds() / 86400, 0)
            score += 0.05 / (1 + age_days / 30)
            hits.append(RetrievalHit(doc, round(score, 6), tuple(sorted(matched))))
        return sorted(hits, key=lambda h: (-h.score, h.document.memory_id))[:limit]
