"""Temporal and versioned memory primitives for Y TE MO.

Immutable version snapshots and bitemporal queries. No clinical truth selection,
LLM calls, database writes, or consent bypasses are performed here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
import copy
import hashlib
import json


def as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TemporalMemory:
    memory_id: str
    owner_id: str
    subject_key: str
    predicate: str
    value: Any
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "ACTIVE"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not all([self.memory_id, self.owner_id, self.subject_key, self.predicate]):
            raise ValueError("memory_id, owner_id, subject_key va predicate la bat buoc")
        start, end = as_utc(self.valid_from), as_utc(self.valid_until)
        recorded = as_utc(self.recorded_at)
        if start and end and end <= start:
            raise ValueError("valid_until phai sau valid_from")
        if recorded is None:
            raise ValueError("recorded_at khong duoc rong")
        object.__setattr__(self, "valid_from", start)
        object.__setattr__(self, "valid_until", end)
        object.__setattr__(self, "recorded_at", recorded)
        object.__setattr__(self, "value", copy.deepcopy(self.value))
        object.__setattr__(self, "metadata", copy.deepcopy(self.metadata))


@dataclass(frozen=True)
class MemoryVersion:
    version_id: str
    memory_id: str
    version_number: int
    payload_hash: str
    snapshot: dict[str, Any]
    recorded_at: datetime
    actor_id: str
    change_reason: str


class VersionConflictError(ValueError):
    pass


class VersionedMemoryStore:
    """In-memory reference implementation; versions are append-only."""
    def __init__(self):
        self._current: dict[str, TemporalMemory] = {}
        self._versions: dict[str, list[MemoryVersion]] = {}

    @staticmethod
    def _snapshot(memory: TemporalMemory) -> dict[str, Any]:
        return {
            "memory_id": memory.memory_id,
            "owner_id": memory.owner_id,
            "subject_key": memory.subject_key,
            "predicate": memory.predicate,
            "value": copy.deepcopy(memory.value),
            "valid_from": memory.valid_from.isoformat() if memory.valid_from else None,
            "valid_until": memory.valid_until.isoformat() if memory.valid_until else None,
            "recorded_at": memory.recorded_at.isoformat(),
            "status": memory.status,
            "metadata": copy.deepcopy(memory.metadata),
        }

    def create(self, memory: TemporalMemory, actor_id: str, reason: str) -> MemoryVersion:
        if memory.memory_id in self._current:
            raise VersionConflictError("Memory da ton tai; hay dung revise()")
        self._current[memory.memory_id] = memory
        return self._append(memory, actor_id, reason)

    def revise(self, memory: TemporalMemory, actor_id: str, reason: str,
               expected_version: Optional[int] = None) -> MemoryVersion:
        old = self._current.get(memory.memory_id)
        if old is None:
            raise KeyError(memory.memory_id)
        versions = self._versions[memory.memory_id]
        current_number = versions[-1].version_number
        if expected_version is not None and expected_version != current_number:
            raise VersionConflictError(
                f"Version stale: expected {expected_version}, current {current_number}"
            )
        if old.owner_id != memory.owner_id:
            raise PermissionError("Khong duoc doi owner cua memory")
        self._current[memory.memory_id] = memory
        return self._append(memory, actor_id, reason)

    def _append(self, memory: TemporalMemory, actor_id: str, reason: str) -> MemoryVersion:
        if not actor_id or not reason:
            raise ValueError("actor_id va change_reason la bat buoc")
        versions = self._versions.setdefault(memory.memory_id, [])
        snapshot = self._snapshot(memory)
        number = len(versions) + 1
        version = MemoryVersion(
            version_id=canonical_hash([memory.memory_id, number, snapshot]),
            memory_id=memory.memory_id,
            version_number=number,
            payload_hash=canonical_hash(snapshot),
            snapshot=snapshot,
            recorded_at=datetime.now(timezone.utc),
            actor_id=actor_id,
            change_reason=reason,
        )
        versions.append(version)
        return version

    def get_current(self, memory_id: str, owner_id: str) -> Optional[TemporalMemory]:
        item = self._current.get(memory_id)
        if item is None or item.owner_id != owner_id:
            return None
        return item

    def history(self, memory_id: str, owner_id: str) -> list[MemoryVersion]:
        item = self._current.get(memory_id)
        if item is None or item.owner_id != owner_id:
            return []
        return list(self._versions[memory_id])

    def restore_as_new_version(self, memory_id: str, owner_id: str,
                               version_number: int, actor_id: str,
                               reason: str) -> MemoryVersion:
        history = self.history(memory_id, owner_id)
        if not history:
            raise KeyError(memory_id)
        match = next((v for v in history if v.version_number == version_number), None)
        if match is None:
            raise KeyError(version_number)
        s = match.snapshot
        restored = TemporalMemory(
            memory_id=s["memory_id"], owner_id=s["owner_id"],
            subject_key=s["subject_key"], predicate=s["predicate"],
            value=s["value"],
            valid_from=datetime.fromisoformat(s["valid_from"]) if s["valid_from"] else None,
            valid_until=datetime.fromisoformat(s["valid_until"]) if s["valid_until"] else None,
            status=s["status"], metadata=s["metadata"],
        )
        return self.revise(restored, actor_id, reason)


class TemporalMemoryQuery:
    """Queries distinguish when a fact was valid from when the system knew it."""
    @staticmethod
    def valid_at(memories: Iterable[TemporalMemory], at: datetime,
                 owner_id: str) -> list[TemporalMemory]:
        point = as_utc(at)
        result = []
        for m in memories:
            if m.owner_id != owner_id or m.status != "ACTIVE":
                continue
            start = m.valid_from or datetime.min.replace(tzinfo=timezone.utc)
            end = m.valid_until or datetime.max.replace(tzinfo=timezone.utc)
            if start <= point < end:
                result.append(m)
        return sorted(result, key=lambda x: x.recorded_at, reverse=True)

    @staticmethod
    def known_at(versions: Iterable[MemoryVersion], at: datetime) -> list[MemoryVersion]:
        point = as_utc(at)
        return sorted(
            [v for v in versions if as_utc(v.recorded_at) <= point],
            key=lambda x: (x.memory_id, x.version_number),
        )
