import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

from planning.models import Goal, StateSnapshot
from planning.pipeline_contracts import (
    PipelinePolicy,
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    PipelineStageResult,
    PipelineStatus,
    StageProvenance,
    StageStatus,
)


def make_goal(domain="generic"):
    return Goal(
        goal_id="goal-001",
        description="Test goal",
        domain=domain,
    )


def make_state(domain="generic"):
    return StateSnapshot(
        subject_id="subject-001",
        domain=domain,
        revision=0,
        as_of=datetime.now(timezone.utc).isoformat(),
        facts=(),
    )


def make_provenance(stage=PipelineStage.STRATEGY_PLANNING):
    return StageProvenance(
        stage=stage,
        component="test-planner",
        component_version="1.0",
        input_revision=0,
        output_revision=1,
        evidence_refs=("evidence-001",),
        metadata={"source": "unit-test"},
    )


class PipelinePolicyTests(unittest.TestCase):
    def test_default_policy_is_explicit_and_safe(self):
        policy = PipelinePolicy()
        self.assertEqual(policy.required_stages, ())
        self.assertFalse(policy.governance_required)
        self.assertTrue(policy.stop_on_stage_failure)
        self.assertTrue(policy.allow_partial_results)
        self.assertTrue(policy.require_provenance)

    def test_required_stages_reject_duplicates(self):
        with self.assertRaises(ValueError):
            PipelinePolicy(
                required_stages=(
                    PipelineStage.DECISION,
                    PipelineStage.DECISION,
                )
            )

    def test_required_stages_reject_wrong_type(self):
        with self.assertRaises(TypeError):
            PipelinePolicy(required_stages=("decision",))

    def test_policy_version_must_not_be_blank(self):
        with self.assertRaises(ValueError):
            PipelinePolicy(version="  ")


class PipelineRequestTests(unittest.TestCase):
    def test_valid_request(self):
        request = PipelineRequest(
            goal=make_goal(),
            state=make_state(),
            enabled_stages=(
                PipelineStage.STRATEGY_PLANNING,
                PipelineStage.VALIDATION,
            ),
        )
        self.assertTrue(request.request_id)
        self.assertEqual(request.goal.domain, request.state.domain)

    def test_domain_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            PipelineRequest(
                goal=make_goal("healthcare"),
                state=make_state("generic"),
                enabled_stages=(PipelineStage.DECISION,),
            )

    def test_empty_stage_selection_is_rejected(self):
        with self.assertRaises(ValueError):
            PipelineRequest(
                goal=make_goal(),
                state=make_state(),
                enabled_stages=(),
            )

    def test_duplicate_enabled_stages_are_rejected(self):
        with self.assertRaises(ValueError):
            PipelineRequest(
                goal=make_goal(),
                state=make_state(),
                enabled_stages=(
                    PipelineStage.DECISION,
                    PipelineStage.DECISION,
                ),
            )

    def test_required_stage_must_be_enabled(self):
        with self.assertRaises(ValueError):
            PipelineRequest(
                goal=make_goal(),
                state=make_state(),
                enabled_stages=(PipelineStage.DECISION,),
                policy=PipelinePolicy(
                    required_stages=(PipelineStage.GOVERNANCE,)
                ),
            )

    def test_governance_requirement_must_be_enabled(self):
        with self.assertRaises(ValueError):
            PipelineRequest(
                goal=make_goal(),
                state=make_state(),
                enabled_stages=(PipelineStage.DECISION,),
                policy=PipelinePolicy(governance_required=True),
            )

    def test_metadata_is_recursively_immutable(self):
        request = PipelineRequest(
            goal=make_goal(),
            state=make_state(),
            enabled_stages=(PipelineStage.DECISION,),
            metadata={"nested": {"items": [1, 2]}},
        )
        self.assertEqual(request.metadata["nested"]["items"], (1, 2))
        with self.assertRaises(TypeError):
            request.metadata["new"] = "value"
        with self.assertRaises(TypeError):
            request.metadata["nested"]["new"] = "value"

    def test_non_json_metadata_is_rejected(self):
        with self.assertRaises(TypeError):
            PipelineRequest(
                goal=make_goal(),
                state=make_state(),
                enabled_stages=(PipelineStage.DECISION,),
                metadata={"invalid": object()},
            )


class StageProvenanceTests(unittest.TestCase):
    def test_valid_provenance(self):
        provenance = make_provenance()
        self.assertEqual(provenance.stage, PipelineStage.STRATEGY_PLANNING)
        self.assertEqual(provenance.output_revision, 1)

    def test_negative_revision_is_rejected(self):
        with self.assertRaises(ValueError):
            StageProvenance(
                stage=PipelineStage.DECISION,
                component="decision-engine",
                component_version="1",
                input_revision=-1,
            )

    def test_empty_component_is_rejected(self):
        with self.assertRaises(ValueError):
            StageProvenance(
                stage=PipelineStage.DECISION,
                component=" ",
                component_version="1",
            )

    def test_metadata_is_immutable(self):
        provenance = StageProvenance(
            stage=PipelineStage.DECISION,
            component="decision-engine",
            component_version="1",
            metadata={"details": [1, 2]},
        )
        self.assertEqual(provenance.metadata["details"], (1, 2))
        with self.assertRaises(TypeError):
            provenance.metadata["details"] = (3,)


class PipelineStageResultTests(unittest.TestCase):
    def test_valid_stage_result_preserves_engine_output(self):
        output = {"engine_specific": "result"}
        result = PipelineStageResult(
            stage=PipelineStage.STRATEGY_PLANNING,
            status=StageStatus.SUCCEEDED,
            output=output,
            provenance=make_provenance(),
        )
        self.assertIs(result.output, output)

    def test_provenance_stage_must_match(self):
        with self.assertRaises(ValueError):
            PipelineStageResult(
                stage=PipelineStage.DECISION,
                status=StageStatus.SUCCEEDED,
                provenance=make_provenance(
                    PipelineStage.STRATEGY_PLANNING
                ),
            )

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaises(ValueError):
            PipelineStageResult(
                stage=PipelineStage.DECISION,
                status=StageStatus.RUNNING,
                started_at=datetime.now(),
            )

    def test_completion_requires_start_time(self):
        with self.assertRaises(ValueError):
            PipelineStageResult(
                stage=PipelineStage.DECISION,
                status=StageStatus.SUCCEEDED,
                completed_at=datetime.now(timezone.utc),
            )

    def test_completion_cannot_precede_start(self):
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            PipelineStageResult(
                stage=PipelineStage.DECISION,
                status=StageStatus.SUCCEEDED,
                started_at=now,
                completed_at=now - timedelta(seconds=1),
            )

    def test_issues_must_be_tuple_of_strings(self):
        with self.assertRaises(TypeError):
            PipelineStageResult(
                stage=PipelineStage.DECISION,
                status=StageStatus.FAILED,
                issues=("valid", 123),
            )


class PipelineResultTests(unittest.TestCase):
    def make_result(self, stage_results=()):
        return PipelineResult(
            request_id="request-001",
            goal_id="goal-001",
            domain="generic",
            status=PipelineStatus.SUCCEEDED,
            stage_results=stage_results,
            started_at=datetime.now(timezone.utc),
        )

    def test_valid_pipeline_result(self):
        result = self.make_result((
            PipelineStageResult(
                stage=PipelineStage.DECISION,
                status=StageStatus.SUCCEEDED,
            ),
        ))
        self.assertEqual(result.status, PipelineStatus.SUCCEEDED)

    def test_duplicate_stage_results_are_rejected(self):
        item = PipelineStageResult(
            stage=PipelineStage.DECISION,
            status=StageStatus.SUCCEEDED,
        )
        with self.assertRaises(ValueError):
            self.make_result((item, item))

    def test_stage_results_must_be_typed(self):
        with self.assertRaises(TypeError):
            self.make_result(("not-a-stage-result",))

    def test_completed_at_must_not_precede_started_at(self):
        started = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            PipelineResult(
                request_id="request-001",
                goal_id="goal-001",
                domain="generic",
                status=PipelineStatus.FAILED,
                stage_results=(),
                started_at=started,
                completed_at=started - timedelta(seconds=1),
            )

    def test_metadata_is_immutable(self):
        result = PipelineResult(
            request_id="request-001",
            goal_id="goal-001",
            domain="generic",
            status=PipelineStatus.PARTIAL,
            stage_results=(),
            started_at=datetime.now(timezone.utc),
            metadata={"trace": {"stages": ["decision"]}},
        )
        self.assertEqual(result.metadata["trace"]["stages"], ("decision",))
        with self.assertRaises(TypeError):
            result.metadata["trace"]["stages"] = ()

    def test_contract_dataclasses_are_frozen(self):
        policy = PipelinePolicy()
        with self.assertRaises(FrozenInstanceError):
            policy.version = "2"


if __name__ == "__main__":
    unittest.main(verbosity=2)