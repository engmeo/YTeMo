# Y TẾ MỞ — Agent Contract

Every Agent added to the platform must document the following contract before it is enabled in a workflow.

## Required declaration

| Field | Requirement |
|---|---|
| `name` | Stable unique Agent name |
| `version` | Explicit version |
| `responsibility` | One bounded responsibility |
| `input_schema` | Required and optional input fields |
| `output_schema` | Structured result fields |
| `allowed_tools` | Explicit allowlist; default deny |
| `evaluation_criteria` | Testable completion criteria |
| `required_critics` | Named independent reviewers |
| `safety_constraints` | Prohibited actions and risk boundaries |
| `escalation_rules` | Conditions requiring human review |
| `max_attempts` | Bounded revision count |

## Output requirements

A specialist result should distinguish:

- Findings
- Evidence and source provenance
- Assumptions
- Missing information
- Risk flags
- Proposed output
- Revision number

## Review requirements

A critic must return one of:

- `approve`: within its review scope, no blocking issue found.
- `revise`: specific fixable issue(s) identified.
- `block`: unsafe, prohibited, or fundamentally invalid result.
- `human_review`: requires qualified human judgment.

A critic must provide its name and rationale. Reviewers must not claim expertise or source verification they do not possess.

## Completion

An Agent is complete only when its required critics approve, or when the workflow explicitly exits into a non-success state. A timeout, missing reviewer, invalid result, or exhausted retry budget must never be silently treated as approval.
