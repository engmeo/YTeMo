"""Domain-neutral predictive world model.

This first implementation is an explicit rule-based transition model.
It does not claim to learn dynamics or establish real-world truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .models import StateSnapshot


def _freeze(value: Any) -> Any:
    """Recursively freeze JSON-like values."""
    if isinstance(value, Mapping):
        return MappingProxyType({
            str(key): _freeze(item) for key, item in value.items()
        })
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported world-state value: {type(value).__name__}")


def _freeze_mapping(values: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(values, Mapping):
        raise TypeError("values must be a mapping")
    return MappingProxyType({
        str(key): _freeze(value) for key, value in values.items()
    })


@dataclass(frozen=True)
class WorldState:
    """Immutable, domain-neutral representation of a world state."""

    subject_id: str
    domain: str
    revision: int
    as_of: str
    values: Mapping[str, Any]
    unknowns: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.subject_id or not self.domain:
            raise ValueError("subject_id and domain are required")
        if self.revision < 0:
            raise ValueError("revision cannot be negative")
        object.__setattr__(self, "values", _freeze_mapping(self.values))
        object.__setattr__(self, "unknowns", tuple(self.unknowns))
        object.__setattr__(self, "constraints", tuple(self.constraints))

    @classmethod
    def from_snapshot(
        cls,
        snapshot: StateSnapshot,
        *,
        values: Mapping[str, Any],
    ) -> "WorldState":
        """Convert a snapshot while requiring explicit fact interpretation.

        StateFact semantics are intentionally not guessed by the core.
        The caller supplies normalized key/value state.
        """
        return cls(
            subject_id=snapshot.subject_id,
            domain=snapshot.domain,
            revision=snapshot.revision,
            as_of=snapshot.as_of,
            values=values,
            unknowns=snapshot.unknowns,
            constraints=snapshot.constraints,
        )

    def apply(
        self,
        effects: Mapping[str, Any],
    ) -> "WorldState":
        updated = dict(self.values)
        updated.update(effects)
        return WorldState(
            subject_id=self.subject_id,
            domain=self.domain,
            revision=self.revision + 1,
            as_of=self.as_of,
            values=updated,
            unknowns=self.unknowns,
            constraints=self.constraints,
        )


@dataclass(frozen=True)
class TransitionRule:
    """Explicit action transition rule supplied by a caller."""

    rule_id: str
    action: str
    preconditions: Mapping[str, Any]
    effects: Mapping[str, Any]
    uncertainty: float = 0.0
    version: int = 1

    def __post_init__(self) -> None:
        if not self.rule_id or not self.action:
            raise ValueError("rule_id and action are required")
        if not 0.0 <= self.uncertainty <= 1.0:
            raise ValueError("uncertainty must be between 0 and 1")
        if self.version < 1:
            raise ValueError("rule version must be at least 1")
        object.__setattr__(
            self, "preconditions", _freeze_mapping(self.preconditions)
        )
        object.__setattr__(self, "effects", _freeze_mapping(self.effects))


@dataclass(frozen=True)
class WorldPrediction:
    """Prediction result with explicit applicability and uncertainty."""

    rule_id: str
    rule_version: int
    action: str
    source_revision: int
    applicable: bool
    predicted_state: WorldState | None
    confidence: float
    uncertainty: float
    changed_keys: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PredictionEvaluation:
    """Comparison between predicted changes and a later observation."""

    rule_id: str
    compared_keys: tuple[str, ...]
    matched_keys: tuple[str, ...]
    mismatched_keys: tuple[str, ...]
    missing_keys: tuple[str, ...]
    accuracy: float


class RuleBasedWorldModel:
    """Transparent rule-based transition predictor.

    Rules are generic and injected by the caller. No domain-specific
    assumptions, external calls, or action execution are performed.
    """

    def __init__(self, rules: Sequence[TransitionRule] = ()) -> None:
        self._rules: dict[str, TransitionRule] = {}
        for rule in rules:
            self.register_rule(rule)

    def register_rule(self, rule: TransitionRule) -> None:
        if not isinstance(rule, TransitionRule):
            raise TypeError("rule must be a TransitionRule")
        existing = self._rules.get(rule.action)
        if existing is not None and rule.version <= existing.version:
            raise ValueError(
                "replacement rule must have a strictly higher version"
            )
        self._rules[rule.action] = rule

    @property
    def actions(self) -> tuple[str, ...]:
        return tuple(sorted(self._rules))

    def predict(
        self,
        state: WorldState,
        action: str,
    ) -> WorldPrediction:
        rule = self._rules.get(action)
        if rule is None:
            raise KeyError(f"no transition rule registered for action: {action}")

        reasons: list[str] = []
        for key, expected in rule.preconditions.items():
            if key not in state.values:
                reasons.append(f"unknown precondition: {key}")
            elif state.values[key] != expected:
                reasons.append(f"precondition mismatch: {key}")

        if reasons:
            return WorldPrediction(
                rule_id=rule.rule_id,
                rule_version=rule.version,
                action=action,
                source_revision=state.revision,
                applicable=False,
                predicted_state=None,
                confidence=0.0,
                uncertainty=1.0,
                changed_keys=(),
                reasons=tuple(reasons),
            )

        predicted = state.apply(rule.effects)
        return WorldPrediction(
            rule_id=rule.rule_id,
            rule_version=rule.version,
            action=action,
            source_revision=state.revision,
            applicable=True,
            predicted_state=predicted,
            confidence=1.0 - rule.uncertainty,
            uncertainty=rule.uncertainty,
            changed_keys=tuple(sorted(rule.effects)),
            reasons=(),
        )

    def evaluate(
        self,
        prediction: WorldPrediction,
        observed_state: WorldState,
    ) -> PredictionEvaluation:
        if not prediction.applicable or prediction.predicted_state is None:
            raise ValueError("cannot evaluate an inapplicable prediction")

        expected_state = prediction.predicted_state
        if observed_state.revision < prediction.source_revision + 1:
            raise ValueError(
                "observed state revision is older than the predicted transition"
            )
        if (
            observed_state.subject_id != expected_state.subject_id
            or observed_state.domain != expected_state.domain
        ):
            raise ValueError("observed state belongs to a different subject or domain")

        keys = prediction.changed_keys
        matched: list[str] = []
        mismatched: list[str] = []
        missing: list[str] = []

        for key in keys:
            if key not in observed_state.values:
                missing.append(key)
            elif observed_state.values[key] == expected_state.values.get(key):
                matched.append(key)
            else:
                mismatched.append(key)

        accuracy = len(matched) / len(keys) if keys else 1.0
        return PredictionEvaluation(
            rule_id=prediction.rule_id,
            compared_keys=keys,
            matched_keys=tuple(matched),
            mismatched_keys=tuple(mismatched),
            missing_keys=tuple(missing),
            accuracy=accuracy,
        )
