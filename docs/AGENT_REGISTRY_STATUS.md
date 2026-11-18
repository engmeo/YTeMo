# Agent Registry — implementation status

## Implemented

- Explicit registration of specialist profiles.
- Every profile must include at least one critic.
- Unique profile keys and critic names are enforced.
- Required critics must be present in the profile.
- A profile can create a bounded `SpecialistRunner`.
- An ordered list of profiles can create a sequential `MultiAgentWorkflow`.
- Existing fail-closed workflow behavior is reused: downstream profiles only receive
  outputs from earlier steps that reached `VERIFIED`.

## Not implemented

- No real healthcare specialist or critic implementation is included.
- No Gemini calls, Supabase writes, patient-data access, external research, diagnosis,
  prescribing, or clinical decision-making.
- No integration into `agent.py`, `main.py`, or `agent_core.py`.
- No claim of clinical verification or production readiness.

## Tests

Run from the backend directory:

```powershell
python -m unittest -v test_agent_registry
```

The tests use deterministic fake agents and reviewers. They verify registry wiring,
not medical correctness.
