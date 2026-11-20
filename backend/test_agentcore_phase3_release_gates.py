import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_CORE = ROOT / "backend" / "agent_core.py"
AGENT_TESTS = ROOT / "backend" / "test_agent_core.py"


def _module(path):
    assert path.is_file(), f"Required source file missing: {path}"
    source = path.read_text(encoding="utf-8-sig")
    return source, ast.parse(source, filename=str(path))


def _class_methods(tree, class_name):
    cls = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name),
        None,
    )
    assert cls is not None, f"Class {class_name} not found"
    return {
        node.name: node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _source_segment(source, node):
    return ast.get_source_segment(source, node) or ""


def test_agent_core_owns_execution_lifecycle_api():
    _, tree = _module(AGENT_CORE)
    methods = _class_methods(tree, "AgentCore")
    required = {
        "_claim_task", "_heartbeat", "_update_task", "_run_tool_with_heartbeat",
        "create_task", "get_task", "list_tasks", "run_task",
    }
    assert required.issubset(methods), (
        f"Missing AgentCore lifecycle methods: {sorted(required - set(methods))}"
    )


def test_task_claim_is_conditional_and_supports_expired_lease_reclaim():
    source, tree = _module(AGENT_CORE)
    body = _source_segment(source, _class_methods(tree, "AgentCore")["_claim_task"])
    for token in (
        "lease_token", "queued", "failed", "running", "updated_at",
        "LEASE_MINUTES", ".in_(", ".lt(",
    ):
        assert token in body, f"_claim_task missing claim/reclaim behavior: {token}"


def test_heartbeat_and_updates_are_fenced_by_current_lease_owner():
    source, tree = _module(AGENT_CORE)
    methods = _class_methods(tree, "AgentCore")
    heartbeat = _source_segment(source, methods["_heartbeat"])
    update = _source_segment(source, methods["_update_task"])
    assert ".eq('lease_token', lease_token)" in heartbeat or '.eq("lease_token", lease_token)' in heartbeat
    assert "AgentCoreError" in heartbeat and "not result.data" in heartbeat
    assert ".eq('user_id', user_id)" in update or '.eq("user_id", user_id)' in update
    assert "lease_token" in update and "AgentCoreError" in update


def test_tool_execution_has_periodic_heartbeat_and_rejects_lost_lease():
    source, tree = _module(AGENT_CORE)
    body = _source_segment(source, _class_methods(tree, "AgentCore")["_run_tool_with_heartbeat"])
    for token in (
        "threading.Event", "HEARTBEAT_SECONDS", "threading.Thread",
        "heartbeat_errors", "stop_event.set()", "AgentCoreError",
    ):
        assert token in body, f"Heartbeat execution missing behavior: {token}"


def test_resume_skips_completed_steps_and_persists_step_results():
    source, tree = _module(AGENT_CORE)
    body = _source_segment(source, _class_methods(tree, "AgentCore")["run_task"])
    for token in (
        "agent_task_steps", "completed", "continue", "attempts", "output",
        "step.completed",
    ):
        assert token in body, f"Task resume/persistence behavior missing: {token}"


def test_task_terminal_transitions_are_lease_guarded_and_emit_events():
    source, tree = _module(AGENT_CORE)
    body = _source_segment(source, _class_methods(tree, "AgentCore")["run_task"])
    for token in (
        "task.completed", "task.failed", "status", "completed", "failed",
        "self._update_task", "lease_token",
    ):
        assert token in body, f"Task terminal transition behavior missing: {token}"


def test_agent_core_regression_suite_covers_concurrency_resume_and_heartbeat():
    _, tree = _module(AGENT_TESTS)
    names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    required = {
        "test_two_workers_only_one_can_claim_task",
        "test_running_task_is_not_claimed_again",
        "test_expired_lease_can_be_reclaimed_and_old_worker_is_fenced",
        "test_resume_skips_completed_steps",
        "test_heartbeat_runs_repeatedly_during_tool_execution",
        "test_lost_lease_during_tool_prevents_result_return",
    }
    assert required.issubset(names), (
        f"Missing AgentCore regression cases: {sorted(required - names)}"
    )