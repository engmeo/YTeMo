"""Clinical evidence intelligence primitives and hybrid retrieval API.

Embeddings are generated only through an explicitly configured OpenAI-compatible
embedding endpoint. Retrieval remains restricted by approved evidence governance.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import date
from typing import Any

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

MODEL = os.getenv("CLINICAL_EMBEDDING_MODEL", "text-embedding-3-small")
DIMENSIONS = 768
TIMEOUT = (5, 20)


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip().casefold()


def lexical_score(query: str, text: str) -> float:
    q = set(re.findall(r"[\w-]{2,}", normalize(query)))
    d = set(re.findall(r"[\w-]{2,}", normalize(text)))
    if not q:
        return 0.0
    return len(q & d) / len(q)


def reciprocal_rank_fusion(*ranked_lists: list[dict[str, Any]], k: int = 60) -> list[dict[str, Any]]:
    """Fuse independent ranked lists without pretending scores share a scale."""
    fused: dict[str, dict[str, Any]] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            key = str(item.get("claim_id") or item.get("id") or "")
            if not key:
                continue
            entry = fused.setdefault(key, {**item, "rrf_score": 0.0})
            entry["rrf_score"] += 1.0 / (k + rank)
    return sorted(fused.values(), key=lambda item: item["rrf_score"], reverse=True)


def embed_query(text: str) -> tuple[list[float], str]:
    endpoint = os.getenv("CLINICAL_EMBEDDING_API_URL", "").strip()
    api_key = os.getenv("CLINICAL_EMBEDDING_API_KEY", "").strip()
    model = os.getenv("CLINICAL_EMBEDDING_MODEL", MODEL)
    if not endpoint or not api_key:
        raise RuntimeError("Embedding endpoint chưa được cấu hình.")
    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "input": text, "dimensions": DIMENSIONS},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    vector = payload["data"][0]["embedding"]
    if len(vector) != DIMENSIONS or not all(isinstance(x, (int, float)) for x in vector):
        raise ValueError("Embedding provider phải trả về vector 768 chiều.")
    return [float(x) for x in vector], model


def vector_literal(vector: list[float]) -> str:
    if len(vector) != DIMENSIONS:
        raise ValueError("Vector phải có 768 chiều.")
    return "[" + ",".join(f"{float(value):.8f}" for value in vector) + "]"


def _governed_candidates(db, request) -> list[dict[str, Any]]:
    """Build the full eligible set before semantic ranking; never use vector similarity as an approval filter."""
    claims_result = db.table("clinical_evidence_claims").select("*").eq("reviewer_status", "ACCEPTED").limit(1000).execute()
    claims = claims_result.data or []
    if not claims:
        return []
    doc_ids = list({item["document_id"] for item in claims})
    docs_result = db.table("clinical_knowledge_documents").select(
        "id,title,publisher,source_url,official_identifier,version,published_at,effective_from,effective_until,knowledge_domain,jurisdiction,target_population,specialty,status,is_current,approved_scope,original_sha256"
    ).in_("id", doc_ids).eq("status", "CLINICAL_APPROVED").eq("is_current", True).limit(1000).execute()
    docs = {item["id"]: item for item in (docs_result.data or [])}
    conflicts = db.table("clinical_evidence_conflicts").select("claim_ids").in_(
        "resolution_status", ["OPEN", "UNDER_REVIEW", "UNRESOLVED"]
    ).limit(500).execute()
    blocked = {cid for row in (conflicts.data or []) for cid in (row.get("claim_ids") or [])}
    as_of = date.fromisoformat(request.as_of) if getattr(request, "as_of", None) else date.today()
    candidates = []
    for claim in claims:
        if claim["id"] in blocked:
            continue
        doc = docs.get(claim["document_id"])
        if not doc or request.scope not in (doc.get("approved_scope") or []):
            continue
        if doc.get("jurisdiction") not in {request.jurisdiction, "GLOBAL"}:
            continue
        if claim.get("jurisdiction") and claim["jurisdiction"] not in {request.jurisdiction, "GLOBAL"}:
            continue
        if request.specialty and doc.get("specialty") != request.specialty:
            continue
        requested_population = normalize(request.population)
        claim_population = normalize(claim.get("population", ""))
        if requested_population not in claim_population:
            continue
        doc_tokens = set(re.findall(r"[\w-]{3,}", normalize(doc.get("target_population", ""))))
        requested_tokens = set(re.findall(r"[\w-]{3,}", requested_population))
        if not doc_tokens.issubset(requested_tokens):
            continue
        try:
            start = date.fromisoformat(doc["effective_from"]) if doc.get("effective_from") else None
            end = date.fromisoformat(doc["effective_until"]) if doc.get("effective_until") else None
        except ValueError:
            continue
        if (start and as_of < start) or (end and as_of > end):
            continue
        candidates.append({
            "claim": claim, "document": doc,
            "citation": {
                "document_title": doc["title"], "publisher": doc["publisher"],
                "source_url": doc["source_url"], "version": doc.get("version"),
                "page": claim.get("source_page_number"), "locator": claim.get("source_locator"),
                "exact_quote": claim.get("exact_quote"), "document_sha256": doc.get("original_sha256"),
            },
        })
    return candidates


def build_router(db, auth_dependency):
    router = APIRouter(prefix="/clinical-intelligence", tags=["Clinical Evidence Intelligence"])

    class SearchRequest(BaseModel):
        query: str = Field(min_length=2, max_length=1000)
        jurisdiction: str = Field(min_length=2, max_length=80)
        population: str = Field(min_length=3, max_length=1000)
        scope: str = Field(min_length=2, max_length=100)
        specialty: str | None = Field(default=None, max_length=120)
        limit: int = Field(default=10, ge=1, le=30)
        min_similarity: float = Field(default=0.25, ge=0, le=1)

    @router.post("/search")
    def hybrid_search(request: SearchRequest, user=Depends(auth_dependency)):
        from clinical_knowledge_workflows import (
            EvidenceRetrievalRequest, can_access_evidence_scope, retrieve_approved_evidence
        )
        evidence_request = EvidenceRetrievalRequest(
            query=request.query, jurisdiction=request.jurisdiction,
            population=request.population, scope=request.scope,
            specialty=request.specialty, limit=request.limit,
        )
        if not can_access_evidence_scope(db, user, request.scope):
            raise HTTPException(status_code=403, detail="Phạm vi này yêu cầu credential chuyên môn đã xác minh.")
        # Run the existing governance filters first; vector search can only rerank
        # eligible, approved claims and must never widen the candidate set.
        governed = retrieve_approved_evidence(db, evidence_request)
        try:
            # Unlike the lexical endpoint, this candidate pool contains every claim
            # that passes governance filters, so semantic matches need not share words.
            eligible = _governed_candidates(db, evidence_request)
            if not eligible:
                return {**governed, "retrieval_mode": "hybrid", "embedding_used": False}
            vector, model = embed_query(request.query)
            rpc = db.rpc("match_clinical_evidence", {
                "query_embedding": vector_literal(vector),
                "match_count": min(100, request.limit * 10),
                "min_similarity": request.min_similarity,
            }).execute()
            vector_rows = rpc.data or []
        except Exception as exc:
            return {
                **governed, "retrieval_mode": "structured_lexical_fallback",
                "embedding_used": False, "vector_search_error": type(exc).__name__,
                "notice": "Vector search không khả dụng; kết quả chỉ dùng lexical retrieval đã qua governance.",
            }
        eligible_by_id = {str(item["claim"]["id"]): item for item in eligible}
        vector_ranked = []
        for row in vector_rows:
            key = str(row.get("claim_id"))
            if key in eligible_by_id:
                vector_ranked.append({**eligible_by_id[key], "claim_id": key, "similarity": row.get("similarity")})
        lexical_ranked = [
            {**item, "claim_id": str(item["claim"]["id"]),
             "lexical_score": lexical_score(request.query, item["claim"].get("claim_text", "") + " " + item["claim"].get("exact_quote", ""))}
            for item in eligible
        ]
        lexical_ranked = [item for item in lexical_ranked if item["lexical_score"] > 0]
        lexical_ranked.sort(key=lambda item: item["lexical_score"], reverse=True)
        fused = reciprocal_rank_fusion(vector_ranked, lexical_ranked)
        output = []
        for item in fused[:request.limit]:
            clean = {k: v for k, v in item.items() if k not in {"claim_id", "rrf_score", "similarity", "lexical_score"}}
            clean["retrieval_scores"] = {
                "rrf": item["rrf_score"], "vector_similarity": item.get("similarity"),
                "lexical_score": item.get("lexical_score"),
            }
            output.append(clean)
        return {
            "evidence": output, "abstention": not bool(output),
            "reason": None if output else "NO_GOVERNED_EVIDENCE_MATCH",
            "retrieval_mode": "hybrid", "embedding_used": True, "embedding_model": model,
            "notice": "Hybrid ranking chỉ sắp xếp lại claim đã qua bộ lọc phê duyệt, phạm vi, quần thể, jurisdiction và conflict; điểm tương đồng không phải độ đúng lâm sàng.",
        }

    @router.post("/embeddings/backfill")
    def backfill_embeddings(limit: int = 100, user=Depends(auth_dependency)):
        reviewer = db.table("clinical_knowledge_reviewers").select("role,is_active").eq(
            "user_id", str(user.id)
        ).eq("is_active", True).limit(1).execute()
        if not reviewer.data or reviewer.data[0].get("role") != "knowledge_admin":
            raise HTTPException(status_code=403, detail="Chỉ knowledge_admin được tạo embedding.")
        limit = max(1, min(limit, 250))
        claims = db.table("clinical_evidence_claims").select(
            "id,document_id,claim_text,exact_quote,population,intervention,comparator,outcomes"
        ).eq("reviewer_status", "ACCEPTED").limit(limit).execute()
        if not claims.data:
            return {"embedded_count": 0, "notice": "Không có claim ACCEPTED."}
        doc_ids = list({row["document_id"] for row in claims.data})
        docs = db.table("clinical_knowledge_documents").select("id,status,is_current").in_(
            "id", doc_ids
        ).eq("status", "CLINICAL_APPROVED").eq("is_current", True).execute()
        approved = {row["id"] for row in (docs.data or [])}
        embedded, skipped = 0, 0
        for claim in claims.data:
            if claim["document_id"] not in approved:
                skipped += 1
                continue
            source = "\\n".join(str(claim.get(key) or "") for key in (
                "claim_text", "exact_quote", "population", "intervention", "comparator", "outcomes"
            ))
            try:
                vector, model = embed_query(source)
                db.table("clinical_evidence_embeddings").upsert({
                    "claim_id": claim["id"], "embedding": vector_literal(vector),
                    "embedding_model": model,
                    "embedding_input_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                }).execute()
                embedded += 1
            except Exception as exc:
                raise HTTPException(status_code=503, detail=f"Embedding thất bại ({type(exc).__name__}); đã xử lý {embedded} claim.") from exc
        return {"embedded_count": embedded, "skipped_not_current_approved": skipped,
                "notice": "Embedding chỉ phục vụ tìm kiếm; không làm thay đổi trạng thái phê duyệt claim."}

    @router.get("/graph/entities")
    def graph_entities(entity_type: str | None = None, limit: int = 100, user=Depends(auth_dependency)):
        limit = max(1, min(limit, 200))
        query = db.table("clinical_evidence_graph_entities").select("*")
        if entity_type:
            query = query.eq("entity_type", entity_type)
        result = query.order("canonical_name").limit(limit).execute()
        return {"entities": result.data or [], "notice": "Graph entity là dữ liệu tri thức có provenance; trạng thái CANDIDATE không được dùng như sự thật lâm sàng."}

    @router.get("/graph/edges")
    def graph_edges(entity_id: str, limit: int = 100, user=Depends(auth_dependency)):
        result = db.table("clinical_evidence_graph_edges").select("*").or_(
            f"source_entity_id.eq.{entity_id},target_entity_id.eq.{entity_id}"
        ).order("created_at", desc=True).limit(max(1, min(limit, 200))).execute()
        return {"edges": result.data or []}

    @router.post("/synthesis/draft")
    def synthesis_draft(claim_ids: list[str], user=Depends(auth_dependency)):
        if not claim_ids or len(claim_ids) > 30:
            raise HTTPException(status_code=422, detail="Cần từ 1 đến 30 claim_id.")
        rows = db.table("clinical_evidence_claims").select(
            "id,document_id,claim_text,claim_type,population,intervention,comparator,outcomes,effect_estimate,certainty,recommendation_strength,appraisal_framework,appraisal,source_page_number,exact_quote"
        ).in_("id", claim_ids).eq("reviewer_status", "ACCEPTED").execute()
        claims = rows.data or []
        if len(claims) != len(set(claim_ids)):
            raise HTTPException(status_code=422, detail="Chỉ chấp nhận claim ACCEPTED; một số claim không hợp lệ.")
        docs = db.table("clinical_knowledge_documents").select(
            "id,title,publisher,version,source_url,jurisdiction,target_population,status,is_current"
        ).in_("id", list({x["document_id"] for x in claims})).execute()
        doc_map = {x["id"]: x for x in (docs.data or [])}
        if any(doc_map.get(x["document_id"], {}).get("status") != "CLINICAL_APPROVED" or not doc_map[x["document_id"]].get("is_current") for x in claims):
            raise HTTPException(status_code=409, detail="Tổng hợp chỉ dùng claim từ tài liệu đã duyệt và còn hiện hành.")
        grouped = {}
        for claim in claims:
            key = (claim["claim_type"], normalize(claim["population"]))
            grouped.setdefault(str(key), []).append({
                "claim": claim, "document": doc_map[claim["document_id"]]
            })
        return {
            "draft_groups": list(grouped.values()),
            "synthesis_status": "STRUCTURED_EVIDENCE_MAP_NOT_META_ANALYSIS",
            "limitations": [
                "Không tính gộp effect size hoặc dị biệt thống kê.",
                "Không suy ra quan hệ nhân quả từ các claim quan sát.",
                "Không giải quyết xung đột bằng cách bỏ phiếu theo số lượng nghiên cứu.",
                "Cần đánh giá nguy cơ sai lệch, tính trực tiếp, độ chắc chắn và bối cảnh áp dụng."
            ],
            "notice": "Đây là evidence map có cấu trúc, không phải khuyến nghị điều trị hay kết luận tổng hợp lâm sàng."
        }

    return router
