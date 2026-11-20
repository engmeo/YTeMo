import unittest

from planning.plan_graph import (
    PlanGraph, PlanGraphNode, PlanGraphEdge, append_plan_version,
)
from planning.replanning import (
    assess_replan, PlanCandidateScore, rank_plan_candidates,
)
from planning.agent_integration import AgentStepRequest, build_agent_handoff


class TestPlanGraph(unittest.TestCase):
    def test_append_version_preserves_history(self):
        first = PlanGraphNode("v1", "plan-a", 1, "proposed", {"goal": "g"})
        graph = PlanGraph(nodes=(first,))
        updated = append_plan_version(
            graph, node_id="v2", plan_id="plan-a",
            payload={"goal": "revised"}, parent_node_id="v1",
        )
        self.assertEqual(len(graph.nodes), 1)
        self.assertEqual(updated.latest_version("plan-a"), 2)
        self.assertEqual(updated.edges[0].relation, "supersedes")

    def test_dependency_cycle_rejected(self):
        a = PlanGraphNode("a", "p", 1, "proposed", {})
        b = PlanGraphNode("b", "p", 2, "proposed", {})
        with self.assertRaises(ValueError):
            PlanGraph((a, b), (
                PlanGraphEdge("a", "b", "depends_on"),
                PlanGraphEdge("b", "a", "depends_on"),
            ))

    def test_unknown_parent_rejected(self):
        with self.assertRaises(ValueError):
            append_plan_version(
                PlanGraph(), node_id="v1", plan_id="p",
                payload={}, parent_node_id="missing",
            )


class TestReplanning(unittest.TestCase):
    def test_changed_fact_marks_only_dependent_steps(self):
        decision = assess_replan(
            changed_fact_keys={"location"},
            step_fact_dependencies={
                "step-1": {"location", "weather"},
                "step-2": {"inventory"},
            },
        )
        self.assertTrue(decision.should_replan)
        self.assertEqual(decision.affected_step_ids, ("step-1",))

    def test_explicit_risk_trigger(self):
        decision = assess_replan(
            changed_fact_keys=set(),
            step_fact_dependencies={},
            risk_limit_exceeded=True,
        )
        self.assertTrue(decision.should_replan)
        self.assertIn("risk_limit_exceeded", decision.reasons)

    def test_candidate_ranking(self):
        ranked = rank_plan_candidates((
            PlanCandidateScore("A", 10, 4, 2),
            PlanCandidateScore("B", 9, 1, 1),
        ))
        self.assertEqual(ranked[0][0], "B")


class TestAgentIntegration(unittest.TestCase):
    def test_handoff_is_proposal_only(self):
        request = AgentStepRequest(
            "s1", "research_agent", "Collect evidence",
            {"source_scope": "approved"}, True,
        )
        proposal = build_agent_handoff(
            plan_id="p1", domain="generic", steps=(request,),
        )
        self.assertEqual(proposal.status, "proposal_only")
        self.assertFalse(proposal.execution_authorized)
        self.assertTrue(proposal.requests[0].requires_human_approval)

    def test_duplicate_step_rejected(self):
        request = AgentStepRequest("s1", "agent", "Do work", {})
        with self.assertRaises(ValueError):
            build_agent_handoff(
                plan_id="p", domain="generic", steps=(request, request),
            )


if __name__ == "__main__":
    unittest.main()
