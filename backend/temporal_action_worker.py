"""Durable worker for approved, due Companion actions.

Claims use database leases. Only explicitly approved actions are executed;
transient provider errors are retried with bounded exponential backoff.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Any

ActionHandler = Callable[[str, dict[str, Any]], dict[str, Any]]
_HANDLERS: dict[str, ActionHandler] = {}


class RetryableActionError(RuntimeError):
    """A transient provider/network failure that may be retried safely."""


def register_handler(action_type: str, handler: ActionHandler) -> None:
    if action_type in _HANDLERS:
        raise ValueError(f"Handler already registered: {action_type}")
    _HANDLERS[action_type] = handler


def _update_claimed_task(db, task: dict, patch: dict) -> bool:
    query = (
        db.table("companion_action_tasks").update(patch)
        .eq("id", task["id"]).eq("status", "running")
    )
    lease = task.get("lease_expires_at")
    if lease:
        query = query.eq("lease_expires_at", lease)
    result = query.select("id").execute()
    return bool(result.data)


def run_once(db, limit: int = 10) -> dict[str, int]:
    """Atomically claim and process one batch of approved, due tasks."""
    now = datetime.now(timezone.utc)
    claimed = db.rpc("claim_companion_action_tasks", {
        "p_now": now.isoformat(),
        "p_limit": max(1, min(int(limit), 50)),
        "p_action_types": sorted(_HANDLERS.keys()),
    }).execute().data or []
    completed = failed = retried = skipped = 0

    for task in claimed:
        action_type = task.get("action_type")
        handler = _HANDLERS.get(action_type)
        if not handler:
            changed = _update_claimed_task(db, task, {
                "status": "failed",
                "last_error": "No worker registered for action type.",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "lease_expires_at": None,
            })
            failed += int(changed)
            skipped += int(not changed)
            continue

        arguments = dict(task.get("arguments") or {})
        # A stable business-event ID lets providers deduplicate retries even if
        # a worker crashes after sending but before persisting task completion.
        arguments["_action_task_id"] = str(task["id"])
        try:
            result = handler(str(task["user_id"]), arguments)
            changed = _update_claimed_task(db, task, {
                "status": "completed",
                "result": result,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "last_error": None,
                "lease_expires_at": None,
                "next_attempt_at": None,
            })
            completed += int(changed)
            skipped += int(not changed)  # lease was reclaimed; newer worker owns it
        except RetryableActionError as exc:
            attempts = int(task.get("attempt_count") or 1)
            max_attempts = int(task.get("max_attempts") or 5)
            if attempts < max_attempts:
                delay = min(3600, 15 * (2 ** max(0, attempts - 1)))
                patch = {
                    "status": "queued",
                    "next_attempt_at": (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat(),
                    "lease_expires_at": None,
                    "last_error": type(exc).__name__,
                }
                changed = _update_claimed_task(db, task, patch)
                retried += int(changed)
                skipped += int(not changed)
            else:
                changed = _update_claimed_task(db, task, {
                    "status": "failed",
                    "last_error": type(exc).__name__,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "lease_expires_at": None,
                })
                failed += int(changed)
                skipped += int(not changed)
        except Exception as exc:
            # Unknown errors fail closed; do not retry arbitrary side effects.
            changed = _update_claimed_task(db, task, {
                "status": "failed",
                "last_error": type(exc).__name__,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "lease_expires_at": None,
            })
            failed += int(changed)
            skipped += int(not changed)

    return {
        "claimed": len(claimed), "completed": completed,
        "retried": retried, "failed": failed, "skipped": skipped,
    }


def serve(db, poll_seconds: float | None = None) -> None:
    interval = poll_seconds or float(os.getenv("YTEMO_ACTION_POLL_SECONDS", "5"))
    interval = max(1.0, min(interval, 60.0))
    while True:
        try:
            stats = run_once(db)
            if stats["claimed"] or stats["failed"]:
                print("COMPANION ACTION WORKER:", stats, flush=True)
        except Exception as exc:
            # Keep the process alive through transient Supabase/network failures.
            print("COMPANION ACTION WORKER ERROR:", type(exc).__name__, flush=True)
        time.sleep(interval)
