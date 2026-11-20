from __future__ import annotations

import ast
from pathlib import Path

from planning.pipeline_contracts import PipelineStage
from planning.pipeline_engine import PipelineEngine


REPO_ROOT = Path(__file__).resolve().parents[1]
PLANNING_DIR = REPO_ROOT / "backend" / "planning"


def test_pipeline_registry_covers_all_stages_in_canonical_order():
    engine = PipelineEngine()
    expected = tuple(PipelineStage)

    assert len(expected) == 13
    assert engine.ORDER == expected
    assert engine.registry.stages == expected
    assert all(engine.registry.supports(stage) for stage in expected)


def test_planning_pipeline_does_not_execute_external_actions():
    source = (PLANNING_DIR / "pipeline_engine.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_calls = {
        "mark_step_started",
        "record_step_success",
        "record_step_failure",
        "execute_action",
        "execute_tool",
    }
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else (
                node.func.attr if isinstance(node.func, ast.Attribute) else ""
            )
            if name in forbidden_calls:
                found.append(name)

    assert not found, (
        "Planning pipeline crossed the execution boundary: "
        + ", ".join(sorted(set(found)))
    )


def test_domain_neutral_planning_modules_do_not_import_domain_plugins():
    forbidden_tokens = ("healthcare", "robotics")
    violations = []

    for path in PLANNING_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue

            for name in names:
                lowered = name.casefold()
                if any(token in lowered for token in forbidden_tokens):
                    violations.append(f"{path.name}: {name}")

    assert not violations, (
        "Domain-specific imports found in domain-neutral Planning core: "
        + "; ".join(violations)
    )
