"""Supabase persistence adapters for Y TE MO Companion Core and Proactive Engine.

Queries are scoped by the authenticated user's UUID. The backend secret key
bypasses RLS, so this ownership filter is mandatory.

The companion adapter writes only records changed since the immediately
preceding get() in the same synchronous request/thread. It never performs a
whole-table reconciliation or deletes records merely because they were absent
from a potentially stale snapshot.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import local
from typing import Any

from companion_core import (
    CompanionState, ConsentRecord, ConsentScope, ContextItem,
    SupportNeed, NeedStatus, UserPriority, CompanionEvent,
)
from proactive_engine import ProactiveProposal, ProposalStatus


def _enum_db(value: str) -> str:
    return value.upper()


def _enum_app(value: str, enum_type):
    return enum_type(value.lower())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseCompanionRepository:
    """Persistence adapter implementing CompanionRepository's get/save contract."""

    def __init__(self, db):
        self.db = db
        self._local = local()

    def _snapshots(self) -> dict[str, CompanionState]:
        if not hasattr(self._local, "snapshots"):
            self._local.snapshots = {}
        return self._local.snapshots

    def get(self, user_id: str) -> CompanionState | None:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        uid = user_id.strip()
        consents = (self.db.table("companion_consents").select("*")
                    .eq("user_id", uid).execute()).data or []
        contexts = (self.db.table("companion_context").select("*")
                    .eq("user_id", uid).is_("deleted_at", "null")
                    .execute()).data or []
        needs = (self.db.table("companion_needs").select("*")
                 .eq("user_id", uid).execute()).data or []
        events = (self.db.table("companion_events").select("*")
                  .eq("user_id", uid).order("occurred_at")
                  .limit(500).execute()).data or []

        state = CompanionState(user_id=uid)
        for row in consents:
            scope = _enum_app(row["scope"], ConsentScope)
            state.consents[scope.value] = ConsentRecord(
                scope=scope, granted=bool(row["granted"]),
                updated_at=row.get("updated_at") or row.get("created_at") or "",
            )
        for row in contexts:
            content = row.get("content") or {}
            state.context_items.append(ContextItem(
                id=str(row["id"]), user_id=uid,
                scope=_enum_app(row["scope"], ConsentScope),
                category=str(row.get("context_type") or "note"),
                content=str(content.get("text", content)),
                source=row.get("source") or "user_provided",
                created_at=row.get("created_at") or "",
                expires_at=row.get("expires_at"),
            ))
        for row in needs:
            state.needs.append(SupportNeed(
                id=str(row["id"]), user_id=uid,
                title=row["title"], description=row.get("description") or "",
                status=_enum_app(row["status"], NeedStatus),
                user_priority=_enum_app(row["priority"], UserPriority),
                created_at=row.get("created_at") or "",
                updated_at=row.get("updated_at") or "",
                next_step=row.get("next_step"),
            ))
        for row in events:
            payload = row.get("payload") or {}
            state.events.append(CompanionEvent(
                id=str(row["id"]), user_id=uid,
                event_type=row["event_type"],
                summary=str(payload.get("summary", "")),
                created_at=row.get("occurred_at") or row.get("created_at") or "",
            ))
        timestamps = [r.get("updated_at") for r in consents + contexts + needs if r.get("updated_at")]
        if timestamps:
            state.updated_at = max(timestamps)
        self._snapshots()[uid] = deepcopy(state)
        return state if (consents or contexts or needs or events) else None

    def save(self, state: CompanionState) -> None:
        uid = state.user_id
        if not isinstance(uid, str) or not uid.strip():
            raise ValueError("state.user_id must be a non-empty string")
        uid = uid.strip()
        snapshots = self._snapshots()
        previous = snapshots.get(uid)
        # If save is called without a preceding get(), treat it as an insert-only
        # state. Never infer deletions from an unknown/stale snapshot.
        old = previous or CompanionState(user_id=uid)

        for key, record in state.consents.items():
            old_record = old.consents.get(key)
            if old_record == record:
                continue
            granted = bool(record.granted)
            payload = {
                "user_id": uid, "scope": _enum_db(record.scope.value),
                "granted": granted,
                "granted_at": record.updated_at if granted else None,
                "revoked_at": None if granted else record.updated_at,
                "updated_at": record.updated_at or _now(),
            }
            self.db.table("companion_consents").upsert(
                payload, on_conflict="user_id,scope"
            ).execute()

        old_context = {item.id: item for item in old.context_items}
        new_context = {item.id: item for item in state.context_items}
        for item_id, item in new_context.items():
            if old_context.get(item_id) == item:
                continue
            payload = {
                "id": item.id, "user_id": uid,
                "scope": _enum_db(item.scope.value),
                "context_type": item.category,
                "content": {"text": item.content},
                "source": item.source, "expires_at": item.expires_at,
                "created_at": item.created_at,
                "updated_at": _now(),
            }
            self.db.table("companion_context").upsert(payload).execute()

        # Only soft-delete IDs that were present in this request's original
        # snapshot and are now absent. Never sweep the user's whole context table.
        for item_id in set(old_context) - set(new_context):
            (self.db.table("companion_context")
             .update({"deleted_at": _now(), "updated_at": _now()})
             .eq("user_id", uid).eq("id", item_id)
             .is_("deleted_at", "null").execute())

        old_needs = {item.id: item for item in old.needs}
        for need in state.needs:
            if old_needs.get(need.id) == need:
                continue
            payload = {
                "id": need.id, "user_id": uid, "title": need.title,
                "description": need.description,
                "status": _enum_db(need.status.value),
                "priority": _enum_db(need.user_priority.value),
                "next_step": need.next_step,
                "created_at": need.created_at,
                "updated_at": need.updated_at or _now(),
            }
            self.db.table("companion_needs").upsert(payload).execute()

        old_events = {item.id for item in old.events}
        for event in state.events:
            if event.id in old_events:
                continue
            self.db.table("companion_events").upsert({
                "id": event.id, "user_id": uid,
                "event_type": event.event_type,
                "payload": {"summary": event.summary},
                "occurred_at": event.created_at,
            }).execute()

        snapshots[uid] = deepcopy(state)


class SupabaseProposalRepository:
    def __init__(self, db):
        self.db = db

    def list_for_user(self, user_id: str) -> list[ProactiveProposal]:
        rows = (self.db.table("proactive_proposals").select("*")
                .eq("user_id", user_id).order("created_at", desc=True)
                .limit(100).execute()).data or []
        return [self._from_row(row, user_id) for row in rows]

    @staticmethod
    def _from_row(row: dict[str, Any], user_id: str) -> ProactiveProposal:
        payload = row.get("payload") or {}
        return ProactiveProposal(
            id=str(row["id"]), user_id=user_id,
            proposal_type=str(payload.get("proposal_type") or row["trigger_type"]),
            title=row["title"], reason=str(row.get("description") or ""),
            suggested_action=str(payload.get("suggested_action") or ""),
            source_need_id=payload.get("source_need_id"),
            status=ProposalStatus(row["status"].lower()),
            created_at=row.get("created_at") or "",
        )

    def save(self, proposal: ProactiveProposal) -> None:
        dedupe = f"{proposal.proposal_type}:{proposal.source_need_id or 'none'}"
        # Fast-path duplicate check; the partial unique index remains the final
        # race-safe guard when two workers evaluate the same event concurrently.
        existing = (self.db.table("proactive_proposals").select("id")
                    .eq("user_id", proposal.user_id)
                    .eq("dedupe_key", dedupe).eq("status", "PROPOSED")
                    .limit(1).execute()).data or []
        if existing:
            return
        try:
            self.db.table("proactive_proposals").insert({
                "id": proposal.id, "user_id": proposal.user_id,
                "trigger_type": proposal.proposal_type,
                "dedupe_key": dedupe,
                "title": proposal.title, "description": proposal.reason,
                "status": proposal.status.value.upper(),
                "payload": {
                    "proposal_type": proposal.proposal_type,
                    "suggested_action": proposal.suggested_action,
                    "source_need_id": proposal.source_need_id,
                },
                "created_at": proposal.created_at,
            }).execute()
        except Exception as exc:
            # PostgreSQL unique_violation from the partial active-dedupe index.
            if getattr(exc, "code", None) != "23505":
                raise

    def update_status(self, user_id: str, proposal_id: str,
                      status: ProposalStatus) -> ProactiveProposal | None:
        values = {"status": status.value.upper(), "updated_at": _now()}
        if status == ProposalStatus.ACCEPTED:
            values["accepted_at"] = values["updated_at"]
        elif status == ProposalStatus.DISMISSED:
            values["dismissed_at"] = values["updated_at"]
        rows = (self.db.table("proactive_proposals").update(values)
                .eq("user_id", user_id).eq("id", proposal_id)
                .select("*").execute()).data or []
        return self._from_row(rows[0], user_id) if rows else None
