import pytest

from planning.multiobjective import (
    ConstraintSpec,
    MultiObjectiveCandidate,
    MultiObjectivePolicy,
    ObjectiveDirection,
    ObjectiveSpec,
    optimize_multiobjective,
)


OBJECTIVES = (
    ObjectiveSpec("cost", ObjectiveDirection.MINIMIZE),
    ObjectiveSpec("quality", ObjectiveDirection.MAXIMIZE),
)


def candidate(candidate_id, cost, quality, violations=None):
    return MultiObjectiveCandidate(
        candidate_id=candidate_id,
        objectives={"cost": cost, "quality": quality},
        constraint_violations=violations or {},
    )


def test_pareto_front_excludes_dominated_candidates():
    result = optimize_multiobjective(
        (
            candidate("A", 1, 5),
            candidate("B", 2, 8),
            candidate("C", 3, 4),
            candidate("D", 3, 9),
        ),
        OBJECTIVES,
    )
    assert set(result.pareto_front) == {"A", "B", "D"}
    assert result.has_feasible_candidates


def test_dominated_candidate_is_ranked_in_later_front():
    result = optimize_multiobjective(
        (
            candidate("A", 1, 8),
            candidate("B", 2, 6),
            candidate("C", 3, 4),
        ),
        OBJECTIVES,
    )
    ranks = {item.candidate_id: item.pareto_rank for item in result.evaluations}
    assert ranks["A"] == 0
    assert ranks["B"] == 1
    assert ranks["C"] == 2


def test_constraint_feasibility_has_priority_over_objectives():
    result = optimize_multiobjective(
        (
            candidate("feasible", 100, 1),
            candidate("infeasible", 1, 100, {"safety": 2}),
        ),
        OBJECTIVES,
        constraints=(ConstraintSpec("safety", 0),),
    )
    assert result.pareto_front == ("feasible",)
    assert result.feasible_candidate_ids == ("feasible",)


def test_infeasible_candidates_rank_by_total_violation_first():
    result = optimize_multiobjective(
        (
            candidate("small", 100, 1, {"safety": 1}),
            candidate("large", 1, 100, {"safety": 5}),
        ),
        OBJECTIVES,
        constraints=(ConstraintSpec("safety", 0),),
    )
    assert result.pareto_front == ("small",)
    assert not result.has_feasible_candidates


def test_constraint_tolerance_is_respected():
    result = optimize_multiobjective(
        (candidate("A", 1, 5, {"load": 0.95}),),
        OBJECTIVES,
        constraints=(ConstraintSpec("load", 1.0),),
    )
    assert result.has_feasible_candidates


def test_crowding_distance_preserves_boundary_candidates():
    result = optimize_multiobjective(
        (
            candidate("A", 1, 1),
            candidate("B", 2, 2),
            candidate("C", 3, 3),
            candidate("D", 4, 4),
        ),
        OBJECTIVES,
    )
    evaluations = {item.candidate_id: item for item in result.evaluations}
    assert evaluations["A"].crowding_distance == float("inf")
    assert evaluations["D"].crowding_distance == float("inf")


def test_epsilon_dominance_treats_small_differences_as_equivalent():
    result = optimize_multiobjective(
        (
            candidate("A", 1.0, 5.0),
            candidate("B", 1.01, 4.99),
        ),
        OBJECTIVES,
        policy=MultiObjectivePolicy(epsilon=0.02),
    )
    assert set(result.pareto_front) == {"A", "B"}


def test_maximize_and_minimize_directions_are_respected():
    result = optimize_multiobjective(
        (
            candidate("A", 1, 5),
            candidate("B", 2, 10),
            candidate("C", 3, 4),
        ),
        OBJECTIVES,
    )
    assert set(result.pareto_front) == {"A", "B"}


def test_frontier_does_not_force_a_single_winner():
    result = optimize_multiobjective(
        (
            candidate("low-cost", 1, 5),
            candidate("high-quality", 3, 10),
        ),
        OBJECTIVES,
    )
    assert len(result.pareto_front) == 2


def test_candidate_order_does_not_change_frontier():
    items = (
        candidate("A", 1, 5),
        candidate("B", 2, 8),
        candidate("C", 3, 4),
    )
    first = optimize_multiobjective(items, OBJECTIVES)
    second = optimize_multiobjective(tuple(reversed(items)), OBJECTIVES)
    assert set(first.pareto_front) == set(second.pareto_front)
    assert set(first.ranked_candidate_ids) == set(second.ranked_candidate_ids)


def test_duplicate_candidate_ids_are_rejected():
    with pytest.raises(ValueError):
        optimize_multiobjective(
            (candidate("A", 1, 2), candidate("A", 2, 3)),
            OBJECTIVES,
        )


def test_missing_objective_is_rejected():
    bad = MultiObjectiveCandidate(
        "bad",
        objectives={"cost": 1},
    )
    with pytest.raises(ValueError):
        optimize_multiobjective((bad,), OBJECTIVES)


def test_non_finite_objective_is_rejected():
    bad = MultiObjectiveCandidate(
        "bad",
        objectives={"cost": float("nan"), "quality": 1},
    )
    with pytest.raises(ValueError):
        optimize_multiobjective((bad,), OBJECTIVES)


def test_negative_constraint_violation_is_rejected():
    with pytest.raises(ValueError):
        MultiObjectiveCandidate(
            "bad",
            objectives={"cost": 1, "quality": 2},
            constraint_violations={"safety": -1},
        )


def test_empty_candidate_set_is_rejected():
    with pytest.raises(ValueError):
        optimize_multiobjective((), OBJECTIVES)


def test_duplicate_objective_names_are_rejected():
    with pytest.raises(ValueError):
        optimize_multiobjective(
            (candidate("A", 1, 2),),
            (
                ObjectiveSpec("cost"),
                ObjectiveSpec("cost", ObjectiveDirection.MAXIMIZE),
            ),
        )


def test_invalid_epsilon_is_rejected():
    with pytest.raises(ValueError):
        MultiObjectivePolicy(epsilon=-0.1)


def test_unknown_constraint_is_rejected():
    with pytest.raises(ValueError):
        optimize_multiobjective(
            (candidate("A", 1, 2, {"unknown": 1}),),
            OBJECTIVES,
            constraints=(ConstraintSpec("safety"),),
        )

