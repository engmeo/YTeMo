"""Permissioned action runtime for Y TE MO Companion.

LLMs may propose actions, but cannot execute them directly. Every action is
validated against this allowlist and user-owned records. Sensitive actions
require explicit user approval before a worker may execute them.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

ALLOWED_ACTIONS = {
    "create_reminder": {
        "description": "Create a user-approved follow-up reminder.",
        "required": {"title", "due_at"},
        "approval_required": True,
    },
    "request_clinician_review": {
        "description": "Create a request for qualified human review.",
        "required": {"reason"},
        "approval_required": True,
    },
    "add_timeline_note": {
        "description": "Add a source-attributed note to the patient's timeline.",
        "required": {"note", "source"},
        "approval_required": True,
    },
}

class ActionValidationError(ValueError):
    pass

def _stable_key(user_id: str, action: str, arguments: dict[str, Any]) -> str:
    raw = json.dumps(
        {"user_id": user_id, "action": action, "arguments": arguments},
        ensure_ascii=False, sort_keys=True, default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def propose_action(db, user_id: str, action: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Persist a proposal; never execute it."""
    if action not in ALLOWED_ACTIONS:
        raise ActionValidationError("Action is not in the allowlist.")
    if not isinstance(arguments, dict):
        raise ActionValidationError("Action arguments must be an object.")
    spec = ALLOWED_ACTIONS[action]
    missing = spec["required"] - set(arguments)
    if missing:
        raise ActionValidationError("Missing required action arguments: " + ", ".join(sorted(missing)))
    if len(json.dumps(arguments, ensure_ascii=False, default=str)) > 4000:
        raise ActionValidationError("Action arguments are too large.")
    if action == "create_reminder":
        title = str(arguments.get("title", "")).strip()
        if not title or len(title) > 180:
            raise ActionValidationError("Reminder title must contain 1–180 characters.")
        due_at = str(arguments.get("due_at", "")).strip()
        try:
            parsed = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ActionValidationError("due_at must be an ISO-8601 timestamp.") from exc
        if parsed.tzinfo is None:
            raise ActionValidationError("due_at must include a timezone.")
    idem = _stable_key(user_id, action, arguments)
    existing = (
        db.table("companion_action_tasks").select("*")
        .eq("user_id", user_id).eq("idempotency_key", idem).limit(1).execute()
    )
    if existing.data:
        return existing.data[0]
    row = {
        "user_id": user_id,
        "action_type": action,
        "arguments": arguments,
        "status": "awaiting_approval" if spec["approval_required"] else "queued",
        "requires_approval": spec["approval_required"],
        "idempotency_key": idem,
        "scheduled_at": arguments.get("due_at") if action == "create_reminder" else datetime.now(timezone.utc).isoformat(),
    }
    result = db.table("companion_action_tasks").insert(row).execute()
    if not result.data:
        raise RuntimeError("Could not persist Agent action proposal.")
    return result.data[0]

def approve_action(db, user_id: str, action_id: str) -> dict[str, Any]:
    """Record explicit owner approval. Execution is performed by a worker."""
    current = (
        db.table("companion_action_tasks").select("*")
        .eq("id", action_id).eq("user_id", user_id).limit(1).execute()
    )
    if not current.data:
        raise LookupError("Action proposal not found.")
    row = current.data[0]
    if row.get("status") != "awaiting_approval":
        raise ActionValidationError("Only pending proposals can be approved.")
    updated = (
        db.table("companion_action_tasks")
        .update({"status": "queued", "approved_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", action_id).eq("user_id", user_id)
        .eq("status", "awaiting_approval").select("*").execute()
    )
    if not updated.data:
        raise RuntimeError("Action approval was not persisted.")
    return updated.data[0]

def reject_action(db, user_id: str, action_id: str) -> dict[str, Any]:
    updated = (
        db.table("companion_action_tasks")
        .update({"status": "rejected", "completed_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", action_id).eq("user_id", user_id)
        .eq("status", "awaiting_approval").execute()
    )
    if not updated.data:
        raise LookupError("Pending action proposal not found.")
    return updated.data[0]

def list_actions(db, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    result = (
        db.table("companion_action_tasks").select("*")
        .eq("user_id", user_id).order("created_at", desc=True)
        .limit(max(1, min(int(limit), 100))).execute()
    )
    return result.data or []
