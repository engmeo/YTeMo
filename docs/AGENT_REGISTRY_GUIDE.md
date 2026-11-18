# How to use the Agent Registry

The registry is a wiring layer. It does not create agents automatically.

A developer must implement a specialist with `execute(task, previous_feedback)`
and one or more critics with `review(task, result)`, then explicitly register them.

Example (illustrative test-style wiring only):

```python
registry = AgentRegistry()
registry.register(
    AgentProfile(
        key="care_access_intake",
        specialist=my_intake_agent,
        critics=(evidence_critic, safety_critic),
        max_attempts=3,
        required_critic_names=("evidence_critic", "safety_critic"),
    )
)
workflow = registry.build_workflow(("care_access_intake",))
report = workflow.run(task)
```

Do not mark a result as clinically correct merely because the orchestration status is
`VERIFIED`. That status means only that every configured required reviewer returned
`APPROVE` for this run. Reviewer independence, evidence quality, and clinical governance
must be validated separately.

Keep high-risk clinical outputs behind qualified human review.
