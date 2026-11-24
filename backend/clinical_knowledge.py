"""Clinical Knowledge governance API.

Automated checks verify provenance metadata and extraction integrity only.
They never certify clinical correctness. Human reviewers control approval.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl, field_validator

ALLOWED_APPROVED_SCOPES = {
    "patient_education", "self_care", "prevention", "screening",
    "diagnostic_reference", "treatment_reference", "medication_safety",
    "professional_decision_support", "public_health",
}

ALLOWED_STATUSES = {
    "DISCOVERED", "SOURCE_VERIFIED", "PROCESSING", "AI_REVIEWED",
    "CLINICAL_APPROVED", "SUPERSEDED", "REJECTED",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def host_is_within(host: str, base_host: str) -> bool:
    host, base_host = host.lower().rstrip("."), base_host.lower().rstrip(".")
    return host == base_host or host.endswith("." + base_host)


def initial_document_status(source_domain_matched: bool, checks_passed: bool) -> str:
    """Domain match and extraction checks never authenticate a clinical document."""
    return "DISCOVERED"


def is_reviewable_status(status: str) -> bool:
    return status in {"DISCOVERED", "SOURCE_VERIFIED", "AI_REVIEWED"}


def reviewer_is_independent(document_creator_id: str | None, reviewer_id: str) -> bool:
    return not document_creator_id or str(document_creator_id) != str(reviewer_id)


def automated_document_checks(metadata: dict, extracted_text: str | None = None) -> dict:
    """Conservative metadata/extraction checks; never a clinical review."""
    issues = []
    for key in ("title", "publisher", "document_type", "source_url", "published_at",
                "knowledge_domain", "jurisdiction", "target_population"):
        if not str(metadata.get(key) or "").strip():
            issues.append(f"MISSING_{key.upper()}")
    source_url = str(metadata.get("source_url") or "")
    if source_url:
        parsed = urlparse(source_url)
        if parsed.scheme != "https" or not parsed.hostname:
            issues.append("SOURCE_URL_NOT_HTTPS")
    if extracted_text is not None:
        if len(extracted_text.strip()) < 200:
            issues.append("TEXT_TOO_SHORT_OR_EXTRACTION_FAILED")
        if "\x00" in extracted_text:
            issues.append("TEXT_CONTAINS_NULL_BYTES")
    return {
        "passed": not issues,
        "issues": issues,
        "checked_at": utc_now(),
        "scope": "metadata_and_extraction_integrity_only",
        "clinical_approval": False,
    }


class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    publisher: str = Field(min_length=2, max_length=300)
    document_type: str = Field(min_length=2, max_length=100)
    source_url: HttpUrl
    published_at: str = Field(min_length=4, max_length=40)
    effective_from: str | None = Field(default=None, max_length=40)
    effective_until: str | None = Field(default=None, max_length=40)
    version: str | None = Field(default=None, max_length=100)
    language: str = Field(default="vi", max_length=10)
    specialty: str | None = Field(default=None, max_length=120)
    extracted_text: str | None = Field(default=None, max_length=2000000)
    license_status: str = Field(default="unknown", max_length=80)
    knowledge_domain: str = Field(min_length=3, max_length=80)
    jurisdiction: str = Field(min_length=2, max_length=80)
    target_population: str = Field(min_length=3, max_length=500)
    evidence_level: str | None = Field(default=None, max_length=100)
    recommendation_strength: str | None = Field(default=None, max_length=100)
    official_identifier: str | None = Field(default=None, max_length=200)
    source_locator: str | None = Field(default=None, max_length=500)
    limitations: str | None = Field(default=None, max_length=3000)

    @field_validator("published_at")
    @classmethod
    def validate_published_at(cls, value: str) -> str:
        date.fromisoformat(value)
        return value

    @field_validator("effective_from", "effective_until")
    @classmethod
    def validate_effective_dates(cls, value: str | None) -> str | None:
        if value is not None:
            date.fromisoformat(value)
        return value


class ReviewDecision(BaseModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED|REQUEST_REVISION)$")
    rationale: str = Field(min_length=10, max_length=5000)
    scope: list[str] = Field(default_factory=list, max_length=30)
    source_document_verified: bool = False
    version_current: bool = False
    license_cleared: bool = False
    evidence_assessment: str = Field(default="", max_length=5000)
    limitations: str = Field(default="", max_length=3000)
    has_conflict_of_interest: bool = False
    extraction_quality_reviewed: bool = False

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, value: list[str]) -> list[str]:
        invalid = set(value) - ALLOWED_APPROVED_SCOPES
        if invalid:
            raise ValueError(f"Unsupported approval scope: {', '.join(sorted(invalid))}")
        return value


def build_router(db, auth_dependency):
    router = APIRouter(prefix="/clinical-knowledge", tags=["Clinical Knowledge"])

    def require_reviewer(user):
        result = (
            db.table("clinical_knowledge_reviewers")
            .select("user_id,role,specialties,is_active,credential_verified,credential_type,credential_identifier,credential_verified_at,credential_verified_by")
            .eq("user_id", str(user.id))
            .eq("is_active", True)
            .limit(1).execute()
        )
        if (
            not result.data
            or result.data[0].get("role") not in {"physician", "pharmacist", "clinical_reviewer"}
            or not result.data[0].get("credential_verified")
            or not result.data[0].get("credential_type")
            or not result.data[0].get("credential_identifier")
            or not result.data[0].get("credential_verified_at")
            or not result.data[0].get("credential_verified_by")
        ):
            raise HTTPException(status_code=403, detail="Tài khoản chưa được cấp quyền thẩm định lâm sàng.")
        return result.data[0]

    @router.get("/sources")
    def list_sources(user=Depends(auth_dependency)):
        result = db.table("clinical_knowledge_sources").select("*").eq("is_active", True).order("name").execute()
        return {"sources": result.data or []}

    @router.post("/documents", status_code=201)
    def register_document(request: KnowledgeDocumentCreate, user=Depends(auth_dependency)):
        metadata = request.model_dump(mode="json")
        extracted_text = metadata.pop("extracted_text", None)
        source_url = str(request.source_url)
        host = normalize_host(source_url)
        sources = db.table("clinical_knowledge_sources").select("*").eq("is_active", True).execute()
        matched = [
            item for item in (sources.data or [])
            if host_is_within(host, normalize_host(item["base_url"]))
        ]
        domain = db.table("clinical_knowledge_domains").select("domain_key").eq("domain_key", request.knowledge_domain).eq("is_active", True).limit(1).execute()
        if not domain.data:
            raise HTTPException(status_code=422, detail="knowledge_domain không nằm trong taxonomy đã đăng ký.")
        checks = automated_document_checks(metadata, extracted_text)
        source_domain_matched = bool(matched)
        # A matching domain does not authenticate a particular document, its version,
        # legal status, or clinical correctness. Never promote on host match alone.
        status = initial_document_status(source_domain_matched, checks["passed"])
        row = {
            **metadata,
            "source_url": source_url,
            "source_id": matched[0]["id"] if matched else None,
            "source_verified": False,
            "source_domain_matched": source_domain_matched,
            "automated_checks": checks,
            "content_hash": hashlib.sha256((extracted_text or "").encode("utf-8")).hexdigest() if extracted_text else None,
            "extracted_text": extracted_text,
            "status": status,
            "created_by": str(user.id),
        }
        try:
            created = db.table("clinical_knowledge_documents").insert(row).execute()
            if not created.data:
                raise RuntimeError("Insert returned no row")
            doc = created.data[0]
            db.table("clinical_knowledge_audit").insert({
                "document_id": doc["id"], "actor_id": str(user.id),
                "action": "DOCUMENT_REGISTERED", "details": {"status": status, "checks": checks},
            }).execute()
            return {"document": doc, "automated_checks": checks, "notice": "Kiểm tra tự động không phải phê duyệt lâm sàng."}
        except Exception as exc:
            print("CLINICAL KNOWLEDGE REGISTER ERROR:", repr(exc), flush=True)
            raise HTTPException(status_code=503, detail="Không thể đăng ký tài liệu. Kiểm tra migration Clinical Knowledge.") from exc

    @router.get("/documents")
    def list_documents(status: str | None = None, limit: int = 50, user=Depends(auth_dependency)):
        limit = max(1, min(limit, 100))
        query = db.table("clinical_knowledge_documents").select(
            "id,title,publisher,document_type,source_url,published_at,effective_from,effective_until,version,language,specialty,knowledge_domain,jurisdiction,target_population,license_status,source_verified,source_domain_matched,automated_checks,status,created_at,updated_at"
        )
        if status:
            if status not in ALLOWED_STATUSES:
                raise HTTPException(status_code=422, detail="Trạng thái không hợp lệ.")
            query = query.eq("status", status)
        result = query.order("created_at", desc=True).limit(limit).execute()
        return {"documents": result.data or []}

    @router.get("/review-queue")
    def review_queue(user=Depends(auth_dependency)):
        require_reviewer(user)
        result = db.table("clinical_knowledge_documents").select(
            "id,title,publisher,document_type,source_url,published_at,effective_from,effective_until,version,specialty,knowledge_domain,jurisdiction,target_population,automated_checks,status,created_at"
        ).in_("status", ["SOURCE_VERIFIED", "AI_REVIEWED", "DISCOVERED"]).order("created_at").limit(100).execute()
        return {"documents": result.data or []}

    @router.get("/documents/{document_id}")
    def get_document_for_review(document_id: str, user=Depends(auth_dependency)):
        require_reviewer(user)
        found = db.table("clinical_knowledge_documents").select("*").eq("id", document_id).limit(1).execute()
        if not found.data:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
        return {"document": found.data[0]}

    @router.post("/documents/{document_id}/review")
    def review_document(document_id: str, request: ReviewDecision, user=Depends(auth_dependency)):
        reviewer = require_reviewer(user)
        found = db.table("clinical_knowledge_documents").select("*").eq("id", document_id).limit(1).execute()
        if not found.data:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
        doc = found.data[0]
        if not is_reviewable_status(str(doc.get("status") or "")):
            raise HTTPException(status_code=409, detail="Tài liệu ở trạng thái không cho phép thẩm định lại.")
        if not reviewer_is_independent(doc.get("created_by"), str(user.id)):
            raise HTTPException(status_code=403, detail="Người đăng ký tài liệu không được tự thẩm định tài liệu đó.")
        if request.has_conflict_of_interest:
            raise HTTPException(status_code=409, detail="Reviewer có xung đột lợi ích không được thực hiện quyết định thẩm định.")
        if request.decision == "APPROVED":
            if not request.source_document_verified or not request.version_current or not request.license_cleared:
                raise HTTPException(status_code=409, detail="Reviewer phải xác minh tài liệu gốc, phiên bản hiện hành và quyền sử dụng trước khi phê duyệt.")
            if not (doc.get("automated_checks") or {}).get("passed"):
                raise HTTPException(status_code=409, detail="Tài liệu chưa đạt kiểm tra metadata và toàn vẹn trích xuất.")
            if not doc.get("original_storage_path") or not doc.get("original_sha256"):
                raise HTTPException(status_code=409, detail="Không thể phê duyệt tài liệu chưa lưu bản gốc trong private storage và checksum.")
            if doc.get("extraction_status") != "EXTRACTED":
                raise HTTPException(status_code=409, detail="Tài liệu có trang chưa trích xuất đầy đủ; không thể phê duyệt.")
            if not str(doc.get("extracted_text") or "").strip() or len(str(doc.get("extracted_text") or "").strip()) < 200:
                raise HTTPException(status_code=409, detail="Không thể phê duyệt khi chưa có nội dung tài liệu đã trích xuất đầy đủ.")
            extraction_report = doc.get("extraction_report") or {}
            if extraction_report.get("pages_needing_human_check") and not request.extraction_quality_reviewed:
                raise HTTPException(status_code=409, detail="Phải xác nhận đã kiểm tra thủ công các trang có cảnh báo OCR/trích xuất.")
            if not request.scope or not request.evidence_assessment.strip():
                raise HTTPException(status_code=422, detail="Phải ghi đánh giá bằng chứng và phạm vi sử dụng được phê duyệt.")
            if doc.get("specialty") and doc["specialty"] not in (reviewer.get("specialties") or []):
                raise HTTPException(status_code=403, detail="Reviewer không có chuyên môn được khai báo phù hợp với tài liệu.")
            domain_policy = db.table("clinical_knowledge_domains").select("required_reviewers").eq("domain_key", doc.get("knowledge_domain")).limit(1).execute()
            required_reviewers = int(domain_policy.data[0]["required_reviewers"]) if domain_policy.data else 2
            prior = db.table("clinical_knowledge_reviews").select("reviewer_id").eq("document_id", document_id).eq("decision", "APPROVED").execute()
            prior_reviewers = {item.get("reviewer_id") for item in (prior.data or [])}
            if str(user.id) in prior_reviewers:
                raise HTTPException(status_code=409, detail="Reviewer này đã ghi nhận phê duyệt; cần reviewer độc lập khác.")
            new_status = "AI_REVIEWED" if len(prior_reviewers) + 1 < required_reviewers else "CLINICAL_APPROVED"
        elif request.decision == "REJECTED":
            new_status = "REJECTED"
        else:
            new_status = "DISCOVERED"
        try:
            db.table("clinical_knowledge_reviews").insert({
                "document_id": document_id, "reviewer_id": str(user.id),
                "reviewer_role": reviewer["role"], "decision": request.decision,
                "rationale": request.rationale, "approved_scope": request.scope,
                "source_document_verified": request.source_document_verified,
                "version_current": request.version_current, "license_cleared": request.license_cleared,
                "evidence_assessment": request.evidence_assessment,
                "limitations": request.limitations,
                "has_conflict_of_interest": request.has_conflict_of_interest,
                "extraction_quality_reviewed": request.extraction_quality_reviewed,
            }).execute()
            updated = db.table("clinical_knowledge_documents").update({
                "status": new_status, "reviewed_at": utc_now(),
                "reviewed_by": str(user.id),
                "license_status": "reviewer_cleared" if request.license_cleared else doc.get("license_status", "unknown"),
                "approved_scope": request.scope if new_status == "CLINICAL_APPROVED" else [],
            }).eq("id", document_id).execute()
            db.table("clinical_knowledge_audit").insert({
                "document_id": document_id, "actor_id": str(user.id),
                "action": "CLINICAL_REVIEW_" + request.decision,
                "details": {"status": new_status, "scope": request.scope, "rationale": request.rationale,
                            "evidence_assessment": request.evidence_assessment,
                            "limitations": request.limitations,
                            "has_conflict_of_interest": request.has_conflict_of_interest,
                            "extraction_quality_reviewed": request.extraction_quality_reviewed},
            }).execute()
            return {"document": updated.data[0] if updated.data else None, "status": new_status,
                    "notice": "Tài liệu thuộc nhóm tác động cao chỉ được phê duyệt sau hai reviewer độc lập." if new_status == "AI_REVIEWED" else "Phê duyệt chỉ có hiệu lực trong approved_scope; không thay thế đánh giá lâm sàng tại từng ca."}
        except Exception as exc:
            print("CLINICAL KNOWLEDGE REVIEW ERROR:", repr(exc), flush=True)
            raise HTTPException(status_code=503, detail="Không thể lưu quyết định thẩm định.") from exc

    return router
