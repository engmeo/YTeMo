"""Generate draft instruction/response examples from structured, reviewed claims.

This is a template-based draft generator. Outputs are explicitly DRAFT and
cannot enter the SFT dataset until a clinician/editor approves them and a
privacy reviewer marks the record safe. It never reads raw patient records.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_examples(claim: dict) -> list[dict]:
    required = ("claim_id", "claim_summary", "evidence_state", "source_id", "source_url", "license")
    missing = [field for field in required if not claim.get(field)]
    if missing:
        raise ValueError(f"Missing claim fields: {', '.join(missing)}")
    state = claim["evidence_state"]
    if state not in {"STRONG", "WEAK", "CONFLICTING", "INSUFFICIENT"}:
        raise ValueError("Invalid evidence_state.")

    source_label = claim.get("source_title") or claim["source_id"]
    locator = claim.get("page_or_locator") or "vị trí trích dẫn cần xác minh"
    summary = claim["claim_summary"]
    scope = claim.get("population") or "quần thể nghiên cứu được nêu trong nguồn"

    if state == "STRONG":
        response = (
            f"Nguồn {source_label} ghi nhận: {summary} "
            f"Đây là thông tin được phân loại STRONG trong bộ dữ liệu nội bộ, "
            f"nhưng chỉ áp dụng trong phạm vi {scope}. Không thể tự động kết luận "
            f"rằng kết quả phù hợp với mọi cá nhân; cần đối chiếu bệnh nền, thuốc, "
            f"triệu chứng và hoàn cảnh cụ thể. Nguồn/vị trí: {claim['source_url']} ({locator})."
        )
    elif state == "WEAK":
        response = (
            f"Nguồn {source_label} nêu: {summary} "
            f"Bằng chứng hiện được phân loại WEAK, vì vậy đây là thông tin còn hạn chế "
            f"và không đủ để khẳng định quan hệ nhân quả hoặc tự đưa ra quyết định điều trị. "
            f"Cần thêm nghiên cứu và đánh giá theo bối cảnh {scope}. "
            f"Nguồn/vị trí: {claim['source_url']} ({locator})."
        )
    elif state == "CONFLICTING":
        response = (
            f"Các nguồn hiện có đang có kết quả hoặc khuyến nghị không thống nhất về nội dung: {summary} "
            f"Không nên chọn một phía như kết luận chắc chắn. Cần so sánh quần thể, phương pháp, "
            f"thời điểm, kết cục và chất lượng từng nguồn; nếu đây là quyết định chăm sóc cá nhân, "
            f"hãy trao đổi với nhân viên y tế. Nguồn tham chiếu: {claim['source_url']} ({locator})."
        )
    else:
        response = (
            f"Thông tin hiện có chưa đủ để kết luận về nội dung: {summary} "
            f"Cần làm rõ thêm câu hỏi, thời gian diễn biến, bệnh nền, thuốc đang dùng "
            f"và dữ liệu liên quan trước khi đưa ra nhận định. Không nên suy đoán khi thiếu dữ kiện. "
            f"Nguồn tham chiếu: {claim['source_url']} ({locator})."
        )

    instructions = [
        f"Giải thích cho người bệnh thông tin sau và nêu rõ mức độ bằng chứng: {summary}",
        f"Người bệnh hỏi liệu thông tin này có chắc chắn áp dụng cho họ không: {summary}",
    ]
    rows = []
    for index, instruction in enumerate(instructions, start=1):
        rows.append({
            "instruction": instruction,
            "input": f"Phạm vi nguồn: {scope}. Trạng thái bằng chứng: {state}.",
            "response": response,
            "evidence_state": state,
            "evidence_summary": summary,
            "source_id": claim["source_id"],
            "source_url": claim["source_url"],
            "license": claim["license"],
            "license_url": claim.get("license_url"),
            "source_version": claim.get("source_version"),
            "source_hash": claim.get("source_hash"),
            "clinical_review_status": "DRAFT",
            "clinical_review_id": None,
            "reviewer_count": 0,
            "privacy_reviewed": False,
            "source_verified": bool(claim.get("source_verified", False)),
            "contains_patient_data": False,
            "draft_id": f"{claim['claim_id']}-SFT-{index}",
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSONL of structured claims with source provenance")
    parser.add_argument("--output", default="artifacts/clinical_sft_drafts.jsonl")
    args = parser.parse_args()
    rows = []
    for line_number, line in enumerate(Path(args.input).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.extend(build_examples(json.loads(line)))
        except Exception as exc:
            raise SystemExit(f"Line {line_number}: {exc}") from exc
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"draft_examples": len(rows), "status": "DRAFT_REQUIRES_CLINICAL_AND_PRIVACY_REVIEW"}))


if __name__ == "__main__":
    main()
