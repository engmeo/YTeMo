[CmdletBinding()]
param([string]$ProjectRoot = "C:\YTeMo")

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$backend = Join-Path $root "backend"
if (-not (Test-Path (Join-Path $backend "main.py"))) { throw "Cannot find backend\main.py under $root" }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $root ".stt18_addon_backup_$stamp"
New-Item -ItemType Directory -Path $backup | Out-Null

# Additive-only policy: never overwrite an existing file; never edit main.py,
# AgentCore, AgentRegistry, healthcare_specialists.py, migrations, or .env files.
$modulePath = Join-Path $backend "healthcare_orchestration_extension.py"
$testPath = Join-Path $backend "test_healthcare_orchestration_extension.py"
$created = New-Object System.Collections.Generic.List[string]
$skipped = New-Object System.Collections.Generic.List[string]

$module = @'
"""Additive healthcare orchestration layer.

This module does not replace AgentCore, AgentRegistry, or existing specialist
implementations. Applications inject approved specialist callables explicitly.
It performs deterministic routing only; it does not make clinical decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class OrchestrationPlan:
    intent: str
    specialist_keys: tuple[str, ...]
    requires_human_review: bool
    reason: str


@dataclass
class OrchestrationResult:
    status: str
    plan: OrchestrationPlan
    specialist_results: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    safety_flags: list[str] = field(default_factory=list)
    next_action: str = "review"
    disclaimer: str = (
        "Thong tin ho tro tham khao; khong thay the chan doan, ke don "
        "hoac quyet dinh cua nhan vien y te."
    )


class HealthcareOrchestrator:
    """Small, deterministic coordinator around already-approved specialists."""

    ROUTES = {
        "cost": ("cost_intelligence",),
        "medication": ("medication_support",),
        "lab": ("lab_result",),
        "bhyt": ("bhyt_support",),
        "comprehensive": (
            "cost_intelligence", "medication_support", "lab_result", "bhyt_support"
        ),
    }

    HIGH_RISK_TERMS = (
         "cap cuu", "khong tho duoc", "dau nguc", "dot quy",
        "tu sat", "qua lieu", "sốc phản vệ", "suy ho hap",
        "chest pain", "shortness of breath", "stroke", "overdose",
    )

    def __init__(
        self,
        specialists: Mapping[str, Callable[[Mapping[str, Any]], Any]],
        *,
        allowed_specialists: Sequence[str] | None = None,
    ) -> None:
        self._specialists = dict(specialists)
        self._allowed = set(allowed_specialists or self.ROUTES["comprehensive"])
        unknown = self._allowed.difference(self._specialists)
        if unknown:
            raise ValueError("Allowed specialists are not registered: " + ", ".join(sorted(unknown)))

    @classmethod
    def plan(cls, request: Mapping[str, Any]) -> OrchestrationPlan:
        text = " ".join(
            str(request.get(k, "")) for k in ("intent", "question", "document_type", "task")
        ).lower()
        explicit = str(request.get("intent", "")).strip().lower()
        if any(term in text for term in cls.HIGH_RISK_TERMS):
            return OrchestrationPlan(
                "urgent_safety", (), True,
                "Phat hien dau hieu co the nguy cap; dung dieu phoi tu dong va chuyen nguoi that."
            )
        if explicit in cls.ROUTES:
            intent = explicit
        elif any(x in text for x in ("thuoc", "don thuoc", "lieu dung", "medication")):
            intent = "medication"
        elif any(x in text for x in ("xet nghiem", "chi so", "lab", "ket qua")):
            intent = "lab"
        elif any(x in text for x in ("bhyt", "bao hiem y te", "quyen loi")):
            intent = "bhyt"
        elif any(x in text for x in ("chi phi", "vien phi", "gia tien", "cost")):
            intent = "cost"
        else:
            intent = "comprehensive"
        return OrchestrationPlan(
            intent, cls.ROUTES[intent], False,
            "Chon specialist theo intent; khong tu suy dien chan doan."
        )

    def run(self, request: Mapping[str, Any]) -> OrchestrationResult:
        plan = self.plan(request)
        if plan.requires_human_review:
            return OrchestrationResult(
                "needs_human_review", plan,
                safety_flags=["possible_urgent_condition"],
                next_action="contact_local_emergency_services_or_qualified_clinician",
            )

        results: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for key in plan.specialist_keys:
            if key not in self._allowed or key not in self._specialists:
                errors[key] = "Specialist is not approved or not registered."
                continue
            try:
                # Only caller-provided, consent-filtered request context is passed through.
                output = self._specialists[key](dict(request))
                results[key] = output
            except Exception as exc:
                # Avoid returning exception text that may contain patient data or secrets.
                errors[key] = type(exc).__name__

        if errors:
            status, action = "partial_or_failed", "human_review_required"
        elif not results:
            status, action = "not_executed", "human_review_required"
        else:
            status, action = "completed_for_review", "review_evidence_and_human_approval"

        return OrchestrationResult(
            status, plan, results, errors,
            safety_flags=["clinical_decision_not_performed"],
            next_action=action,
        )
'@

$tests = @'
from healthcare_orchestration_extension import HealthcareOrchestrator


def test_routes_medication_request():
    called = []
    service = HealthcareOrchestrator({
        "medication_support": lambda ctx: called.append("medication") or {"ok": True}
    }, allowed_specialists=["medication_support"])
    result = service.run({"question": "Can you review my medication list?"})
    assert result.status == "completed_for_review"
    assert called == ["medication"]


def test_urgent_signal_stops_automatic_execution():
    called = []
    service = HealthcareOrchestrator({
        "medication_support": lambda ctx: called.append("called")
    }, allowed_specialists=["medication_support"])
    result = service.run({"question": "I have chest pain"})
    assert result.status == "needs_human_review"
    assert called == []


def test_failure_is_reported_without_exception_text():
    def fail(_):
        raise RuntimeError("private detail")
    service = HealthcareOrchestrator(
        {"cost_intelligence": fail}, allowed_specialists=["cost_intelligence"]
    )
    result = service.run({"intent": "cost"})
    assert result.status == "partial_or_failed"
    assert result.errors == {"cost_intelligence": "RuntimeError"}
    assert "private detail" not in str(result.errors)


def test_comprehensive_route_uses_only_registered_allowed_agents():
    called = []
    service = HealthcareOrchestrator({
        key: (lambda ctx, k=key: called.append(k) or {"agent": k})
        for key in ("cost_intelligence", "medication_support", "lab_result", "bhyt_support")
    })
    result = service.run({"intent": "comprehensive"})
    assert result.status == "completed_for_review"
    assert set(called) == {
        "cost_intelligence", "medication_support", "lab_result", "bhyt_support"
    }
'@

try {
    if (Test-Path -LiteralPath $modulePath) {
        $skipped.Add("backend\healthcare_orchestration_extension.py (already exists; not overwritten)")
    } else {
        [System.IO.File]::WriteAllText($modulePath, $module, (New-Object System.Text.UTF8Encoding($false)))
        $created.Add("backend\healthcare_orchestration_extension.py")
    }

    if (Test-Path -LiteralPath $testPath) {
        $skipped.Add("backend\test_healthcare_orchestration_extension.py (already exists; not overwritten)")
    } else {
        [System.IO.File]::WriteAllText($testPath, $tests, (New-Object System.Text.UTF8Encoding($false)))
        $created.Add("backend\test_healthcare_orchestration_extension.py")
    }

    $python = Join-Path $backend ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $python = (Get-Command python -ErrorAction Stop).Source
    }

    Push-Location $backend
    try {
        & $python -m py_compile healthcare_orchestration_extension.py test_healthcare_orchestration_extension.py
        if ($LASTEXITCODE -ne 0) { throw "Python compile failed. New files are preserved for inspection." }
        & $python -m pytest -q test_healthcare_orchestration_extension.py
        if ($LASTEXITCODE -ne 0) { throw "STT18 add-on tests failed. Existing project files were not modified." }
    } finally {
        Pop-Location
    }

    $report = Join-Path $root "STT18_ADDON_REPORT.txt"
    @(
        "STT18 ADDITIVE ORCHESTRATION ADD-ON",
        "Timestamp: $(Get-Date -Format o)",
        "Project: $root",
        "",
        "Created:", ($created | ForEach-Object { " - $_" }),
        "",
        "Skipped:", ($skipped | ForEach-Object { " - $_" }),
        "",
        "Backup directory: $backup",
        "Existing files modified: NO",
        "AgentCore/AgentRegistry/main.py modified: NO",
        "Migrations/.env/credentials touched: NO",
        "Commit/push/deploy performed: NO",
        "Scope: additive orchestration module and isolated tests only.",
        "Integration note: inject existing approved specialist callables from the current application; this script intentionally does not rewrite API routes or replace existing orchestration."
    ) | Set-Content -LiteralPath $report -Encoding UTF8

    Write-Host ""
    Write-Host "STT18 ADDITIVE ADD-ON: PASS" -ForegroundColor Green
    Write-Host "Created: $($created -join ', ')"
    Write-Host "Skipped: $($skipped -join ', ')"
    Write-Host "Report: $report"
    Write-Host "No existing source files were overwritten."
}
catch {
    Write-Host "STT18 ADDITIVE ADD-ON: FAIL" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    throw
}
