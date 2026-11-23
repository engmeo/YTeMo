"""Evidence-grounded healthcare document specialists and bounded orchestrator.

These specialists extract facts explicitly present in supplied text. They do
not diagnose, prescribe, estimate unprovided prices, or determine BHYT benefits.
"""
from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import re
import uuid
from typing import Any, Sequence

from agent_foundation import (
    AgentResult, AgentTask, CriticFeedback, CriticVerdict,
    WorkflowStatus, result_to_dict,
)
from agent_registry import AgentProfile, AgentRegistry

DEFAULT_AGENT_KEYS = ("cost", "medication", "lab", "bhyt")


def _lines(text: str) -> list[tuple[int, str]]:
    return [(i, line.strip()) for i, line in enumerate(text.splitlines(), 1) if line.strip()]


def _currency_value(raw: str, unit: str) -> int | None:
    cleaned = raw.replace(" ", "")
    # In Vietnamese invoices, dot/comma commonly separate thousands.
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", cleaned):
        cleaned = cleaned.replace(".", "").replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    multiplier = 1_000_000 if unit.lower() == "triệu" else 1_000 if unit.lower() in {"nghìn", "ngàn"} else 1
    return int(value * multiplier)


class _BaseSpecialist:
    name = "BaseSpecialist"
    def execute(self, task: AgentTask, previous_feedback: Sequence[CriticFeedback]) -> AgentResult:
        raise NotImplementedError

    @staticmethod
    def text(task: AgentTask) -> str:
        value = task.context.get("document_text", "")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("document_text is required")
        return value

    @staticmethod
    def result(name: str, findings: list[dict[str, Any]], missing: list[str], output: dict[str, Any]) -> AgentResult:
        return AgentResult(
            agent_name=name,
            status="extracted" if findings else "no_matching_information",
            findings=findings,
            evidence=[{"line": x["line"], "quote": x["source_quote"]} for x in findings],
            missing_information=missing,
            output={
                **output,
                "clinical_recommendations": [],
                "disclaimer": "Chỉ trích xuất thông tin xuất hiện trong tài liệu; không phải kết luận y khoa.",
            },
        )


class CostIntelligenceAgent(_BaseSpecialist):
    name = "CostIntelligenceAgent"
    pattern = re.compile(r"(?P<amount>\d[\d., ]{0,15})\s*(?P<unit>triệu|nghìn|ngàn|đồng|vnđ|vnd|đ|₫)(?=$|[\s,.;:)])", re.I)

    def execute(self, task, previous_feedback):
        text = self.text(task)
        findings = []
        for line_no, line in _lines(text):
            for match in self.pattern.finditer(line):
                raw = match.group("amount").strip()
                unit = match.group("unit")
                amount = _currency_value(raw, unit)
                if amount is None:
                    continue
                findings.append({
                    "category": "document_amount",
                    "amount_raw": match.group(0),
                    "amount_vnd": amount,
                    "context": line[:500],
                    "line": line_no,
                    "source_quote": line[:500],
                })
        missing = [] if findings else ["Không tìm thấy khoản tiền có đơn vị rõ ràng trong tài liệu."]
        return self.result(self.name, findings, missing, {
            "items": findings,
            "total_extracted_amount_vnd": sum(x["amount_vnd"] for x in findings),
            "total_is_not_a_bill_estimate": True,
        })


class MedicationSupportAgent(_BaseSpecialist):
    name = "MedicationSupportAgent"
    dose = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|g|ml|mL|iu|đvqt)\b", re.I)
    cues = re.compile(r"thuốc|viên|ống|uống|tiêm|sáng|trưa|chiều|tối|lần/ngày|lần mỗi ngày", re.I)

    def execute(self, task, previous_feedback):
        findings = []
        for line_no, line in _lines(self.text(task)):
            doses = self.dose.findall(line)
            if doses or self.cues.search(line):
                findings.append({
                    "category": "medication_mention",
                    "raw_text": line[:700],
                    "dose_mentions": doses,
                    "line": line_no,
                    "source_quote": line[:700],
                })
        missing = [] if findings else ["Không tìm thấy dòng thông tin thuốc/liều dùng trong tài liệu."]
        return self.result(self.name, findings, missing, {
            "items": findings,
            "interpretation": "none",
            "prescription_changes": "not_supported",
        })


class LabResultAgent(_BaseSpecialist):
    name = "LabResultAgent"
    markers = re.compile(
        r"hba1c|glucose|gluco|đường huyết|cholesterol|triglycerid|creatinin|creatinine|"
        r"ure\b|urê|ast\b|alt\b|sgot|sgpt|wbc|rbc|hgb|hemoglobin|hemoglobin|"
        r"tiểu cầu|platelet|crp\b|tsh\b|ft4\b|ft3\b|bilirubin|albumin|eGFR",
        re.I,
    )
    numeric = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:mg/dl|mmol/l|µmol/l|umol/l|g/l|u/l|iu/l|%|10\^\d+/l)?", re.I)

    def execute(self, task, previous_feedback):
        findings = []
        for line_no, line in _lines(self.text(task)):
            if not self.markers.search(line):
                continue
            values = self.numeric.findall(line)
            findings.append({
                "category": "lab_result_mention",
                "raw_text": line[:700],
                "numeric_mentions": values,
                "line": line_no,
                "source_quote": line[:700],
                "clinical_interpretation": None,
            })
        missing = [] if findings else ["Không tìm thấy chỉ số xét nghiệm nhận diện được trong tài liệu."]
        return self.result(self.name, findings, missing, {
            "items": findings,
            "interpretation": "none",
            "reference_range_validation": "not_performed",
        })


class BHYTSupportAgent(_BaseSpecialist):
    name = "BHYTSupportAgent"
    markers = re.compile(
        r"bhyt|bảo hiểm y tế|mức hưởng|đúng tuyến|trái tuyến|mã thẻ|"
        r"nơi đăng ký khám chữa bệnh|thời hạn thẻ|giấy chuyển tuyến",
        re.I,
    )
    card_code = re.compile(r"(?i)(mã\s*thẻ\s*(?:bhyt)?\s*[:：]?\s*)[A-Z]{2,3}\d{2,3}\d{5,10}")

    def execute(self, task, previous_feedback):
        findings = []
        for line_no, line in _lines(self.text(task)):
            if not self.markers.search(line):
                continue
            safe_line = self.card_code.sub(r"\1[ĐÃ ẨN MÃ THẺ]", line)
            findings.append({
                "category": "bhyt_information_mention",
                "raw_text": safe_line[:700],
                "line": line_no,
                "source_quote": safe_line[:700],
            })
        missing = [] if findings else ["Không tìm thấy thông tin BHYT trong tài liệu."]
        return self.result(self.name, findings, missing, {
            "items": findings,
            "benefit_eligibility": "not_determined",
            "coverage_rate": "not_inferred",
            "official_verification_required": True,
        })


class EvidenceTraceCritic:
    name = "EvidenceTraceCritic"
    def review(self, task: AgentTask, result: AgentResult) -> CriticFeedback:
        source_lines = str(task.context.get("document_text", "")).splitlines()
        for finding in result.findings:
            line_number = finding.get("line")
            quote = finding.get("source_quote")
            if not quote or not isinstance(line_number, int) or not (1 <= line_number <= len(source_lines)):
                return CriticFeedback(self.name, CriticVerdict.REVISE,
                                      issues=("Mỗi phát hiện phải có trích dẫn nguồn và số dòng hợp lệ.",))
            original_line = source_lines[line_number - 1].strip()
            # BHYT output masks a possible card number; all other text must be
            # traceable to the original line before masking.
            if quote not in original_line and "[ĐÃ ẨN MÃ THẺ]" not in quote:
                return CriticFeedback(self.name, CriticVerdict.REVISE,
                                      evidence_concerns=("Trích dẫn không khớp dòng nguồn.",))
        return CriticFeedback(self.name, CriticVerdict.APPROVE,
                              rationale="Mọi phát hiện đều truy vết được về dòng nguồn.")


class SafetyBoundaryCritic:
    name = "SafetyBoundaryCritic"
    def review(self, task: AgentTask, result: AgentResult) -> CriticFeedback:
        recommendations = result.output.get("clinical_recommendations", [])
        if recommendations:
            return CriticFeedback(self.name, CriticVerdict.BLOCK,
                                  issues=("Không cho phép tạo khuyến nghị lâm sàng trong bước trích xuất.",))
        return CriticFeedback(self.name, CriticVerdict.APPROVE,
                              rationale="Đầu ra chỉ trích xuất; không chẩn đoán/kê đơn.")


class HealthcareAgentService:
    """Registers the four domain agents and orchestrates them through AgentRegistry."""
    def __init__(self):
        self.registry = AgentRegistry()
        profiles = (
            ("cost", CostIntelligenceAgent()),
            ("medication", MedicationSupportAgent()),
            ("lab", LabResultAgent()),
            ("bhyt", BHYTSupportAgent()),
        )
        for key, specialist in profiles:
            # Each profile gets independent critic instances to keep execution isolated.
            self.registry.register(AgentProfile(
                key=key,
                specialist=specialist,
                critics=(EvidenceTraceCritic(), SafetyBoundaryCritic()),
                max_attempts=2,
            ))

    def list_agents(self) -> list[dict[str, str]]:
        return [
            {"key": "cost", "name": "Cost Intelligence Agent", "purpose": "Trích xuất khoản tiền đã ghi trong hồ sơ; không ước tính giá."},
            {"key": "medication", "name": "Medication Support Agent", "purpose": "Trích xuất dòng thuốc/liều dùng; không thay đổi đơn."},
            {"key": "lab", "name": "Lab Result Agent", "purpose": "Trích xuất chỉ số xét nghiệm; không diễn giải chẩn đoán."},
            {"key": "bhyt", "name": "BHYT Support Agent", "purpose": "Trích xuất thông tin BHYT; không xác định quyền lợi thay cơ quan BHYT."},
        ]

    def route_agents(self, document_text: str) -> dict[str, Any]:
        """Select relevant specialists from explicit document signals, not diagnosis."""
        selected: list[str] = []
        reasons: dict[str, str] = {}
        if CostIntelligenceAgent.pattern.search(document_text):
            selected.append("cost")
            reasons["cost"] = "Tìm thấy số tiền kèm đơn vị tiền tệ."
        if MedicationSupportAgent.dose.search(document_text) or MedicationSupportAgent.cues.search(document_text):
            selected.append("medication")
            reasons["medication"] = "Tìm thấy từ khóa thuốc hoặc hàm lượng/lịch dùng."
        if LabResultAgent.markers.search(document_text):
            selected.append("lab")
            reasons["lab"] = "Tìm thấy tên chỉ số xét nghiệm đã nhận diện."
        if BHYTSupportAgent.markers.search(document_text):
            selected.append("bhyt")
            reasons["bhyt"] = "Tìm thấy từ khóa bảo hiểm y tế."
        if not selected:
            selected = list(DEFAULT_AGENT_KEYS)
            reasons = {key: "Không đủ tín hiệu để định tuyến; chạy toàn bộ Agent để không bỏ sót nhóm thông tin." for key in selected}
        return {"mode": "automatic", "agent_keys": selected, "reasons": reasons}

    def run(self, document_text: str, agent_keys: Sequence[str] | None = None) -> dict[str, Any]:
        if not isinstance(document_text, str) or not document_text.strip():
            raise ValueError("document_text không được để trống.")
        if len(document_text) > 200_000:
            raise ValueError("document_text vượt giới hạn 200.000 ký tự.")
        routing = self.route_agents(document_text) if agent_keys is None else {
            "mode": "explicit", "agent_keys": list(agent_keys),
            "reasons": {key: "Được Frontend/người dùng chọn tường minh." for key in agent_keys},
        }
        keys = tuple(routing["agent_keys"])
        if not keys or len(keys) != len(set(keys)):
            raise ValueError("agent_keys phải có ít nhất một Agent và không được trùng.")
        unknown = set(keys) - set(self.registry.keys())
        if unknown:
            raise ValueError(f"Agent không được đăng ký: {', '.join(sorted(unknown))}")
        task = AgentTask(
            task_id=str(uuid.uuid4()),
            goal="Trích xuất thông tin có bằng chứng từ hồ sơ y tế do người dùng cung cấp.",
            context={"document_text": document_text},
        )
        report = self.registry.build_workflow(keys).run(task)
        step_reports = {
            key: result_to_dict(step_report)
            for key, step_report in report.step_reports.items()
        }
        return {
            "task_id": task.task_id,
            "status": report.status.value,
            "stopped_at": report.stopped_at,
            "routing": routing,
            "agents_requested": list(keys),
            "agents_completed": list(report.outputs.keys()),
            "step_reports": step_reports,
            "results": {
                key: result_to_dict(report.step_reports[key])["result"]
                for key in report.outputs
            },
            "limitations": [
                "Chỉ trích xuất thông tin xuất hiện trong văn bản nguồn.",
                "Không chẩn đoán, kê đơn, đánh giá phác đồ hoặc đề xuất thay đổi điều trị.",
                "Không ước tính giá thiếu nguồn và không tự xác định mức hưởng BHYT.",
                "Kết quả cần người dùng/chuyên gia đối chiếu với hồ sơ gốc.",
            ],
        }


# --- YTEMO_HEALTHCARE_ORCHESTRATION_INTEGRATION_V2 ---
def _ytemo_attach_orchestration(self):
    try:
        from .healthcare_orchestration_bridge import attach_orchestration
    except ImportError:
        from healthcare_orchestration_bridge import attach_orchestration
    return attach_orchestration(self)
if "HealthcareAgentService" in globals() and not hasattr(HealthcareAgentService,"attach_orchestration"):
    HealthcareAgentService.attach_orchestration=_ytemo_attach_orchestration
