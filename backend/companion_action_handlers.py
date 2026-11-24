"""Idempotent persistence handlers for approved Companion actions."""
from __future__ import annotations

from datetime import datetime, timezone


def _persist_once(db, table_name: str, payload: dict) -> dict:
    task_id = payload.get("action_task_id")
    if not task_id:
        raise ValueError("A persisted action task ID is required.")
    try:
        result = db.table(table_name).insert(payload).select("*").execute()
        if result.data:
            return result.data[0]
    except Exception:
        # Unique action_task_id makes a retry return the original effect.
        existing = (
            db.table(table_name).select("*")
            .eq("action_task_id", task_id).limit(1).execute()
        )
        if existing.data:
            return existing.data[0]
        raise
    existing = (
        db.table(table_name).select("*")
        .eq("action_task_id", task_id).limit(1).execute()
    )
    if existing.data:
        return existing.data[0]
    raise RuntimeError("Action effect was not persisted.")


def make_clinician_review_handler(db):
    def request_review(user_id: str, arguments: dict) -> dict:
        reason = str(arguments.get("reason", "")).strip()
        if not reason or len(reason) > 1500:
            raise ValueError("Review reason must contain 1–1500 characters.")
        row = _persist_once(db, "companion_needs", {
            "action_task_id": arguments.get("_action_task_id"),
            "user_id": user_id,
            "title": "Yêu cầu chuyên gia lâm sàng xem xét",
            "description": reason,
            "status": "OPEN",
            "priority": "HIGH",
            "next_step": "Nhân viên y tế có thẩm quyền cần tiếp nhận và phản hồi.",
            "metadata": {
                "source": "companion_action",
                "action_task_id": arguments.get("_action_task_id"),
                "human_review_required": True,
            },
        })
        return {"stored": True, "destination": "companion_needs", "id": row["id"], "human_review_required": True}
    return request_review


def make_timeline_note_handler(db):
    def add_note(user_id: str, arguments: dict) -> dict:
        note = str(arguments.get("note", "")).strip()
        source = str(arguments.get("source", "")).strip()
        if not note or len(note) > 4000:
            raise ValueError("Timeline note must contain 1–4000 characters.")
        if not source or len(source) > 500:
            raise ValueError("Timeline note source must contain 1–500 characters.")
        task_id = arguments.get("_action_task_id")
        row = _persist_once(db, "companion_events", {
            "action_task_id": task_id,
            "user_id": user_id,
            "event_type": "TIMELINE_NOTE_ADDED",
            "payload": {"note": note, "source": source, "action_task_id": task_id},
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"stored": True, "destination": "companion_events", "id": row["id"]}
    return add_note
