import ast
import importlib
from pathlib import Path

import pytest

import planning


PLANNING_DIR = Path(__file__).parent / "planning"

FORBIDDEN_IMPORT_ROOTS = {
    "fastapi",
    "supabase",
    "healthcare",
    "robotics",
    "finance",
    "agentcore",
}


def test_all_planning_modules_compile():
    files = list(PLANNING_DIR.glob("*.py"))
    assert files
    for path in files:
        source = path.read_text(encoding="utf-8-sig")
        compile(source, str(path), "exec")


def test_all_planning_modules_are_importable():
    files = [
        path for path in PLANNING_DIR.glob("*.py")
        if path.name != "__init__.py"
    ]
    assert files

    for path in files:
        importlib.import_module(f"planning.{path.stem}")


def test_public_all_contains_no_duplicate_names():
    exports = getattr(planning, "__all__", None)
    assert isinstance(exports, (list, tuple))
    assert len(exports) == len(set(exports))


def test_every_public_export_resolves():
    for name in planning.__all__:
        assert hasattr(planning, name), f"Missing public export: {name}"


def test_phase_1_to_8_public_api_is_present():
    required = {
        # Phase 1
        "PlanningOrchestrator",
        "PlannerStrategy",
        "PlanningResult",
        # Phase 2
        "WorldState",
        "TransitionRule",
        "RuleBasedWorldModel",
        "WorldPrediction",
        # Phase 3
        "HierarchicalPlanner",
        "HierarchicalMethod",
        "hierarchical_result_to_plan",
        # Phase 4
        "DecisionCandidate",
        "DecisionPolicy",
        "select_decision",
        # Phase 5
        "MultiObjectiveCandidate",
        "MultiObjectivePolicy",
        "optimize_multiobjective",
        # Phase 6
        "ExecutionSnapshot",
        "ExecutionFeedback",
        "evaluate_recovery",
        # Phase 7
        "MetaCognitiveState",
        "MetaPolicy",
        "record_verified_outcome",
        "select_strategy",
        # Phase 8
        "AgentDescriptor",
        "CoordinationTask",
        "MultiAgentPolicy",
        "allocate_tasks",
    }
    missing = sorted(name for name in required if not hasattr(planning, name))
    assert not missing, f"Missing phase exports: {missing}"


def test_core_has_no_forbidden_domain_imports():
    violations = []

    for path in PLANNING_DIR.glob("*.py"):
        tree = ast.parse(
            path.read_text(encoding="utf-8-sig"),
            filename=str(path),
        )

        for node in ast.walk(tree):
            imported_roots = []

            if isinstance(node, ast.Import):
                imported_roots.extend(
                    alias.name.split(".")[0].lower()
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.append(node.module.split(".")[0].lower())

            for root in imported_roots:
                if root in FORBIDDEN_IMPORT_ROOTS:
                    violations.append(f"{path.name}: {root}")

    assert not violations, (
        "Domain/application dependency found in Planning core: "
        + "; ".join(violations)
    )


def test_meta_cognition_and_multiagent_contracts_compose():
    state = planning.MetaCognitiveState()

    evidence = planning.OutcomeEvidence(
        evidence_id="phase9-evidence-001",
        strategy_id="planner-alpha",
        expected_utility=8.0,
        observed_utility=9.0,
        verified=True,
        resource_cost=2.0,
        latency_ms=100.0,
    )

    update = planning.record_verified_outcome(state, evidence)
    assert update.accepted

    decision = planning.select_strategy(
        [
            planning.StrategyCandidate(
                "planner-alpha",
                estimated_cost=2.0,
                estimated_latency_ms=100.0,
            )
        ],
        update.state,
    )
    assert decision.selected_strategy_id == "planner-alpha"

    allocation = planning.allocate_tasks(
        agents=[
            planning.AgentDescriptor(
                agent_id="agent-a",
                capabilities=("planning",),
            )
        ],
        tasks=[
            planning.CoordinationTask(
                task_id="task-a",
                required_capabilities=("planning",),
            )
        ],
        bids=[
            planning.AgentBid(
                agent_id="agent-a",
                task_id="task-a",
                estimated_cost=1.0,
                estimated_duration=2.0,
                confidence=0.95,
            )
        ],
    )

    assert allocation.status == planning.AllocationStatus.COMPLETE
    assert allocation.assignments[0].agent_id == "agent-a"


def test_meta_learning_rejects_unverified_evidence():
    state = planning.MetaCognitiveState()
    evidence = planning.OutcomeEvidence(
        evidence_id="phase9-unverified",
        strategy_id="planner-alpha",
        expected_utility=5.0,
        observed_utility=10.0,
        verified=False,
    )

    result = planning.record_verified_outcome(state, evidence)
    assert not result.accepted
    assert result.state == state


def test_multiagent_dependency_and_capacity_contracts():
    result = planning.allocate_tasks(
        agents=[
            planning.AgentDescriptor(
                "agent-a",
                capabilities=("planning",),
                max_assigned_tasks=2,
            )
        ],
        tasks=[
            planning.CoordinationTask("task-b", dependencies=("task-a",)),
            planning.CoordinationTask("task-a"),
        ],
        bids=[
            planning.AgentBid("agent-a", "task-a", 1, 1, 0.9),
            planning.AgentBid("agent-a", "task-b", 1, 1, 0.9),
        ],
    )

    assert result.status == planning.AllocationStatus.COMPLETE
    assert [item.task_id for item in result.assignments] == [
        "task-a",
        "task-b",
    ]


def test_meta_policy_is_immutable():
    policy = planning.MetaPolicy()
    with pytest.raises((AttributeError, TypeError)):
        policy.max_resource_cost = 999


def test_multiagent_policy_is_immutable():
    policy = planning.MultiAgentPolicy()
    with pytest.raises((AttributeError, TypeError)):
        policy.cost_weight = 999


def test_planning_core_does_not_import_application_entrypoint():
    violations = []

    for path in PLANNING_DIR.glob("*.py"):
        tree = ast.parse(
            path.read_text(encoding="utf-8-sig"),
            filename=str(path),
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0].lower()
                    if root in {"main", "backend", "app"}:
                        violations.append(f"{path.name}: {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0].lower()
                if root in {"main", "backend", "app"}:
                    violations.append(f"{path.name}: {node.module}")

    assert not violations, "; ".join(violations)
