"""Consent-aware, framework-neutral memory engine for Y TE MO.

This module stores candidate memories by default. It does not call an LLM,
make clinical judgments, or promote unverified content automatically.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol


MEMORY_TYPES = {
    "WORKING", "EPISODIC", "SEMANTIC", "PROCEDURAL",
    "RELATIONAL", "SHARED_KNOWLEDGE",
}
OWNER_TYPES = {"USER", "AGENT", "TENANT", "SHARED"}
STATUSES = {"CANDIDATE", "ACTIVE", "SUPERSEDED", "REJECTED", "ARCHIVED"}
VERIFICATION_STATES = {"UNVERIFIED", "SUPPORTED", "REVIEWED", "VERIFIED", "DISPUTED"}
SENSITIVITY_LEVELS = {"NORMAL", "PERSONAL", "HEALTH", "HIGH"}
CONSENT_SCOPES = {"BASIC_PROFILE", "HEALTH_CONTEXT", "FOLLOW_UP"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


@dataclass
class MemoryRecord:
    id: str
    owner_type: str
    user_id: Optional[str]
    tenant_id: Optional[str]
    agent_key: Optional[str]
    memory_type: str
    content: Dict[str, Any]
    summary: str
    source_type: str
    source_ref: Optional[str] = None
    source_metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "CANDIDATE"
    verification_state: str = "UNVERIFIED"
    confidence: float = 0.5
    sensitivity: str = "NORMAL"
    consent_scope: Optional[str] = None
    access_policy: Dict[str, Any] = field(default_factory=dict)
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    observed_at: Optional[str] = None
    expires_at: Optional[str] = None
    dedupe_hash: Optional[str] = None
    created_by_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    recorded_at: str = field(default_factory=_now)


@dataclass
class MemoryWriteResult:
    record: MemoryRecord
    created: bool
    reason: str


@dataclass
class MemoryQuery:
    user_id: str
    agent_key: Optional[str] = None
    memory_types: Optional[List[str]] = None
    query: Optional[str] = None
    limit: int = 20
    include_agent_global: bool = False
    as_of: Optional[str] = None


class MemoryRepository(Protocol):
    def insert(self, row: Dict[str, Any]) -> Dict[str, Any]: ...
    def find_duplicate(self, *, user_id: Optional[str], agent_key: Optional[str],
                       memory_type: str, dedupe_hash: str) -> Optional[Dict[str, Any]]: ...
    def retrieve(self, *, user_id: str, agent_key: Optional[str],
                 memory_types: Optional[List[str]], as_of: str,
                 include_agent_global: bool, limit: int) -> List[Dict[str, Any]]: ...
    def update(self, memory_id: str, values: Dict[str, Any]) -> Dict[str, Any]: ...
    def audit(self, row: Dict[str, Any]) -> None: ...


class SupabaseMemoryRepository:
    """Small adapter over the Supabase Python client's table API.

    All user reads are scoped by user_id in SQL. Service-role clients bypass RLS,
    so this application-level scoping is mandatory and must not be removed.
    """
    def __init__(self, client: Any):
        self.client = client

    def insert(self, row: Dict[str, Any]) -> Dict[str, Any]:
        result = self.client.table("agent_memories").insert(row).execute()
        data = getattr(result, "data", None) or []
        if not data:
            raise RuntimeError("Supabase did not return the inserted memory")
        return data[0]

    def find_duplicate(self, *, user_id: Optional[str], agent_key: Optional[str],
                       memory_type: str, dedupe_hash: str) -> Optional[Dict[str, Any]]:
        q = (self.client.table("agent_memories").select("*")
             .eq("owner_type", "USER").eq("user_id", user_id)
             .eq("memory_type", memory_type).eq("dedupe_hash", dedupe_hash)
             .in_("status", ["CANDIDATE", "ACTIVE"]).is_("deleted_at", "null"))
        if agent_key is None:
            q = q.is_("agent_key", "null")
        else:
            q = q.eq("agent_key", agent_key)
        data = getattr(q.execute(), "data", None) or []
        return data[0] if data else None

    def retrieve(self, *, user_id: str, agent_key: Optional[str],
                 memory_types: Optional[List[str]], as_of: str,
                 include_agent_global: bool, limit: int) -> List[Dict[str, Any]]:
        q = (self.client.table("agent_memories").select("*")
             .eq("owner_type", "USER").eq("user_id", user_id)
             .eq("status", "ACTIVE").is_("deleted_at", "null")
             .lte("valid_from", as_of))
        # User-wide Companion memories and this Agent's private namespace.
        if agent_key:
            q = q.or_(f"agent_key.is.null,agent_key.eq.{agent_key}")
        else:
            q = q.is_("agent_key", "null")
        if memory_types:
            q = q.in_("memory_type", memory_types)
        data = getattr(q.order("recorded_at", desc=True).limit(limit).execute(),
                       "data", None) or []
        rows = []
        for row in data:
            until = row.get("valid_until")
            expiry = row.get("expires_at")
            if until and until < as_of:
                continue
            if expiry and expiry < as_of:
                continue
            rows.append(row)
        if include_agent_global and agent_key:
            g = (self.client.table("agent_memories").select("*")
                 .eq("owner_type", "AGENT").eq("agent_key", agent_key)
                 .eq("status", "ACTIVE").is_("deleted_at", "null"))
            if memory_types:
                g = g.in_("memory_type", memory_types)
            global_rows = getattr(g.order("recorded_at", desc=True).limit(limit).execute(),
                                  "data", None) or []
            rows.extend(global_rows)
        return rows[:limit]

    def update(self, memory_id: str, values: Dict[str, Any]) -> Dict[str, Any]:
        result = (self.client.table("agent_memories").update(values)
                  .eq("id", memory_id).execute())
        data = getattr(result, "data", None) or []
        if not data:
            raise LookupError("Memory not found or update not permitted")
        return data[0]

    def audit(self, row: Dict[str, Any]) -> None:
        self.client.table("agent_memory_audit").insert(row).execute()


class MemoryEngine:
    def __init__(self, repository: MemoryRepository,
                 consent_checker: Optional[Callable[[str, str], bool]] = None):
        self.repository = repository
        self.consent_checker = consent_checker or (lambda _user, _scope: False)

    def write(self, *, owner_type: str, memory_type: str,
              content: Dict[str, Any], summary: str, source_type: str,
              user_id: Optional[str] = None, tenant_id: Optional[str] = None,
              agent_key: Optional[str] = None, source_ref: Optional[str] = None,
              source_metadata: Optional[Dict[str, Any]] = None,
              confidence: float = 0.5, sensitivity: str = "NORMAL",
              consent_scope: Optional[str] = None,
              created_by_agent: Optional[str] = None,
              valid_from: Optional[str] = None, valid_until: Optional[str] = None,
              expires_at: Optional[str] = None,
              metadata: Optional[Dict[str, Any]] = None) -> MemoryWriteResult:
        owner_type = owner_type.upper()
        memory_type = memory_type.upper()
        sensitivity = sensitivity.upper()
        if owner_type not in OWNER_TYPES or memory_type not in MEMORY_TYPES:
            raise ValueError("Invalid owner_type or memory_type")
        if sensitivity not in SENSITIVITY_LEVELS:
            raise ValueError("Invalid sensitivity")
        if not isinstance(content, dict) or not content:
            raise ValueError("content must be a non-empty object")
        if not summary.strip() or not source_type.strip():
            raise ValueError("summary and source_type are required")
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if owner_type == "USER":
            if not user_id:
                raise ValueError("USER memory requires user_id")
            if sensitivity in {"PERSONAL", "HEALTH", "HIGH"}:
                if not consent_scope or consent_scope not in CONSENT_SCOPES:
                    raise PermissionError("A valid consent_scope is required")
                if not self.consent_checker(user_id, consent_scope):
                    raise PermissionError("Consent is missing or revoked")
        elif owner_type == "AGENT" and not agent_key:
            raise ValueError("AGENT memory requires agent_key")
        elif owner_type == "TENANT" and not tenant_id:
            raise ValueError("TENANT memory requires tenant_id")
        elif owner_type == "SHARED" and (user_id or tenant_id):
            raise ValueError("SHARED memory must not carry user_id or tenant_id")
        if owner_type == "USER" and memory_type == "SHARED_KNOWLEDGE":
            raise ValueError("SHARED_KNOWLEDGE must use a shared/tenant owner")

        digest_input = {
            "owner_type": owner_type, "user_id": user_id, "agent_key": agent_key,
            "memory_type": memory_type, "content": content,
        }
        digest = hashlib.sha256(_canonical(digest_input).encode("utf-8")).hexdigest()
        if owner_type == "USER":
            existing = self.repository.find_duplicate(
                user_id=user_id, agent_key=agent_key,
                memory_type=memory_type, dedupe_hash=digest)
            if existing:
                return MemoryWriteResult(self._from_row(existing), False, "duplicate")

        row = {
            "id": str(uuid.uuid4()), "owner_type": owner_type, "user_id": user_id,
            "tenant_id": tenant_id, "agent_key": agent_key, "memory_type": memory_type,
            "content": content, "summary": summary, "source_type": source_type,
            "source_ref": source_ref, "source_metadata": source_metadata or {},
            "status": "CANDIDATE", "verification_state": "UNVERIFIED",
            "confidence": confidence, "sensitivity": sensitivity,
            "consent_scope": consent_scope, "access_policy": {},
            "valid_from": valid_from or _now(), "valid_until": valid_until,
            "observed_at": _now(), "expires_at": expires_at, "dedupe_hash": digest,
            "created_by_agent": created_by_agent, "metadata": metadata or {},
        }
        saved = self.repository.insert(row)
        self.repository.audit({
            "memory_id": saved["id"], "action": "CREATED", "actor_type":
            "AGENT" if created_by_agent else "SYSTEM", "actor_id": created_by_agent,
            "new_state": {"status": "CANDIDATE", "verification_state": "UNVERIFIED"},
            "reason": "Memory captured as an unverified candidate",
        })
        return MemoryWriteResult(self._from_row(saved), True, "created_as_candidate")

    def retrieve(self, query: MemoryQuery) -> List[MemoryRecord]:
        if not query.user_id:
            raise ValueError("user_id is required for user-context retrieval")
        if query.memory_types:
            invalid = set(query.memory_types) - MEMORY_TYPES
            if invalid:
                raise ValueError(f"Invalid memory types: {sorted(invalid)}")
        now = query.as_of or _now()
        rows = self.repository.retrieve(
            user_id=query.user_id, agent_key=query.agent_key,
            memory_types=query.memory_types, as_of=now,
            include_agent_global=query.include_agent_global,
            limit=max(1, min(query.limit, 100)))
        if query.query:
            terms = [t.casefold() for t in query.query.split() if t.strip()]
            rows = [r for r in rows if all(
                t in (str(r.get("summary", "")) + " " + _canonical(r.get("content", {}))).casefold()
                for t in terms)]
        return [self._from_row(r) for r in rows]

    def review(self, memory_id: str, *, decision: str, actor_id: str,
               actor_type: str = "HUMAN", reason: str = "") -> MemoryRecord:
        decision = decision.upper()
        if decision not in {"APPROVE", "REJECT"}:
            raise ValueError("decision must be APPROVE or REJECT")
        if actor_type.upper() != "HUMAN" or not actor_id:
            raise PermissionError("Only an identified human reviewer may review memory")
        status = "ACTIVE" if decision == "APPROVE" else "REJECTED"
        verification = "REVIEWED" if decision == "APPROVE" else "DISPUTED"
        updated = self.repository.update(memory_id, {
            "status": status, "verification_state": verification,
            "reviewed_by": actor_id, "reviewed_at": _now(), "updated_at": _now(),
        })
        self.repository.audit({
            "memory_id": memory_id, "action": "ACTIVATED" if decision == "APPROVE" else "REJECTED",
            "actor_type": "HUMAN", "actor_id": actor_id,
            "new_state": {"status": status, "verification_state": verification},
            "reason": reason or "Human review",
        })
        return self._from_row(updated)

    def soft_delete(self, memory_id: str, *, actor_id: str,
                    actor_type: str = "HUMAN", reason: str = "") -> None:
        if not actor_id:
            raise PermissionError("actor_id is required")
        self.repository.update(memory_id, {
            "deleted_at": _now(), "status": "ARCHIVED", "updated_at": _now(),
        })
        self.repository.audit({
            "memory_id": memory_id, "action": "DELETED",
            "actor_type": actor_type.upper(), "actor_id": actor_id,
            "reason": reason or "Soft-deleted",
        })

    @staticmethod
    def _from_row(row: Dict[str, Any]) -> MemoryRecord:
        allowed = MemoryRecord.__dataclass_fields__.keys()
        return MemoryRecord(**{k: v for k, v in row.items() if k in allowed})
