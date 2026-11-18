# Y TẾ MỞ — Multi-Agent Architecture

**Status:** Target architecture / foundation proposal  
**Implementation status:** The orchestration primitives in `backend/agent_foundation.py` are an initial framework. They are not yet connected to the production chat endpoint, Gemini, Supabase task persistence, or validated clinical agents.

## 1. Design principles

1. One specialist Agent owns one bounded responsibility.
2. Every Agent has an explicit input/output contract, allowed tools, constraints, and completion criteria.
3. Specialist execution and independent review are separate roles.
4. Required reviewers must approve; there is no majority-vote shortcut for safety-critical findings.
5. A blocked or unresolved result never passes to the next workflow step.
6. Missing information is represented explicitly; Agents must not invent it.
7. Human review is mandatory where clinical judgment, prescribing, diagnosis, or other regulated decisions require it.
8. Every loop has attempt, time, and resource limits.
9. "Verified" means approved by the configured software review gates. It does not mean clinically proven or guaranteed correct.

## 2. High-level architecture

```text
Patient / User
    |
    v
Proactive Intent Discovery
    |
    v
Healthcare Orchestrator
    |
    +--> Patient Journey / Access Agent
    +--> Medical Research Agent
    +--> Diagnostic Information Agent
    +--> Medication Analysis Agent
    +--> Coverage / Benefits Agent
    +--> Price & Cost Intelligence Agent
    +--> Care Coordination Agent
    +--> Continuity & Outcome Agent
    |
    v
Independent Critic Network
    +--> Evidence Critic
    +--> Data Quality Critic
    +--> Safety Critic
    +--> Cost / Coverage Critic
    +--> Clinical Review Router
    |
    v
Safety Gate / Human Review
    |
    v
Response or permitted action
```

The list above is a target network, not a claim that all these agents currently exist.

## 3. Three nested control loops

### 3.1 Specialist Execution Loop

`Understand -> Plan -> Execute -> Self-evaluate -> Revise`

The specialist returns structured findings, evidence, assumptions, missing information, risk flags, and output. Self-evaluation is useful but is not an independent verification.

### 3.2 Cross-Agent Verification Loop

Independent critics review the specialist result. Each critic must stay within its assigned review scope. Required critics must approve. A `REVISE` verdict returns actionable feedback to the specialist. `BLOCK` and `HUMAN_REVIEW` stop automatic progression.

Critics should use independent evidence or methods where possible. Several agents agreeing after reading the same model-generated text is not independent evidence.

### 3.3 Workflow Improvement Loop

The orchestrator detects missing inputs, conflicting results, repeated failures, or changed context. It can request clarification, route to another specialist, pause, or escalate. It must not silently bypass a failed gate.

## 4. Standard Agent Contract

Every production Agent should declare:

- `identity`: stable name and version
- `responsibility`: bounded task
- `input_schema`: required and optional inputs
- `output_schema`: structured result
- `allowed_tools`: explicit tool allowlist
- `evaluation_criteria`: measurable completion checks
- `critic_agents`: required reviewers
- `safety_constraints`: prohibited actions and risk boundaries
- `escalation_rules`: when a human is required
- `completion_criteria`: exact conditions for completion

The initial Python foundation provides task/result/critic data structures and a bounded runner. It does not yet enforce a full declarative registry or JSON Schema validation.

## 5. Workflow states

- `verified`: every configured required critic approved.
- `revision_required`: retry limit reached without all required approvals.
- `blocked`: at least one critic identified a blocking issue.
- `human_review`: a critic requires qualified human review.
- `failed`: runtime, contract, or reviewer error.

These states are workflow control states, not clinical confidence scores.

## 6. Initial reference workflow

The first target workflow is deliberately narrow:

```text
Intent Discovery
    -> Structured Intake
    -> One bounded specialist task
    -> Independent critic review
    -> Revision loop (bounded)
    -> Safety gate
    -> User-facing response
```

A practical first use case is navigation and cost-information support, not autonomous diagnosis or treatment. The system may identify missing information and prepare questions or options. It must not invent current provider prices, insurance eligibility, or clinical recommendations.

## 7. Patient Journey integration

The specialist network will eventually support:

1. Before Care — access and navigation.
2. During Care — coordination and diagnostic-service optimization.
3. Treatment — medication, coverage, supply, procedure, and cost analysis.
4. After Care — continuity, rehabilitation, and outcome monitoring.
5. Long-term Care — prevention and chronic-care support.

The Patient Journey Cost Intelligence System can consume verified outputs from these workflows, while retaining source, time, uncertainty, and provenance for every cost claim.

## 8. Safety and governance

- Do not treat model agreement as proof.
- Do not let an Agent approve its own high-risk output.
- Preserve evidence provenance and timestamps.
- Distinguish user-provided facts, retrieved facts, assumptions, and inferences.
- Do not change prescriptions, doses, diagnoses, or care plans autonomously.
- Escalate emergencies and high-risk cases according to clinically reviewed protocols.
- Use privacy-minimizing, consent-based access to health data.
- Test against representative, de-identified or synthetic cases before real-world use.
- Measure false reassurance, missed escalation, unsupported claims, and workflow failure—not just answer fluency.

## 9. Current implementation boundary

Existing repository components include a FastAPI backend, a LangGraph-based conversational discovery flow, Gemini service integration, and a Supabase-backed task runtime. The new `agent_foundation.py` is intentionally framework-neutral and is not wired into those existing routes yet.

Next engineering steps:

1. Define versioned Agent Contracts and schemas.
2. Add an explicit Agent/Critic registry and tool permission model.
3. Persist workflow runs, attempts, critic feedback, and provenance.
4. Add timeout, cancellation, idempotency, and resource budgets.
5. Integrate the foundation behind a separate feature flag/API path.
6. Add deterministic tests, adversarial tests, and domain-expert-reviewed evaluation sets.
7. Only then connect the first healthcare workflow.

## 10. Non-goal

This architecture does not promise that repeated model calls make an answer "certain". The objective is traceable, bounded, evidence-aware review with explicit uncertainty and safe escalation.
