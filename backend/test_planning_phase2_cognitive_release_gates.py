"""Phase 2 release gates for universal cognitive intelligence primitives."""
from __future__ import annotations

import ast
from pathlib import Path


PLANNING_DIR = Path(__file__).parent / "planning"


def test_cognitive_intelligence_modules_exist_and_parse():
    required = (
        "models.py",
        "hierarchy.py",
        "hierarchical_engine.py",
        "search.py",
        "belief_engine.py",
        "decision_engine.py",
        "world_model.py",
        "metacognition.py",
        "meta_planner.py",
        "causal.py",
        "counterfactual.py",
        "multiobjective.py",
    )
    for name in required:
        path = PLANNING_DIR / name
        assert path.is_file(), f"Missing cognitive planning module: {name}"
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def test_goal_contract_is_domain_neutral_and_metadata_is_immutable():
    from planning.models import Goal, GoalPriority

    goal = Goal(
        goal_id="g1",
        description="Reach a target state",
        domain="generic",
        priority=GoalPriority.NORMAL,
        metadata={"source": "user", "tags": ["planning"]},
    )
    assert goal.goal_id == "g1"
    assert goal.domain == "generic"
    try:
        goal.metadata["source"] = "changed"
    except TypeError:
        pass
    else:
        raise AssertionError("Goal metadata must be immutable")


def test_htn_decomposition_preserves_order_and_trace():
    from planning.hierarchy import DecompositionMethod, Task
    from planning.hierarchical_engine import HierarchicalPlanner

    result = HierarchicalPlanner().plan(
        [Task("root", "mission")],
        [
            DecompositionMethod(
                "decompose-mission",
                "mission",
                (Task("sense", "sense environment", True),
                 Task("act", "perform action", True)),
            )
        ],
    )
    assert result.ordered_task_ids == ("sense", "act")
    assert result.decomposition_trace[0].parent_task_id == "root"
    assert result.decomposition_trace[0].child_task_ids == ("sense", "act")


def test_search_ranking_is_deterministic_for_equal_scores():
    from planning.search import SearchCandidate, best_of_n

    result = best_of_n(
        (
            SearchCandidate("z", ("wait",), 1.0),
            SearchCandidate("a", ("inspect",), 1.0),
        ),
        2,
    )
    assert tuple(item.candidate_id for item in result.candidates) == ("a", "z")


def test_belief_update_uses_explicit_evidence_and_normalizes():
    from datetime import datetime, timezone
    from math import isclose
    from planning.models import BeliefHypothesis, BeliefState, StateSnapshot
    from planning.belief_engine import EvidenceLikelihood, update_belief

    now = datetime.now(timezone.utc).isoformat()
    belief = BeliefState(
        StateSnapshot("subject", "generic", 1, now),
        hypotheses=(
            BeliefHypothesis("h1", "Hypothesis one", 0.6),
            BeliefHypothesis("h2", "Hypothesis two", 0.4),
        ),
    )
    result = update_belief(
        belief,
        EvidenceLikelihood(
            "evidence-1", "sensor", "sensor-1", now,
            {"h1": 0.8, "h2": 0.2},
        ),
    )
    probabilities = [item.probability for item in result.belief.hypotheses]
    assert isclose(sum(probabilities), 1.0)
    assert "evidence-1" in result.belief.hypotheses[0].evidence_refs


def test_world_model_predicts_without_mutating_input_state():
    from planning.models import StateSnapshot
    from planning.world_model import RuleBasedWorldModel, TransitionRule, WorldState

    snapshot = StateSnapshot(
        "subject", "generic", 1, "2026-11-20T00:00:00Z"
    )
    state = WorldState.from_snapshot(
        snapshot, values={"status": "idle"}
    )
    model = RuleBasedWorldModel(
        [TransitionRule(
            rule_id="start-rule",
            action="start",
            preconditions={"status": "idle"},
            effects={"status": "running"},
            uncertainty=0.1,
        )]
    )
    prediction = model.predict(state, "start")
    assert prediction.applicable
    assert prediction.predicted_state.values["status"] == "running"
    assert state.values["status"] == "idle"
    assert prediction.predicted_state.revision == 2


def test_metacognition_rejects_unverified_outcomes():
    from planning.metacognition import (
        MetaCognitiveState, OutcomeEvidence, record_verified_outcome,
    )

    evidence = OutcomeEvidence(
        evidence_id="unverified-1",
        strategy_id="strategy-a",
        expected_utility=1.0,
        observed_utility=0.5,
        verified=False,
    )
    result = record_verified_outcome(MetaCognitiveState(), evidence)
    assert not result.accepted
    assert result.state == MetaCognitiveState()
    assert result.reason == "evidence_not_verified"