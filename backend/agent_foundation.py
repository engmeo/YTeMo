"""Framework-neutral foundation for Y TE MO's iterative multi-agent workflows.

This module provides orchestration mechanics only. It does not make clinical
decisions, verify medical truth by itself, call an LLM, or access patient data.
Concrete agents and independent reviewers must be explicitly registered by the
application and validated for their intended use.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Protocol, Sequence


class WorkflowStatus(str, Enum):
    VERIFIED = "verified"
    REVISION_REQUIRED = "revision_required"
    BLOCKED = "blocked"
    HUMAN_REVIEW = "human_review"
    FAILED = "failed"


class CriticVerdict(str, Enum):
    APPROVE = "approve"
    REVISE = "revise"
    BLOCK = "block"
    HUMAN_REVIEW = "human_review"


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    goal: str
    context: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    agent_name: str
    status: str
    findings: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    output: dict[str, Any] = field(default_factory=dict)
    revision: int = 1


@dataclass(frozen=True)
class CriticFeedback:
    critic_name: str
    verdict: CriticVerdict
    issues: tuple[str, ...] = ()
    evidence_concerns: tuple[str, ...] = ()
    rationale: str = ""


@dataclass
class AgentRunReport:
    status: WorkflowStatus
    result: AgentResult | None
    feedback_history: list[list[CriticFeedback]] = field(default_factory=list)
    attempts: int = 0
    reason: str = ""


class SpecialistAgent(Protocol):
    name: str

    def execute(self, task: AgentTask, previous_feedback: Sequence[CriticFeedback]) -> AgentResult:
        ...


class CriticAgent(Protocol):
    name: str

    def review(self, task: AgentTask, result: AgentResult) -> CriticFeedback:
        ...


def _validate_result(result: AgentResult, expected_agent: str) -> None:
    if not isinstance(result, AgentResult):
        raise TypeError("Specialist must return an AgentResult.")
    if result.agent_name != expected_agent:
        raise ValueError("AgentResult.agent_name does not match the registered specialist.")
    for name in ("findings", "evidence", "assumptions", "missing_information", "risk_flags"):
        if not isinstance(getattr(result, name), list):
            raise TypeError(f"AgentResult.{name} must be a list.")
    if not isinstance(result.output, dict):
        raise TypeError("AgentResult.output must be a dictionary.")


class SpecialistRunner:
    """Runs one specialist and requires every configured critic to approve.

    This is deterministic orchestration. The quality of the review depends on
    the actual critic implementations, their evidence, and their independence.
    """

    def __init__(
        self,
        specialist: SpecialistAgent,
        critics: Sequence[CriticAgent],
        *,
        max_attempts: int = 3,
        required_critic_names: Sequence[str] | None = None,
    ):
        if max_attempts < 1 or max_attempts > 10:
            raise ValueError("max_attempts must be between 1 and 10.")
        if not critics:
            raise ValueError("At least one independent critic is required.")
        names = [critic.name for critic in critics]
        if len(names) != len(set(names)):
            raise ValueError("Critic names must be unique.")
        self.specialist = specialist
        self.critics = tuple(critics)
        self.max_attempts = max_attempts
        self.required_critic_names = set(required_critic_names or names)
        if not self.required_critic_names.issubset(set(names)):
            raise ValueError("Required critic is not registered.")

    def run(self, task: AgentTask) -> AgentRunReport:
        feedback: list[CriticFeedback] = []
        history: list[list[CriticFeedback]] = []
        latest: AgentResult | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                latest = self.specialist.execute(task, feedback)
                _validate_result(latest, self.specialist.name)
                latest.revision = attempt
                round_feedback = [critic.review(task, latest) for critic in self.critics]
                for critic, item in zip(self.critics, round_feedback):
                    if item.critic_name != critic.name:
                        raise ValueError("CriticFeedback.critic_name does not match reviewer.")
                history.append(round_feedback)

                verdicts = {item.critic_name: item.verdict for item in round_feedback}
                if any(v == CriticVerdict.BLOCK for v in verdicts.values()):
                    return AgentRunReport(
                        WorkflowStatus.BLOCKED, latest, history, attempt,
                        "At least one critic issued a blocking verdict.",
                    )
                if any(v == CriticVerdict.HUMAN_REVIEW for v in verdicts.values()):
                    return AgentRunReport(
                        WorkflowStatus.HUMAN_REVIEW, latest, history, attempt,
                        "At least one critic requires qualified human review.",
                    )

                missing_required = self.required_critic_names - set(verdicts)
                if missing_required:
                    return AgentRunReport(
                        WorkflowStatus.FAILED, latest, history, attempt,
                        f"Missing required critic reviews: {sorted(missing_required)}",
                    )

                required_verdicts = [verdicts[name] for name in self.required_critic_names]
                if all(v == CriticVerdict.APPROVE for v in required_verdicts):
                    return AgentRunReport(
                        WorkflowStatus.VERIFIED, latest, history, attempt,
                        "All required configured critics approved this result.",
                    )

                feedback = round_feedback
            except Exception as exc:
                return AgentRunReport(
                    WorkflowStatus.FAILED, latest, history, attempt,
                    f"Agent workflow error: {type(exc).__name__}: {exc}",
                )

        return AgentRunReport(
            WorkflowStatus.REVISION_REQUIRED, latest, history, self.max_attempts,
            "Maximum revision attempts reached without all required approvals.",
        )


@dataclass(frozen=True)
class WorkflowStep:
    key: str
    runner: SpecialistRunner


@dataclass
class WorkflowReport:
    status: WorkflowStatus
    step_reports: dict[str, AgentRunReport]
    outputs: dict[str, AgentResult]
    stopped_at: str | None = None


class MultiAgentWorkflow:
    """Sequential fail-closed workflow; only VERIFIED steps pass downstream."""

    def __init__(self, steps: Sequence[WorkflowStep]):
        if not steps:
            raise ValueError("Workflow must contain at least one step.")
        keys = [step.key for step in steps]
        if len(keys) != len(set(keys)):
            raise ValueError("Workflow step keys must be unique.")
        self.steps = tuple(steps)

    def run(self, task: AgentTask) -> WorkflowReport:
        reports: dict[str, AgentRunReport] = {}
        outputs: dict[str, AgentResult] = {}

        for step in self.steps:
            step_context = dict(task.context)
            step_context["verified_prior_outputs"] = {
                key: value.output for key, value in outputs.items()
            }
            step_task = AgentTask(task.task_id, task.goal, step_context)
            report = step.runner.run(step_task)
            reports[step.key] = report

            if report.status != WorkflowStatus.VERIFIED or report.result is None:
                return WorkflowReport(report.status, reports, outputs, step.key)

            outputs[step.key] = report.result

        return WorkflowReport(WorkflowStatus.VERIFIED, reports, outputs)


def result_to_dict(report: AgentRunReport) -> dict[str, Any]:
    """Serialize a report into an API/log-friendly plain dictionary."""
    return {
        "status": report.status.value,
        "attempts": report.attempts,
        "reason": report.reason,
        "result": None if report.result is None else {
            "agent_name": report.result.agent_name,
            "status": report.result.status,
            "findings": report.result.findings,
            "evidence": report.result.evidence,
            "assumptions": report.result.assumptions,
            "missing_information": report.result.missing_information,
            "risk_flags": report.result.risk_flags,
            "output": report.result.output,
            "revision": report.result.revision,
        },
        "feedback_history": [
            [
                {
                    "critic_name": item.critic_name,
                    "verdict": item.verdict.value,
                    "issues": list(item.issues),
                    "evidence_concerns": list(item.evidence_concerns),
                    "rationale": item.rationale,
                }
                for item in round_items
            ]
            for round_items in report.feedback_history
        ],
    }
