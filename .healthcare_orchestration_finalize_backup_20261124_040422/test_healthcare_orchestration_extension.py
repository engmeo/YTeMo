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