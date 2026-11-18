import unittest

from companion_core import (
    CompanionCore,
    CompanionNotFoundError,
    ConsentRequiredError,
    ConsentScope,
    InMemoryCompanionRepository,
    NeedStatus,
    UserPriority,
)


class CompanionCoreTests(unittest.TestCase):
    def setUp(self):
        self.core = CompanionCore(InMemoryCompanionRepository())
        self.core.initialize("user-a")

    def test_initialize_does_not_grant_any_consent(self):
        snap = self.core.snapshot("user-a")
        self.assertEqual(snap["consents"], {})
        self.assertEqual(snap["context_count"], 0)

    def test_health_context_requires_explicit_consent(self):
        with self.assertRaises(ConsentRequiredError):
            self.core.remember_context(
                "user-a", scope=ConsentScope.HEALTH_CONTEXT,
                category="preference", content="..."
            )

    def test_can_save_and_read_consented_context(self):
        self.core.set_consent("user-a", ConsentScope.HEALTH_CONTEXT, True)
        item = self.core.remember_context(
            "user-a", scope=ConsentScope.HEALTH_CONTEXT,
            category="care_preference", content="Prefers clear explanations"
        )
        self.assertEqual(self.core.get_context("user-a"), [item])

    def test_revoking_consent_hides_existing_context(self):
        self.core.set_consent("user-a", ConsentScope.HEALTH_CONTEXT, True)
        self.core.remember_context(
            "user-a", scope=ConsentScope.HEALTH_CONTEXT,
            category="note", content="User-provided note"
        )
        self.core.set_consent("user-a", ConsentScope.HEALTH_CONTEXT, False)
        self.assertEqual(self.core.get_context("user-a"), [])

    def test_user_can_delete_context(self):
        self.core.set_consent("user-a", ConsentScope.BASIC_PROFILE, True)
        item = self.core.remember_context(
            "user-a", scope=ConsentScope.BASIC_PROFILE,
            category="language", content="Vietnamese"
        )
        self.assertTrue(self.core.delete_context("user-a", item.id))
        self.assertEqual(self.core.get_context("user-a"), [])

    def test_need_requires_care_needs_consent(self):
        with self.assertRaises(ConsentRequiredError):
            self.core.create_need(
                "user-a", title="Find a clinic", description="Need help"
            )

    def test_create_and_update_support_need(self):
        self.core.set_consent("user-a", ConsentScope.CARE_NEEDS, True)
        need = self.core.create_need(
            "user-a", title="Find a clinic", description="Need help comparing access",
            user_priority=UserPriority.HIGH, next_step="Clarify location"
        )
        self.assertEqual(need.user_priority, UserPriority.HIGH)
        updated = self.core.update_need(
            "user-a", need.id, status=NeedStatus.IN_PROGRESS,
            next_step="Collect facility options"
        )
        self.assertEqual(updated.status, NeedStatus.IN_PROGRESS)
        self.assertEqual(len(self.core.list_needs("user-a")), 1)

    def test_resolved_need_hidden_by_default(self):
        self.core.set_consent("user-a", ConsentScope.CARE_NEEDS, True)
        need = self.core.create_need(
            "user-a", title="Appointment", description="Arrange appointment"
        )
        self.core.update_need("user-a", need.id, status=NeedStatus.RESOLVED)
        self.assertEqual(self.core.list_needs("user-a"), [])
        self.assertEqual(len(self.core.list_needs("user-a", include_resolved=True)), 1)

    def test_follow_up_requires_consent(self):
        with self.assertRaises(ConsentRequiredError):
            self.core.record_follow_up_event("user-a", "Check-in")

    def test_follow_up_event_is_recorded_after_consent(self):
        self.core.set_consent("user-a", ConsentScope.FOLLOW_UP, True)
        event = self.core.record_follow_up_event("user-a", "User requested a check-in")
        self.assertEqual(event.event_type, "follow_up")
        self.assertEqual(self.core.snapshot("user-a")["events_count"], 3)

    def test_user_data_is_partitioned(self):
        self.core.initialize("user-b")
        self.core.set_consent("user-a", ConsentScope.HEALTH_CONTEXT, True)
        self.core.remember_context(
            "user-a", scope=ConsentScope.HEALTH_CONTEXT,
            category="note", content="Private to user A"
        )
        self.assertEqual(self.core.get_context("user-b"), [])

    def test_unknown_companion_raises(self):
        with self.assertRaises(CompanionNotFoundError):
            self.core.snapshot("unknown")

    def test_empty_user_id_rejected(self):
        with self.assertRaises(ValueError):
            self.core.initialize(" ")

    def test_context_scope_validation(self):
        self.core.set_consent("user-a", ConsentScope.CARE_NEEDS, True)
        with self.assertRaises(ValueError):
            self.core.remember_context(
                "user-a", scope=ConsentScope.CARE_NEEDS,
                category="x", content="y"
            )


if __name__ == "__main__":
    unittest.main()
