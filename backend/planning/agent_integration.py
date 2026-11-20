"""Safe proposal-only boundary between Planning and agent runtimes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class AgentStepRequest:
    step_id: str
    agent_role: str
    instruction: str
    inputs: Mapping[str, object]
    requires_human_approval: bool = False

    def __post_init__(self) -> None:
        for name in ("step_id", "agent_role", "instruction"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.inputs, Mapping):
            raise ValueError("inputs must be a mapping")
        if not isinstance(self.requires_human_approval, bool):
            raise ValueError("requires_human_approval must be boolean")
        object.__setattr__(self, "inputs", dict(self.inputs))


@dataclass(frozen=True)
class AgentHandoffProposal:
    plan_id: str
    domain: str
    requests: tuple[AgentStepRequest, ...]
    status: str = "proposal_only"
    execution_authorized: bool = False


def build_agent_handoff(
    *,
    plan_id: str,
    domain: str,
    steps: Iterable[AgentStepRequest],
) -> AgentHandoffProposal:
    if not isinstance(plan_id, str) or not plan_id.strip():
        raise ValueError("plan_id must be a non-empty string")
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("domain must be a non-empty string")
    requests = tuple(steps)
    if not requests or any(not isinstance(s, AgentStepRequest) for s in requests):
        raise ValueError("steps must contain at least one AgentStepRequest")
    if len({s.step_id for s in requests}) != len(requests):
        raise ValueError("step IDs must be unique")
    return AgentHandoffProposal(plan_id, domain, requests)
