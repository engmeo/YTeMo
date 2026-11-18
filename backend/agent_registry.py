"""Explicit registry for Y TE MO specialist agents and review teams.

This module wires implementations into the existing framework-neutral
agent_foundation. It does not create LLM agents, access patient data, or make
clinical decisions. Register only implementations that have been reviewed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from agent_foundation import (
    CriticAgent,
    MultiAgentWorkflow,
    SpecialistAgent,
    SpecialistRunner,
    WorkflowStep,
)


@dataclass(frozen=True)
class AgentProfile:
    key: str
    specialist: SpecialistAgent
    critics: tuple[CriticAgent, ...]
    max_attempts: int = 3
    required_critic_names: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if not self.key or not self.key.strip():
            raise ValueError("Agent profile key must not be empty.")
        if not self.critics:
            raise ValueError("Every specialist profile must have at least one critic.")
        if self.max_attempts < 1 or self.max_attempts > 10:
            raise ValueError("max_attempts must be between 1 and 10.")
        names = [critic.name for critic in self.critics]
        if len(names) != len(set(names)):
            raise ValueError("Critic names must be unique within a profile.")
        required = self.required_critic_names or tuple(names)
        if not set(required).issubset(set(names)):
            raise ValueError("A required critic is not included in this profile.")
        object.__setattr__(self, "required_critic_names", tuple(required))


class AgentRegistry:
    """Stores approved profiles and assembles bounded sequential workflows."""

    def __init__(self) -> None:
        self._profiles: dict[str, AgentProfile] = {}

    def register(self, profile: AgentProfile) -> None:
        if profile.key in self._profiles:
            raise ValueError(f"Agent profile already registered: {profile.key}")
        if not profile.specialist.name:
            raise ValueError("Specialist must have a non-empty name.")
        self._profiles[profile.key] = profile

    def get(self, key: str) -> AgentProfile:
        try:
            return self._profiles[key]
        except KeyError as exc:
            raise KeyError(f"Unknown agent profile: {key}") from exc

    def keys(self) -> tuple[str, ...]:
        return tuple(self._profiles.keys())

    def build_runner(self, key: str) -> SpecialistRunner:
        profile = self.get(key)
        return SpecialistRunner(
            specialist=profile.specialist,
            critics=profile.critics,
            max_attempts=profile.max_attempts,
            required_critic_names=profile.required_critic_names,
        )

    def build_workflow(self, ordered_profile_keys: Sequence[str]) -> MultiAgentWorkflow:
        if not ordered_profile_keys:
            raise ValueError("At least one profile is required to build a workflow.")
        if len(ordered_profile_keys) != len(set(ordered_profile_keys)):
            raise ValueError("A profile cannot appear more than once in a workflow.")
        steps = [
            WorkflowStep(key=key, runner=self.build_runner(key))
            for key in ordered_profile_keys
        ]
        return MultiAgentWorkflow(steps)
