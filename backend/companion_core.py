"""Y TE MO Companion Core v1.

A framework-neutral, consent-aware state layer for a persistent healthcare
companion. This module deliberately contains no diagnosis, treatment advice,
LLM calls, network access, or production database adapter.

The included in-memory repository is for tests and local prototyping only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return str(uuid4())


class ConsentScope(str, Enum):
    BASIC_PROFILE = "basic_profile"
    CARE_NEEDS = "care_needs"
    HEALTH_CONTEXT = "health_context"
    FOLLOW_UP = "follow_up"
    PROACTIVE_CONTACT = "proactive_contact"


class NeedStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    RESOLVED = "resolved"
    PAUSED = "paused"


class UserPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class CompanionError(Exception):
    """Base error for companion core operations."""


class ConsentRequiredError(CompanionError):
    """Raised when an operation requires consent that has not been granted."""


class CompanionNotFoundError(CompanionError):
    """Raised when the requested user's companion state does not exist."""


@dataclass(frozen=True)
class ConsentRecord:
    scope: ConsentScope
    granted: bool
    updated_at: str


@dataclass(frozen=True)
class ContextItem:
    id: str
    user_id: str
    scope: ConsentScope
    category: str
    content: str
    source: str
    created_at: str
    expires_at: str | None = None


@dataclass(frozen=True)
class SupportNeed:
    id: str
    user_id: str
    title: str
    description: str
    status: NeedStatus
    user_priority: UserPriority
    created_at: str
    updated_at: str
    next_step: str | None = None


@dataclass(frozen=True)
class CompanionEvent:
    id: str
    user_id: str
    event_type: str
    summary: str
    created_at: str


@dataclass
class CompanionState:
    user_id: str
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    consents: dict[str, ConsentRecord] = field(default_factory=dict)
    context_items: list[ContextItem] = field(default_factory=list)
    needs: list[SupportNeed] = field(default_factory=list)
    events: list[CompanionEvent] = field(default_factory=list)


class CompanionRepository(Protocol):
    """Storage contract. A production adapter must enforce user isolation."""

    def get(self, user_id: str) -> CompanionState | None: ...
    def save(self, state: CompanionState) -> None: ...


class InMemoryCompanionRepository:
    """Local/test repository. Data disappears when the process exits."""

    def __init__(self) -> None:
        self._states: dict[str, CompanionState] = {}

    def get(self, user_id: str) -> CompanionState | None:
        state = self._states.get(user_id)
        return _clone_state(state) if state else None

    def save(self, state: CompanionState) -> None:
        self._states[state.user_id] = _clone_state(state)


def _clone_state(state: CompanionState) -> CompanionState:
    return CompanionState(
        user_id=state.user_id,
        created_at=state.created_at,
        updated_at=state.updated_at,
        consents=dict(state.consents),
        context_items=list(state.context_items),
        needs=list(state.needs),
        events=list(state.events),
    )


class CompanionCore:
    """Consent-aware lifecycle and support-state manager."""

    def __init__(self, repository: CompanionRepository):
        self.repository = repository

    @staticmethod
    def _validate_user_id(user_id: str) -> str:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        return user_id.strip()

    def _load_or_create(self, user_id: str) -> CompanionState:
        user_id = self._validate_user_id(user_id)
        state = self.repository.get(user_id)
        if state is None:
            state = CompanionState(user_id=user_id)
        return state

    def _load(self, user_id: str) -> CompanionState:
        user_id = self._validate_user_id(user_id)
        state = self.repository.get(user_id)
        if state is None:
            raise CompanionNotFoundError("Companion state not found")
        return state

    @staticmethod
    def _has_consent(state: CompanionState, scope: ConsentScope) -> bool:
        record = state.consents.get(scope.value)
        return bool(record and record.granted)

    def has_consent(self, user_id: str, scope: ConsentScope) -> bool:
        """Public fail-closed consent check for internal memory services."""
        try:
            state = self._load(user_id)
            return bool(state and self._has_consent(state, scope))
        except Exception:
            return False

    @staticmethod
    def _context_is_expired(item: ContextItem) -> bool:
        if not item.expires_at:
            return False
        try:
            value = item.expires_at.replace("Z", "+00:00")
            expiry = datetime.fromisoformat(value)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            return expiry <= datetime.now(timezone.utc)
        except (TypeError, ValueError):
            # Fail closed: malformed expiry must never expose old context.
            return True

    @staticmethod
    def _require_consent(state: CompanionState, scope: ConsentScope) -> None:
        if not CompanionCore._has_consent(state, scope):
            raise ConsentRequiredError(
                f"Consent is required for scope: {scope.value}"
            )

    @staticmethod
    def _add_event(
        state: CompanionState, event_type: str, summary: str
    ) -> None:
        state.events.append(
            CompanionEvent(
                id=_id(),
                user_id=state.user_id,
                event_type=event_type,
                summary=summary,
                created_at=_now(),
            )
        )
        state.updated_at = _now()

    def initialize(self, user_id: str) -> dict[str, Any]:
        """Create a companion record without opting the user into data storage."""
        state = self._load_or_create(user_id)
        self._add_event(state, "companion_initialized", "Companion record initialized")
        self.repository.save(state)
        return self.snapshot(user_id)

    def set_consent(
        self, user_id: str, scope: ConsentScope, granted: bool
    ) -> dict[str, Any]:
        state = self._load_or_create(user_id)
        state.consents[scope.value] = ConsentRecord(
            scope=scope, granted=bool(granted), updated_at=_now()
        )
        # Revocation is destructive for this consent scope:
        # old context must not reappear after consent is granted again.
        if not granted:
            state.context_items = [
                item for item in state.context_items if item.scope != scope
            ]
        self._add_event(
            state,
            "consent_granted" if granted else "consent_revoked",
            f"Consent for {scope.value}: {'granted' if granted else 'revoked'}",
        )
        self.repository.save(state)
        return self.snapshot(user_id)

    def remember_context(
        self,
        user_id: str,
        *,
        scope: ConsentScope,
        category: str,
        content: str,
        source: str = "user_provided",
        expires_at: str | None = None,
    ) -> ContextItem:
        if scope not in {
            ConsentScope.BASIC_PROFILE,
            ConsentScope.HEALTH_CONTEXT,
            ConsentScope.FOLLOW_UP,
        }:
            raise ValueError("Context items require a profile, health, or follow-up scope")
        if not category.strip() or not content.strip():
            raise ValueError("category and content must not be empty")
        state = self._load(user_id)
        self._require_consent(state, scope)
        item = ContextItem(
            id=_id(),
            user_id=state.user_id,
            scope=scope,
            category=category.strip(),
            content=content.strip(),
            source=source.strip() or "user_provided",
            created_at=_now(),
            expires_at=expires_at,
        )
        state.context_items.append(item)
        self._add_event(state, "context_saved", f"Context saved under {scope.value}")
        self.repository.save(state)
        return item

    def get_context(
        self, user_id: str, scopes: list[ConsentScope] | None = None
    ) -> list[ContextItem]:
        state = self._load(user_id)
        allowed = set(scopes) if scopes is not None else set(ConsentScope)
        return [
            item for item in state.context_items
            if item.scope in allowed
            and self._has_consent(state, item.scope)
            and not self._context_is_expired(item)
        ]

    def delete_context(self, user_id: str, context_id: str) -> bool:
        state = self._load(user_id)
        before = len(state.context_items)
        state.context_items = [
            item for item in state.context_items if item.id != context_id
        ]
        deleted = len(state.context_items) != before
        if deleted:
            self._add_event(state, "context_deleted", "A context item was deleted")
            self.repository.save(state)
        return deleted

    def create_need(
        self,
        user_id: str,
        *,
        title: str,
        description: str,
        user_priority: UserPriority = UserPriority.NORMAL,
        next_step: str | None = None,
    ) -> SupportNeed:
        if not title.strip() or not description.strip():
            raise ValueError("title and description must not be empty")
        state = self._load(user_id)
        self._require_consent(state, ConsentScope.CARE_NEEDS)
        now = _now()
        need = SupportNeed(
            id=_id(),
            user_id=state.user_id,
            title=title.strip(),
            description=description.strip(),
            status=NeedStatus.OPEN,
            user_priority=user_priority,
            created_at=now,
            updated_at=now,
            next_step=next_step.strip() if next_step else None,
        )
        state.needs.append(need)
        self._add_event(state, "support_need_created", "A support need was recorded")
        self.repository.save(state)
        return need

    def update_need(
        self,
        user_id: str,
        need_id: str,
        *,
        status: NeedStatus | None = None,
        next_step: str | None = None,
    ) -> SupportNeed:
        state = self._load(user_id)
        self._require_consent(state, ConsentScope.CARE_NEEDS)
        for index, need in enumerate(state.needs):
            if need.id == need_id:
                updated = SupportNeed(
                    id=need.id,
                    user_id=need.user_id,
                    title=need.title,
                    description=need.description,
                    status=status or need.status,
                    user_priority=need.user_priority,
                    created_at=need.created_at,
                    updated_at=_now(),
                    next_step=next_step.strip() if next_step is not None else need.next_step,
                )
                state.needs[index] = updated
                self._add_event(state, "support_need_updated", "A support need was updated")
                self.repository.save(state)
                return updated
        raise CompanionNotFoundError("Support need not found")

    def list_needs(
        self, user_id: str, include_resolved: bool = False
    ) -> list[SupportNeed]:
        state = self._load(user_id)
        self._require_consent(state, ConsentScope.CARE_NEEDS)
        return [
            need for need in state.needs
            if include_resolved or need.status != NeedStatus.RESOLVED
        ]

    def record_follow_up_event(
        self, user_id: str, summary: str
    ) -> CompanionEvent:
        state = self._load(user_id)
        self._require_consent(state, ConsentScope.FOLLOW_UP)
        if not summary.strip():
            raise ValueError("summary must not be empty")
        event = CompanionEvent(
            id=_id(),
            user_id=state.user_id,
            event_type="follow_up",
            summary=summary.strip(),
            created_at=_now(),
        )
        state.events.append(event)
        state.updated_at = _now()
        self.repository.save(state)
        return event

    def snapshot(self, user_id: str) -> dict[str, Any]:
        state = self._load(user_id)
        return {
            "user_id": state.user_id,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
            "consents": {
                key: {"granted": value.granted, "updated_at": value.updated_at}
                for key, value in state.consents.items()
            },
            "context_count": len(state.context_items),
            "needs_count": len(state.needs),
            "open_needs_count": sum(
                1 for need in state.needs
                if need.status not in {NeedStatus.RESOLVED, NeedStatus.PAUSED}
            ),
            "events_count": len(state.events),
        }
