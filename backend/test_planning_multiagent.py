import pytest

from planning.multiagent import (
    AgentBid,
    AgentDescriptor,
    AllocationStatus,
    ConflictKind,
    CoordinationTask,
    MultiAgentPolicy,
    allocate_tasks,
)


def agent(agent_id, capabilities=("python",), limit=5, enabled=True):
    return AgentDescriptor(agent_id, capabilities, limit, enabled)


def task(task_id, capabilities=("python",), dependencies=(), priority=1.0, approval=False):
    return CoordinationTask(
        task_id,
        capabilities,
        dependencies,
        priority,
        approval,
    )


def bid(agent_id, task_id, cost=1, duration=1, confidence=0.9, **kwargs):
    return AgentBid(
        agent_id,
        task_id,
        cost,
        duration,
        confidence,
        **kwargs,
    )


def test_assigns_task_to_capable_agent():
    result = allocate_tasks(
        [agent("a1", ("python",)), agent("a2", ("java",))],
        [task("t1", ("python",))],
        [bid("a1", "t1"), bid("a2", "t1")],
    )
    assert result.status == AllocationStatus.COMPLETE
    assert result.assignments[0].agent_id == "a1"


def test_selects_lower_scoring_bid():
    result = allocate_tasks(
        [agent("a1"), agent("a2")],
        [task("t1")],
        [
            bid("a1", "t1", cost=10),
            bid("a2", "t1", cost=2),
        ],
        MultiAgentPolicy(
            cost_weight=1,
            duration_weight=0,
            confidence_weight=0,
            priority_weight=0,
            load_balance_weight=0,
        ),
    )
    assert result.assignments[0].agent_id == "a2"


def test_safety_ineligible_bid_is_rejected():
    result = allocate_tasks(
        [agent("unsafe"), agent("safe")],
        [task("t1")],
        [
            bid("unsafe", "t1", safety_eligible=False),
            bid("safe", "t1"),
        ],
    )
    assert result.assignments[0].agent_id == "safe"
    rejected = next(x for x in result.trace.bid_assessments if x.agent_id == "unsafe")
    assert not rejected.eligible
    assert "excluded_by_external_safety_gate" in rejected.reasons


def test_disabled_agent_cannot_receive_assignment():
    result = allocate_tasks(
        [agent("off", enabled=False)],
        [task("t1")],
        [bid("off", "t1")],
    )
    assert result.status == AllocationStatus.PARTIAL
    assert not result.assignments


def test_agent_assignment_limit_is_enforced():
    result = allocate_tasks(
        [agent("a1", limit=1)],
        [task("t1"), task("t2")],
        [bid("a1", "t1"), bid("a1", "t2")],
    )
    assert len(result.assignments) == 1
    assert len(result.unassigned_task_ids) == 1
    assert any(
        "agent_assignment_capacity_exceeded" in item.reasons
        for item in result.trace.bid_assessments
    )


def test_global_resource_capacity_is_enforced():
    result = allocate_tasks(
        [agent("a1"), agent("a2")],
        [task("t1"), task("t2")],
        [
            bid("a1", "t1", resource_usage=(("gpu", 4),)),
            bid("a2", "t2", resource_usage=(("gpu", 4),)),
        ],
        MultiAgentPolicy(resource_capacities=(("gpu", 6),)),
    )
    assert len(result.assignments) == 1
    assert len(result.unassigned_task_ids) == 1


def test_dependency_order_is_preserved():
    result = allocate_tasks(
        [agent("a1"), agent("a2")],
        [task("t2", dependencies=("t1",)), task("t1")],
        [bid("a1", "t1"), bid("a2", "t2")],
    )
    assert result.trace.allocation_order == ("t1", "t2")
    assert [x.task_id for x in result.assignments] == ["t1", "t2"]


def test_dependent_task_is_blocked_when_dependency_unassigned():
    result = allocate_tasks(
        [agent("a1", capabilities=("python",))],
        [
            task("t1", capabilities=("rust",)),
            task("t2", dependencies=("t1",)),
        ],
        [bid("a1", "t1"), bid("a1", "t2")],
    )
    assert result.unassigned_task_ids == ("t1", "t2")
    assert any(
        item.kind == ConflictKind.DEPENDENCY_UNASSIGNED
        for item in result.conflicts
    )


def test_unknown_dependency_is_rejected():
    with pytest.raises(ValueError):
        allocate_tasks(
            [agent("a1")],
            [task("t1", dependencies=("missing",))],
            [],
        )


def test_dependency_cycle_is_rejected():
    with pytest.raises(ValueError):
        allocate_tasks(
            [agent("a1")],
            [
                task("t1", dependencies=("t2",)),
                task("t2", dependencies=("t1",)),
            ],
            [],
        )


def test_duplicate_task_ids_are_rejected():
    with pytest.raises(ValueError):
        allocate_tasks(
            [agent("a1")],
            [task("t1"), task("t1")],
            [],
        )


def test_duplicate_agent_ids_are_rejected():
    with pytest.raises(ValueError):
        allocate_tasks(
            [agent("a1"), agent("a1")],
            [task("t1")],
            [],
        )


def test_duplicate_bids_are_rejected():
    with pytest.raises(ValueError):
        allocate_tasks(
            [agent("a1")],
            [task("t1")],
            [bid("a1", "t1"), bid("a1", "t1")],
        )


def test_unknown_agent_in_bid_is_rejected():
    with pytest.raises(ValueError):
        allocate_tasks(
            [agent("a1")],
            [task("t1")],
            [bid("missing", "t1")],
        )


def test_unknown_task_in_bid_is_rejected():
    with pytest.raises(ValueError):
        allocate_tasks(
            [agent("a1")],
            [task("t1")],
            [bid("a1", "missing")],
        )


def test_partial_allocation_is_reported():
    result = allocate_tasks(
        [agent("a1")],
        [task("t1"), task("t2")],
        [bid("a1", "t1")],
        MultiAgentPolicy(allow_partial_allocation=True),
    )
    assert result.status == AllocationStatus.PARTIAL
    assert result.unassigned_task_ids == ("t2",)


def test_atomic_allocation_returns_no_assignments_if_incomplete():
    result = allocate_tasks(
        [agent("a1")],
        [task("t1"), task("t2")],
        [bid("a1", "t1")],
        MultiAgentPolicy(allow_partial_allocation=False),
    )
    assert result.status == AllocationStatus.NO_FEASIBLE_ASSIGNMENT
    assert result.assignments == ()
    assert result.unassigned_task_ids == ("t2",)


def test_human_approval_is_propagated():
    result = allocate_tasks(
        [agent("a1")],
        [task("t1", approval=True)],
        [bid("a1", "t1")],
    )
    assert result.status == AllocationStatus.HUMAN_REVIEW
    assert result.assignments[0].requires_human_approval


def test_bid_can_independently_require_human_approval():
    result = allocate_tasks(
        [agent("a1")],
        [task("t1")],
        [bid("a1", "t1", requires_human_approval=True)],
    )
    assert result.status == AllocationStatus.HUMAN_REVIEW


def test_trace_records_policy_and_allocation_order():
    result = allocate_tasks(
        [agent("a1")],
        [task("t1")],
        [bid("a1", "t1")],
        MultiAgentPolicy(policy_version="policy-v2"),
    )
    assert result.trace.policy_version == "policy-v2"
    assert result.trace.allocation_order == ("t1",)
    assert len(result.trace.bid_assessments) == 1


def test_load_balancing_penalizes_already_assigned_agent():
    result = allocate_tasks(
        [agent("a1"), agent("a2")],
        [task("t1"), task("t2")],
        [
            bid("a1", "t1"), bid("a2", "t1"),
            bid("a1", "t2"), bid("a2", "t2"),
        ],
        MultiAgentPolicy(
            cost_weight=0,
            duration_weight=0,
            confidence_weight=0,
            priority_weight=0,
            load_balance_weight=10,
        ),
    )
    assert len(result.assignments) == 2
    assert result.assignments[0].agent_id != result.assignments[1].agent_id


def test_task_priority_influences_score():
    result = allocate_tasks(
        [agent("a1")],
        [task("low", priority=0), task("high", priority=10)],
        [bid("a1", "low"), bid("a1", "high")],
        MultiAgentPolicy(
            cost_weight=0,
            duration_weight=0,
            confidence_weight=0,
            priority_weight=1,
            load_balance_weight=0,
        ),
    )
    scores = {x.task_id: x.score for x in result.assignments}
    assert scores["high"] < scores["low"]


def test_invalid_confidence_is_rejected():
    with pytest.raises(ValueError):
        bid("a1", "t1", confidence=1.5)


def test_negative_resource_usage_is_rejected():
    with pytest.raises(ValueError):
        bid("a1", "t1", resource_usage=(("gpu", -1),))


def test_policy_resource_capacities_must_be_unique():
    with pytest.raises(ValueError):
        MultiAgentPolicy(resource_capacities=(("gpu", 1), ("gpu", 2)))


def test_empty_bids_produce_explicit_conflict():
    result = allocate_tasks(
        [agent("a1")],
        [task("t1")],
        [],
    )
    assert result.status == AllocationStatus.PARTIAL
    assert result.conflicts[0].kind == ConflictKind.NO_ELIGIBLE_BID
