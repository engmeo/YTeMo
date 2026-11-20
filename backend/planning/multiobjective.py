"""Domain-neutral multi-objective optimization.

Provides constraint-aware Pareto sorting, epsilon dominance and
crowding-distance ranking. Existing optimization/search APIs remain intact.
"""
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Mapping, Sequence


class ObjectiveDirection(str, Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


@dataclass(frozen=True)
class ObjectiveSpec:
    name: str
    direction: ObjectiveDirection = ObjectiveDirection.MINIMIZE

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("objective name must be non-empty")
        if not isinstance(self.direction, ObjectiveDirection):
            raise TypeError("direction must be an ObjectiveDirection")


@dataclass(frozen=True)
class ConstraintSpec:
    name: str
    maximum_violation: float = 0.0

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("constraint name must be non-empty")
        if (
            isinstance(self.maximum_violation, bool)
            or not isinstance(self.maximum_violation, (int, float))
            or not isfinite(self.maximum_violation)
            or self.maximum_violation < 0
        ):
            raise ValueError("maximum_violation must be finite and non-negative")


@dataclass(frozen=True)
class MultiObjectiveCandidate:
    candidate_id: str
    objectives: Mapping[str, float]
    constraint_violations: Mapping[str, float] | None = None
    metadata: Mapping[str, object] | None = None

    def __post_init__(self):
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise ValueError("candidate_id must be non-empty")

        if not isinstance(self.objectives, Mapping) or not self.objectives:
            raise ValueError("objectives must be a non-empty mapping")

        object.__setattr__(
            self, "objectives", MappingProxyType(dict(self.objectives))
        )
        violations = dict(self.constraint_violations or {})
        for name, value in violations.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("constraint names must be non-empty strings")
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value < 0
            ):
                raise ValueError(
                    f"constraint violation {name} must be finite and non-negative"
                )

        object.__setattr__(
            self,
            "constraint_violations",
            MappingProxyType(violations),
        )
        object.__setattr__(
            self, "metadata", MappingProxyType(dict(self.metadata or {}))
        )


@dataclass(frozen=True)
class MultiObjectivePolicy:
    epsilon: float = 0.0

    def __post_init__(self):
        if (
            isinstance(self.epsilon, bool)
            or not isinstance(self.epsilon, (int, float))
            or not isfinite(self.epsilon)
            or self.epsilon < 0
        ):
            raise ValueError("epsilon must be finite and non-negative")


@dataclass(frozen=True)
class MultiObjectiveEvaluation:
    candidate_id: str
    pareto_rank: int
    crowding_distance: float
    feasible: bool
    total_constraint_violation: float


@dataclass(frozen=True)
class MultiObjectiveResult:
    fronts: tuple[tuple[str, ...], ...]
    pareto_front: tuple[str, ...]
    ranked_candidate_ids: tuple[str, ...]
    feasible_candidate_ids: tuple[str, ...]
    evaluations: tuple[MultiObjectiveEvaluation, ...]

    @property
    def has_feasible_candidates(self) -> bool:
        return bool(self.feasible_candidate_ids)


def _validate_inputs(
    candidates: Sequence[MultiObjectiveCandidate],
    objectives: Sequence[ObjectiveSpec],
    constraints: Sequence[ConstraintSpec],
):
    if not candidates:
        raise ValueError("at least one candidate is required")
    if not objectives:
        raise ValueError("at least one objective is required")

    candidate_ids = [item.candidate_id for item in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("candidate_id values must be unique")

    objective_names = [item.name for item in objectives]
    if len(objective_names) != len(set(objective_names)):
        raise ValueError("objective names must be unique")

    constraint_names = [item.name for item in constraints]
    if len(constraint_names) != len(set(constraint_names)):
        raise ValueError("constraint names must be unique")

    expected_objectives = set(objective_names)
    expected_constraints = set(constraint_names)

    for candidate in candidates:
        if not isinstance(candidate, MultiObjectiveCandidate):
            raise TypeError("all candidates must be MultiObjectiveCandidate")

        if set(candidate.objectives) != expected_objectives:
            raise ValueError(
                f"{candidate.candidate_id}: objective keys must exactly match specifications"
            )

        if not set(candidate.constraint_violations).issubset(expected_constraints):
            raise ValueError(
                f"{candidate.candidate_id}: unknown constraint supplied"
            )

        for name, value in candidate.objectives.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
            ):
                raise ValueError(
                    f"{candidate.candidate_id}: objective {name} must be finite"
                )

        for name, value in candidate.constraint_violations.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value < 0
            ):
                raise ValueError(
                    f"{candidate.candidate_id}: constraint {name} must be finite and non-negative"
                )


def _constraint_total(
    candidate: MultiObjectiveCandidate,
    constraints: Sequence[ConstraintSpec],
) -> float:
    return sum(
        max(
            0.0,
            float(candidate.constraint_violations.get(item.name, 0.0))
            - item.maximum_violation,
        )
        for item in constraints
    )


def _objective_dominates(
    left: MultiObjectiveCandidate,
    right: MultiObjectiveCandidate,
    objectives: Sequence[ObjectiveSpec],
    epsilon: float,
) -> bool:
    strictly_better = False

    for spec in objectives:
        a = float(left.objectives[spec.name])
        b = float(right.objectives[spec.name])

        if spec.direction is ObjectiveDirection.MINIMIZE:
            if a > b + epsilon:
                return False
            if a < b - epsilon:
                strictly_better = True
        else:
            if a < b - epsilon:
                return False
            if a > b + epsilon:
                strictly_better = True

    return strictly_better


def _dominates(
    left: MultiObjectiveCandidate,
    right: MultiObjectiveCandidate,
    objectives: Sequence[ObjectiveSpec],
    constraints: Sequence[ConstraintSpec],
    epsilon: float,
) -> bool:
    left_violation = _constraint_total(left, constraints)
    right_violation = _constraint_total(right, constraints)

    left_feasible = left_violation == 0
    right_feasible = right_violation == 0

    if left_feasible and not right_feasible:
        return True
    if right_feasible and not left_feasible:
        return False

    if not left_feasible and not right_feasible:
        if left_violation < right_violation - epsilon:
            return True
        if right_violation < left_violation - epsilon:
            return False

    return _objective_dominates(left, right, objectives, epsilon)


def _non_dominated_sort(
    candidates,
    objectives,
    constraints,
    epsilon,
):
    dominates_map = {}
    dominated_count = {}

    for candidate in candidates:
        candidate_id = candidate.candidate_id
        dominates_map[candidate_id] = []
        dominated_count[candidate_id] = 0

    by_id = {item.candidate_id: item for item in candidates}

    for index, left in enumerate(candidates):
        for right in candidates[index + 1:]:
            if _dominates(left, right, objectives, constraints, epsilon):
                dominates_map[left.candidate_id].append(right.candidate_id)
                dominated_count[right.candidate_id] += 1
            elif _dominates(right, left, objectives, constraints, epsilon):
                dominates_map[right.candidate_id].append(left.candidate_id)
                dominated_count[left.candidate_id] += 1

    current = sorted(
        candidate_id
        for candidate_id, count in dominated_count.items()
        if count == 0
    )
    fronts = []

    while current:
        fronts.append(tuple(current))
        following = []

        for candidate_id in current:
            for dominated_id in dominates_map[candidate_id]:
                dominated_count[dominated_id] -= 1
                if dominated_count[dominated_id] == 0:
                    following.append(dominated_id)

        current = sorted(following)

    if sum(len(front) for front in fronts) != len(candidates):
        raise RuntimeError("non-dominated sorting failed to rank every candidate")

    return tuple(fronts), by_id


def _crowding_distances(front, by_id, objectives):
    distances = {candidate_id: 0.0 for candidate_id in front}

    if len(front) <= 2:
        return {candidate_id: float("inf") for candidate_id in front}

    for spec in objectives:
        ordered = sorted(
            front,
            key=lambda candidate_id: (
                float(by_id[candidate_id].objectives[spec.name]),
                candidate_id,
            ),
        )

        distances[ordered[0]] = float("inf")
        distances[ordered[-1]] = float("inf")

        minimum = float(by_id[ordered[0]].objectives[spec.name])
        maximum = float(by_id[ordered[-1]].objectives[spec.name])
        span = maximum - minimum

        if span == 0:
            continue

        for index in range(1, len(ordered) - 1):
            candidate_id = ordered[index]
            if distances[candidate_id] == float("inf"):
                continue

            previous_value = float(
                by_id[ordered[index - 1]].objectives[spec.name]
            )
            next_value = float(
                by_id[ordered[index + 1]].objectives[spec.name]
            )
            distances[candidate_id] += (next_value - previous_value) / span

    return distances


def optimize_multiobjective(
    candidates: Sequence[MultiObjectiveCandidate],
    objectives: Sequence[ObjectiveSpec],
    constraints: Sequence[ConstraintSpec] = (),
    policy: MultiObjectivePolicy | None = None,
) -> MultiObjectiveResult:
    """Rank candidates using constraint-aware Pareto fronts and crowding distance.

    This function does not collapse a Pareto frontier into one arbitrary winner.
    """
    candidates = tuple(candidates)
    objectives = tuple(objectives)
    constraints = tuple(constraints)
    policy = policy or MultiObjectivePolicy()

    if not isinstance(policy, MultiObjectivePolicy):
        raise TypeError("policy must be a MultiObjectivePolicy")

    _validate_inputs(candidates, objectives, constraints)

    fronts, by_id = _non_dominated_sort(
        candidates, objectives, constraints, policy.epsilon
    )

    evaluations_by_id = {}
    ranked = []

    for rank, front in enumerate(fronts):
        distances = _crowding_distances(front, by_id, objectives)

        for candidate_id in front:
            candidate = by_id[candidate_id]
            violation = _constraint_total(candidate, constraints)

            evaluations_by_id[candidate_id] = MultiObjectiveEvaluation(
                candidate_id=candidate_id,
                pareto_rank=rank,
                crowding_distance=distances[candidate_id],
                feasible=(violation == 0),
                total_constraint_violation=violation,
            )

        ranked.extend(
            sorted(
                front,
                key=lambda candidate_id: (
                    -distances[candidate_id],
                    _constraint_total(by_id[candidate_id], constraints),
                    candidate_id,
                ),
            )
        )

    evaluations = tuple(
        evaluations_by_id[candidate.candidate_id]
        for candidate in candidates
    )

    feasible_ids = tuple(
        candidate.candidate_id
        for candidate in candidates
        if _constraint_total(candidate, constraints) == 0
    )

    return MultiObjectiveResult(
        fronts=fronts,
        pareto_front=fronts[0],
        ranked_candidate_ids=tuple(ranked),
        feasible_candidate_ids=feasible_ids,
        evaluations=evaluations,
    )

