"""Phase 5 release gates for healthcare domain and companion-agent boundaries."""
import pytest

from companion_core import (
    CompanionCore, ConsentRequiredError, ConsentScope,
    InMemoryCompanionRepository, NeedStatus,
)
from proactive_engine import (
    InMemoryProposalRepository, ProactiveEngine, ProposalStatus,
    TriggerEvent, TriggerType,
)
from planning.contracts import DomainPolicy, PlanningDomainAdapter
from planning.models import StepRisk
from planning.domains.healthcare.policy import HealthcareDomainAdapter


def _core(user_id="phase5-user"):
    core = CompanionCore(InMemoryCompanionRepository())
    core.initialize(user_id)
    return core


def _event(user_id="phase5-user", trigger=TriggerType.SCHEDULED_REVIEW):
    return TriggerEvent(user_id, trigger, "A permitted event occurred")


def test_companion_initialization_is_opt_in_and_does_not_grant_consent():
    snapshot = _core().snapshot("phase5-user")
    assert snapshot["consents"] == {}
    assert snapshot["context_count"] == 0


def test_health_context_requires_explicit_health_context_consent():
    core = _core()
    with pytest.raises(ConsentRequiredError):
        core.remember_context(
            "phase5-user", scope=ConsentScope.HEALTH_CONTEXT,
            category="care_preference", content="User supplied preference",
        )


def test_consent_scopes_are_independent():
    core = _core()
    core.set_consent("phase5-user", ConsentScope.BASIC_PROFILE, True)
    with pytest.raises(ConsentRequiredError):
        core.remember_context(
            "phase5-user", scope=ConsentScope.HEALTH_CONTEXT,
            category="note", content="Health context",
        )


def test_revocation_deletes_only_its_scope_and_regrant_does_not_restore_data():
    core = _core()
    core.set_consent("phase5-user", ConsentScope.HEALTH_CONTEXT, True)
    core.set_consent("phase5-user", ConsentScope.BASIC_PROFILE, True)
    health = core.remember_context(
        "phase5-user", scope=ConsentScope.HEALTH_CONTEXT,
        category="note", content="Sensitive context",
    )
    profile = core.remember_context(
        "phase5-user", scope=ConsentScope.BASIC_PROFILE,
        category="language", content="Vietnamese",
    )
    core.set_consent("phase5-user", ConsentScope.HEALTH_CONTEXT, False)
    assert core.get_context("phase5-user") == [profile]
    core.set_consent("phase5-user", ConsentScope.HEALTH_CONTEXT, True)
    assert core.get_context("phase5-user") == [profile]
    assert health not in core.get_context("phase5-user")


def test_context_is_partitioned_by_user():
    core = _core()
    core.initialize("another-user")
    core.set_consent("phase5-user", ConsentScope.BASIC_PROFILE, True)
    core.remember_context(
        "phase5-user", scope=ConsentScope.BASIC_PROFILE,
        category="language", content="Vietnamese",
    )
    assert core.get_context("another-user") == []


def test_care_needs_and_follow_up_require_their_own_consents():
    core = _core()
    with pytest.raises(ConsentRequiredError):
        core.create_need("phase5-user", title="Need", description="Description")
    with pytest.raises(ConsentRequiredError):
        core.record_follow_up_event("phase5-user", "Requested follow-up")


def test_healthcare_adapter_implements_domain_neutral_extension_contract():
    adapter = HealthcareDomainAdapter()
    assert isinstance(adapter, PlanningDomainAdapter)
    policy = adapter.get_policy()
    assert isinstance(policy, DomainPolicy)
    assert policy.domain_id == "healthcare"
    assert policy.required_human_approval_risks == frozenset()
    assert policy.required_evidence_risks == frozenset({StepRisk.HIGH, StepRisk.CRITICAL})


def test_healthcare_adapter_does_not_modify_generic_domain_contract():
    generic = DomainPolicy("generic")
    healthcare = HealthcareDomainAdapter().get_policy()
    assert generic.domain_id == "generic"
    assert generic.required_evidence_risks == frozenset()
    assert healthcare.domain_id != generic.domain_id


def test_proactive_engine_requires_proactive_contact_consent():
    core = _core()
    core.set_consent("phase5-user", ConsentScope.CARE_NEEDS, True)
    need = core.create_need(
        "phase5-user", title="Support request", description="User requested help",
        next_step="Ask whether to continue",
    )
    core.update_need("phase5-user", need.id, status=NeedStatus.WAITING)
    engine = ProactiveEngine(core, InMemoryProposalRepository())
    assert engine.evaluate(_event()) == []


def test_proactive_need_resume_requires_both_need_and_contact_consents():
    core = _core()
    core.set_consent("phase5-user", ConsentScope.CARE_NEEDS, True)
    need = core.create_need(
        "phase5-user", title="Support request", description="User requested help",
        next_step="Ask whether to continue",
    )
    core.update_need("phase5-user", need.id, status=NeedStatus.WAITING)
    core.set_consent("phase5-user", ConsentScope.PROACTIVE_CONTACT, True)
    engine = ProactiveEngine(core, InMemoryProposalRepository())
    proposals = engine.evaluate(_event())
    assert len(proposals) == 1
    assert proposals[0].source_need_id == need.id
    assert proposals[0].status is ProposalStatus.PROPOSED
    assert "không tự thực hiện" in proposals[0].suggested_action


def test_proactive_follow_up_requires_follow_up_and_contact_consents():
    core = _core()
    engine = ProactiveEngine(core, InMemoryProposalRepository())
    core.set_consent("phase5-user", ConsentScope.PROACTIVE_CONTACT, True)
    assert engine.evaluate(_event(trigger=TriggerType.USER_REQUESTED_FOLLOW_UP)) == []
    core.set_consent("phase5-user", ConsentScope.FOLLOW_UP, True)
    proposals = engine.evaluate(_event(trigger=TriggerType.USER_REQUESTED_FOLLOW_UP))
    assert len(proposals) == 1
    assert proposals[0].proposal_type == "requested_follow_up"


def test_proactive_engine_deduplicates_active_proposals_and_respects_cap():
    core = _core()
    core.set_consent("phase5-user", ConsentScope.CARE_NEEDS, True)
    need = core.create_need(
        "phase5-user", title="Support request", description="User requested help",
        next_step="Ask whether to continue",
    )
    core.update_need("phase5-user", need.id, status=NeedStatus.IN_PROGRESS)
    core.set_consent("phase5-user", ConsentScope.PROACTIVE_CONTACT, True)
    engine = ProactiveEngine(
        core, InMemoryProposalRepository(), max_active_proposals_per_user=1
    )
    assert len(engine.evaluate(_event())) == 1
    assert engine.evaluate(_event()) == []


def test_resolved_need_does_not_generate_proactive_proposal():
    core = _core()
    core.set_consent("phase5-user", ConsentScope.CARE_NEEDS, True)
    need = core.create_need(
        "phase5-user", title="Completed support", description="Resolved by user",
        next_step="No further action",
    )
    core.update_need("phase5-user", need.id, status=NeedStatus.RESOLVED)
    core.set_consent("phase5-user", ConsentScope.PROACTIVE_CONTACT, True)
    assert ProactiveEngine(core, InMemoryProposalRepository()).evaluate(_event()) == []


def test_proactive_engine_returns_proposals_without_sending_or_executing_actions():
    core = _core()
    core.set_consent("phase5-user", ConsentScope.FOLLOW_UP, True)
    core.set_consent("phase5-user", ConsentScope.PROACTIVE_CONTACT, True)
    proposals = ProactiveEngine(core, InMemoryProposalRepository()).evaluate(
        _event(trigger=TriggerType.USER_REQUESTED_FOLLOW_UP)
    )
    assert len(proposals) == 1
    assert proposals[0].status is ProposalStatus.PROPOSED
    assert proposals[0].suggested_action