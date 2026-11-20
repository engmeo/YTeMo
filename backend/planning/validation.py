"""Deterministic structural and policy validation for proposed plans."""
from __future__ import annotations
from dataclasses import dataclass
from .contracts import DomainPolicy
from .models import Plan, PlanStatus, StepRisk

@dataclass(frozen=True)
class PlanningPolicy:
    max_steps: int = 100
    require_human_approval_for_high_risk: bool = True
    require_human_approval_for_critical_risk: bool = True

@dataclass(frozen=True)
class PlanValidationIssue:
    code: str
    message: str
    step_id: str | None = None
    severity: str = "error"

@dataclass(frozen=True)
class PlanValidationResult:
    valid: bool
    issues: tuple[PlanValidationIssue, ...]
    topological_order: tuple[str, ...]
    @property
    def blocking_issues(self):
        return tuple(x for x in self.issues if x.severity == "error")

def validate_plan(plan: Plan, policy: PlanningPolicy | None = None, domain_policy: DomainPolicy | None = None) -> PlanValidationResult:
    policy = policy or PlanningPolicy()
    if isinstance(policy.max_steps, bool) or not isinstance(policy.max_steps, int) or policy.max_steps < 0:
        raise ValueError("PlanningPolicy.max_steps must be a non-negative integer.")
    issues = []
    steps = plan.steps
    ids = [x.step_id for x in steps]
    if domain_policy is not None and domain_policy.domain_id.casefold() != plan.domain.casefold():
        issues.append(PlanValidationIssue("domain_policy_mismatch", f"Domain policy {domain_policy.domain_id!r} does not match plan domain {plan.domain!r}."))
        domain_policy = None
    if len(steps) > policy.max_steps:
        issues.append(PlanValidationIssue("max_steps_exceeded", f"Plan has {len(steps)} steps; policy allows {policy.max_steps}."))
    if len(ids) != len(set(ids)):
        issues.append(PlanValidationIssue("duplicate_step_id", "Step ids must be unique."))
    known = set(ids)
    graph = {}
    for step in steps:
        if step.step_id in graph: continue
        unknown = [d for d in step.depends_on if d not in known]
        if unknown:
            issues.append(PlanValidationIssue("unknown_dependency", f"Unknown dependencies: {', '.join(unknown)}.", step.step_id))
        if step.step_id in step.depends_on:
            issues.append(PlanValidationIssue("self_dependency", "A step cannot depend on itself.", step.step_id))
        graph[step.step_id] = tuple(d for d in step.depends_on if d in known)
        universal_gate = ((step.risk == StepRisk.HIGH and policy.require_human_approval_for_high_risk) or (step.risk == StepRisk.CRITICAL and policy.require_human_approval_for_critical_risk))
        domain_gate = domain_policy is not None and step.risk in domain_policy.required_human_approval_risks
        if (universal_gate or domain_gate) and not step.requires_human_approval:
            issues.append(PlanValidationIssue("human_approval_required", "This risk level requires explicit human approval.", step.step_id))
        if domain_policy is not None and step.risk in domain_policy.required_evidence_risks and not step.evidence_refs:
            issues.append(PlanValidationIssue("domain_evidence_required", f"Domain {domain_policy.domain_id!r} requires evidence references for this risk level.", step.step_id))
    indegree = {n: len(ds) for n, ds in graph.items()}
    dependents = {n: [] for n in graph}
    for n, deps in graph.items():
        for d in deps: dependents[d].append(n)
    ready = sorted(n for n, degree in indegree.items() if degree == 0)
    order = []
    while ready:
        node = ready.pop(0); order.append(node)
        for child in sorted(dependents[node]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child); ready.sort()
    if len(order) != len(graph):
        issues.append(PlanValidationIssue("dependency_cycle", "Plan dependency graph contains a cycle."))
    errors = any(x.severity == "error" for x in issues)
    return PlanValidationResult(not errors, tuple(issues), tuple(order) if not errors else ())

def mark_validated(plan: Plan, policy: PlanningPolicy | None = None, domain_policy: DomainPolicy | None = None) -> Plan:
    from dataclasses import replace
    result = validate_plan(plan, policy, domain_policy)
    if not result.valid:
        details = "; ".join(f"{x.code}: {x.message}" for x in result.blocking_issues)
        raise ValueError(f"Plan validation failed: {details}")
    return replace(plan, status=PlanStatus.VALIDATED)
