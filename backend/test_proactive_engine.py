import unittest
from companion_core import CompanionCore, ConsentScope, InMemoryCompanionRepository, NeedStatus
from proactive_engine import InMemoryProposalRepository, ProactiveEngine, ProactiveEngineError, ProposalStatus, TriggerEvent, TriggerType

class ProactiveEngineTests(unittest.TestCase):
    def setUp(self):
        self.core = CompanionCore(InMemoryCompanionRepository())
        self.core.initialize("u1")
        self.repo = InMemoryProposalRepository()
        self.engine = ProactiveEngine(self.core, self.repo)

    def grant(self, *scopes):
        for scope in scopes:
            self.core.set_consent("u1", scope, True)

    def add_waiting_need(self):
        self.grant(ConsentScope.CARE_NEEDS)
        need = self.core.create_need("u1", title="Tìm cơ sở khám", description="Người dùng muốn so sánh", next_step="Xác nhận khu vực")
        return self.core.update_need("u1", need.id, status=NeedStatus.WAITING)

    def event(self, trigger=TriggerType.SCHEDULED_REVIEW):
        return TriggerEvent("u1", trigger, "A permitted event occurred")

    def test_no_proactive_consent_means_no_proposal(self):
        self.add_waiting_need()
        self.assertEqual(self.engine.evaluate(self.event()), [])

    def test_proactive_consent_alone_does_not_expose_care_needs(self):
        self.add_waiting_need()
        self.core.set_consent("u1", ConsentScope.CARE_NEEDS, False)
        self.grant(ConsentScope.PROACTIVE_CONTACT)
        self.assertEqual(self.engine.evaluate(self.event()), [])

    def test_waiting_need_creates_proposal_with_both_consents(self):
        need = self.add_waiting_need()
        self.grant(ConsentScope.PROACTIVE_CONTACT)
        proposals = self.engine.evaluate(self.event())
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].source_need_id, need.id)
        self.assertEqual(proposals[0].status, ProposalStatus.PROPOSED)

    def test_duplicate_active_proposal_is_not_created(self):
        self.add_waiting_need()
        self.grant(ConsentScope.PROACTIVE_CONTACT)
        self.engine.evaluate(self.event())
        self.assertEqual(self.engine.evaluate(self.event()), [])

    def test_resolved_need_does_not_create_proposal(self):
        need = self.add_waiting_need()
        self.core.update_need("u1", need.id, status=NeedStatus.RESOLVED)
        self.grant(ConsentScope.PROACTIVE_CONTACT)
        self.assertEqual(self.engine.evaluate(self.event()), [])

    def test_no_next_step_means_no_resume_proposal(self):
        self.grant(ConsentScope.CARE_NEEDS, ConsentScope.PROACTIVE_CONTACT)
        self.core.create_need("u1", title="Need title", description="Need description")
        self.assertEqual(self.engine.evaluate(self.event()), [])

    def test_user_requested_follow_up_requires_follow_up_consent(self):
        self.grant(ConsentScope.PROACTIVE_CONTACT)
        self.assertEqual(self.engine.evaluate(self.event(TriggerType.USER_REQUESTED_FOLLOW_UP)), [])

    def test_user_requested_follow_up_with_consent(self):
        self.grant(ConsentScope.PROACTIVE_CONTACT, ConsentScope.FOLLOW_UP)
        proposals = self.engine.evaluate(self.event(TriggerType.USER_REQUESTED_FOLLOW_UP))
        self.assertEqual(proposals[0].proposal_type, "requested_follow_up")

    def test_dismissed_proposal_can_be_proposed_again(self):
        self.add_waiting_need()
        self.grant(ConsentScope.PROACTIVE_CONTACT)
        first = self.engine.evaluate(self.event())[0]
        self.engine.update_proposal("u1", first.id, ProposalStatus.DISMISSED)
        self.assertEqual(len(self.engine.evaluate(self.event())), 1)

    def test_active_proposal_cap_is_enforced(self):
        self.add_waiting_need()
        self.grant(ConsentScope.PROACTIVE_CONTACT)
        engine = ProactiveEngine(self.core, self.repo, max_active_proposals_per_user=1)
        self.assertEqual(len(engine.evaluate(self.event())), 1)
        self.assertEqual(engine.evaluate(self.event()), [])

    def test_proposal_cannot_be_accessed_under_another_user(self):
        self.add_waiting_need()
        self.grant(ConsentScope.PROACTIVE_CONTACT)
        self.engine.evaluate(self.event())
        with self.assertRaises(ProactiveEngineError):
            self.engine.update_proposal("u1", "not-the-id", ProposalStatus.DISMISSED)

    def test_invalid_limits_rejected(self):
        with self.assertRaises(ValueError):
            ProactiveEngine(self.core, self.repo, max_proposals_per_evaluation=0)

    def test_invalid_event_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.evaluate(TriggerEvent(" ", TriggerType.USER_RETURNED, "x"))

    def test_unrelated_trigger_does_not_propose_need_resume(self):
        self.add_waiting_need()
        self.grant(ConsentScope.PROACTIVE_CONTACT)
        self.assertEqual(self.engine.evaluate(self.event(TriggerType.USER_REQUESTED_FOLLOW_UP)), [])

if __name__ == "__main__":
    unittest.main()
