"""Y TE MO Proactive Engine v1.

Event-driven, bounded proposal generation for a healthcare companion.
This module does not contact users, infer diagnoses, or make clinical decisions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol
from uuid import uuid4

from companion_core import (
    CompanionCore,
    ConsentScope,
    NeedStatus,
    SupportNeed,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid4())


class TriggerType(str, Enum):
    USER_RETURNED = "user_returned"
    USER_REQUESTED_FOLLOW_UP = "user_requested_follow_up"
    SCHEDULED_REVIEW = "scheduled_review"
    TASK_COMPLETED = "task_completed"
    NEED_STATUS_CHANGED = "need_status_changed"


class ProposalStatus(str, Enum):
    PROPOSED = "proposed"
    DISMISSED = "dismissed"
    ACCEPTED = "accepted"
    EXPIRED = "expired"


@dataclass(frozen=True)
class TriggerEvent:
    user_id: str
    trigger_type: TriggerType
    summary: str
    source: str = "system_event"
    occurred_at: str = ""


@dataclass(frozen=True)
class ProactiveProposal:
    id: str
    user_id: str
    proposal_type: str
    title: str
    reason: str
    suggested_action: str
    source_need_id: str | None
    status: ProposalStatus
    created_at: str


class ProposalRepository(Protocol):
    def list_for_user(self, user_id: str) -> list[ProactiveProposal]: ...
    def save(self, proposal: ProactiveProposal) -> None: ...
    def update_status(
        self, user_id: str, proposal_id: str, status: ProposalStatus
    ) -> ProactiveProposal | None: ...


class InMemoryProposalRepository:
    """Test/local repository only. Not durable across process restarts."""

    def __init__(self) -> None:
        self._items: dict[str, list[ProactiveProposal]] = {}

    def list_for_user(self, user_id: str) -> list[ProactiveProposal]:
        return list(self._items.get(user_id, []))

    def save(self, proposal: ProactiveProposal) -> None:
        self._items.setdefault(proposal.user_id, []).append(proposal)

    def update_status(
        self, user_id: str, proposal_id: str, status: ProposalStatus
    ) -> ProactiveProposal | None:
        items = self._items.get(user_id, [])
        for index, item in enumerate(items):
            if item.id == proposal_id:
                updated = ProactiveProposal(
                    id=item.id,
                    user_id=item.user_id,
                    proposal_type=item.proposal_type,
                    title=item.title,
                    reason=item.reason,
                    suggested_action=item.suggested_action,
                    source_need_id=item.source_need_id,
                    status=status,
                    created_at=item.created_at,
                )
                items[index] = updated
                return updated
        return None


class ProactiveEngineError(Exception):
    pass


class ProactiveEngine:
    """Creates bounded, reviewable suggestions from explicit events and needs."""

    def __init__(
        self,
        companion: CompanionCore,
        proposals: ProposalRepository,
        *,
        max_proposals_per_evaluation: int = 3,
        max_active_proposals_per_user: int = 10,
    ) -> None:
        if not 1 <= max_proposals_per_evaluation <= 10:
            raise ValueError("max_proposals_per_evaluation must be between 1 and 10")
        if not 1 <= max_active_proposals_per_user <= 50:
            raise ValueError("max_active_proposals_per_user must be between 1 and 50")
        self.companion = companion
        self.proposals = proposals
        self.max_proposals_per_evaluation = max_proposals_per_evaluation
        self.max_active_proposals_per_user = max_active_proposals_per_user

    def _consented(self, user_id: str, scope: ConsentScope) -> bool:
        snapshot = self.companion.snapshot(user_id)
        record = snapshot["consents"].get(scope.value)
        return bool(record and record["granted"])

    def evaluate(self, event: TriggerEvent) -> list[ProactiveProposal]:
        """Evaluate one event. Returns proposals only; never sends a message."""
        if not event.user_id.strip():
            raise ValueError("event.user_id must not be empty")
        if not event.summary.strip():
            raise ValueError("event.summary must not be empty")

        # Do not infer permission from a prior conversation or from another scope.
        if not self._consented(event.user_id, ConsentScope.PROACTIVE_CONTACT):
            return []

        needs_consent = self._consented(event.user_id, ConsentScope.CARE_NEEDS)
        follow_up_consent = self._consented(event.user_id, ConsentScope.FOLLOW_UP)
        candidates: list[tuple[str, str, str, str | None]] = []

        if (
            event.trigger_type in {
                TriggerType.SCHEDULED_REVIEW,
                TriggerType.USER_RETURNED,
                TriggerType.NEED_STATUS_CHANGED,
                TriggerType.TASK_COMPLETED,
            }
            and needs_consent
        ):
            for need in self.companion.list_needs(event.user_id):
                if need.status in {NeedStatus.IN_PROGRESS, NeedStatus.WAITING} and need.next_step:
                    candidates.append((
                        "resume_open_need",
                        f"Tiếp tục: {need.title}",
                        f"Nhu cầu này vẫn ở trạng thái {need.status.value}; bước tiếp theo đã được ghi nhận: {need.next_step}",
                        need.id,
                    ))

        if (
            event.trigger_type == TriggerType.USER_REQUESTED_FOLLOW_UP
            and follow_up_consent
        ):
            candidates.append((
                "requested_follow_up",
                "Tiếp tục hỗ trợ theo yêu cầu",
                "Người dùng đã chủ động yêu cầu được theo dõi hoặc hỗ trợ tiếp.",
                None,
            ))

        existing = self.proposals.list_for_user(event.user_id)
        active = [
            item for item in existing
            if item.status in {ProposalStatus.PROPOSED, ProposalStatus.ACCEPTED}
        ]
        active_keys = {
            (item.proposal_type, item.source_need_id)
            for item in active
        }
        remaining_capacity = max(
            0, self.max_active_proposals_per_user - len(active)
        )
        limit = min(self.max_proposals_per_evaluation, remaining_capacity)

        created: list[ProactiveProposal] = []
        for proposal_type, title, reason, need_id in candidates:
            if len(created) >= limit:
                break
            key = (proposal_type, need_id)
            if key in active_keys:
                continue
            proposal = ProactiveProposal(
                id=_new_id(),
                user_id=event.user_id,
                proposal_type=proposal_type,
                title=title,
                reason=reason,
                suggested_action=(
                    "Hỏi người dùng có muốn tiếp tục bước này không; "
                    "không tự thực hiện thay người dùng."
                ),
                source_need_id=need_id,
                status=ProposalStatus.PROPOSED,
                created_at=_now(),
            )
            self.proposals.save(proposal)
            created.append(proposal)
            active_keys.add(key)
        return created

    def list_proposals(self, user_id: str) -> list[ProactiveProposal]:
        # Snapshot verifies that this companion exists and is scoped to this user.
        self.companion.snapshot(user_id)
        return self.proposals.list_for_user(user_id)

    def update_proposal(
        self, user_id: str, proposal_id: str, status: ProposalStatus
    ) -> ProactiveProposal:
        self.companion.snapshot(user_id)
        updated = self.proposals.update_status(user_id, proposal_id, status)
        if updated is None:
            raise ProactiveEngineError("Proposal not found for this user")
        return updated
