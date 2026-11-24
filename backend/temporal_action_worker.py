"""Polling worker for durable Companion tasks.

Only explicitly approved, due tasks are claimed. Unregistered action types fail
closed; this worker does not book care or modify clinical treatment.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Callable, Any

ActionHandler = Callable[[str, dict[str, Any]], dict[str, Any]]
_HANDLERS: dict[str, ActionHandler] = {}


def register_handler(action_type: str, handler: ActionHandler) -> None:
    if action_type in _HANDLERS:
        raise ValueError(f"Handler already registered: {action_type}")
    _HANDLERS[action_type] = handler


def run_once(db, limit: int = 10) -> dict[str, int]:
    """Atomically claim and process one batch of approved, due tasks."""
    now = datetime.now(timezone.utc).isoformat()
    claimed = db.rpc("claim_companion_action_tasks", {
        "p_now": now,
        "p_limit": max(1, min(int(limit), 50)),
    }).execute().data or []
    completed = failed = 0
    for task in claimed:
        action_type = task.get("action_type")
        handler = _HANDLERS.get(action_type)
        if not handler:
            db.table("companion_action_tasks").update({
                "status": "failed",
                "last_error": "No worker registered for action type.",
            }).eq("id", task["id"]).eq("status", "running").execute()
            failed += 1
            continue
        try:
            result = handler(str(task["user_id"]), task.get("arguments") or {})
            db.table("companion_action_tasks").update({
                "status": "completed",
                "result": result,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "last_error": None,
            }).eq("id", task["id"]).eq("status", "running").execute()
            completed += 1
        except Exception as exc:
            db.table("companion_action_tasks").update({
                "status": "failed",
                "last_error": type(exc).__name__,
            }).eq("id", task["id"]).eq("status", "running").execute()
            failed += 1
    return {"claimed": len(claimed), "completed": completed, "failed": failed, "skipped": 0}


def serve(db, poll_seconds: float | None = None) -> None:
    interval = poll_seconds or float(os.getenv("YTEMO_ACTION_POLL_SECONDS", "5"))
    interval = max(1.0, min(interval, 60.0))
    while True:
        try:
            stats = run_once(db)
            if stats["claimed"]:
                print("COMPANION ACTION WORKER:", stats, flush=True)
        except Exception as exc:
            # Keep the process alive through transient Supabase/network failures.
            print("COMPANION ACTION WORKER ERROR:", type(exc).__name__, flush=True)
        time.sleep(interval)
