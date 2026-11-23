from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable, Mapping, Optional
import re


class CostIntelligenceError(ValueError):
    pass


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise CostIntelligenceError(f"{field} must be a finite number")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise CostIntelligenceError(f"{field} must be a finite number")
    if not result.is_finite():
        raise CostIntelligenceError(f"{field} must be finite")
    return result


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CostIntelligenceError(f"{field} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class CostLine:
    item_id: str
    category: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    currency: str
    source_quote: Optional[str] = None
    source_ref: Optional[str] = None


def normalize_cost_items(items: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    '''Validate and normalize explicitly supplied invoice/service/medicine/lab line items.'''
    if isinstance(items, (str, bytes, Mapping)):
        raise CostIntelligenceError("items must be a sequence of item objects")
    normalized = []
    seen = set()
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise CostIntelligenceError(f"items[{index}] must be an object")
        item_id = str(item.get("item_id") or f"line-{index + 1}").strip()
        if item_id in seen:
            raise CostIntelligenceError(f"duplicate item_id: {item_id}")
        seen.add(item_id)
        category = _text(item.get("category"), f"items[{index}].category").lower()
        if category not in {"visit", "medicine", "lab", "imaging", "procedure", "supplies", "transport", "other"}:
            raise CostIntelligenceError(f"unsupported category: {category}")
        description = _text(item.get("description"), f"items[{index}].description")
        quantity = _decimal(item.get("quantity", 1), f"items[{index}].quantity")
        unit_price = _decimal(item.get("unit_price"), f"items[{index}].unit_price")
        if quantity <= 0 or unit_price < 0:
            raise CostIntelligenceError("quantity must be > 0 and unit_price must be >= 0")
        amount = (quantity * unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        currency = str(item.get("currency") or "VND").upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise CostIntelligenceError(f"invalid currency: {currency}")
        normalized.append({
            "item_id": item_id, "category": category, "description": description,
            "quantity": _money(quantity), "unit_price": _money(unit_price),
            "amount": _money(amount), "currency": currency,
            "source_quote": item.get("source_quote"), "source_ref": item.get("source_ref")
        })
    return normalized


def analyze_patient_journey_cost(items: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    '''Aggregate only supplied amounts; never invent prices or infer clinical necessity.'''
    rows = normalize_cost_items(items)
    currencies = sorted({r["currency"] for r in rows})
    if len(currencies) > 1:
        raise CostIntelligenceError("mixed currencies are not aggregated; convert explicitly first")
    currency = currencies[0] if currencies else "VND"
    totals = defaultdict(Decimal)
    for row in rows:
        totals[row["category"]] += Decimal(row["amount"])
    grand_total = sum(totals.values(), Decimal("0"))
    return {
        "status": "calculated" if rows else "insufficient_data",
        "currency": currency,
        "line_count": len(rows),
        "total": _money(grand_total),
        "by_category": {k: _money(v) for k, v in sorted(totals.items())},
        "items": rows,
        "limitations": [
            "Chi phi chi duoc tinh tu du lieu do nguoi dung cung cap; khong phai bao gia.",
            "Khong ket luan dich vu, thuoc hoac xet nghiem co can thiet ve mat lam sang hay khong.",
            "Can doi chieu hoa don, bang gia va quy dinh hien hanh voi co so y te."
        ]
    }


def estimate_bhyt_payment(
    *, eligible_amount: Any, coverage_rate: Any,
    patient_cap: Any = None, currency: str = "VND",
    rule_reference: Optional[str] = None
) -> dict[str, Any]:
    '''Arithmetic estimate from explicitly supplied eligibility/rate/cap; no legal-rule inference.'''
    eligible = _decimal(eligible_amount, "eligible_amount")
    rate = _decimal(coverage_rate, "coverage_rate")
    if eligible < 0 or rate < 0 or rate > 100:
        raise CostIntelligenceError("eligible_amount must be >= 0 and coverage_rate must be between 0 and 100")
    gross = (eligible * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    applied_cap = None
    if patient_cap is not None:
        cap = _decimal(patient_cap, "patient_cap")
        if cap < 0:
            raise CostIntelligenceError("patient_cap must be >= 0")
        gross = min(gross, cap)
        applied_cap = _money(cap)
    cur = str(currency).upper()
    if not re.fullmatch(r"[A-Z]{3}", cur):
        raise CostIntelligenceError("currency must be a three-letter code")
    return {
        "status": "estimate_only",
        "eligible_amount": _money(eligible),
        "coverage_rate_percent": _money(rate),
        "estimated_insurer_payment": _money(gross),
        "estimated_patient_share_of_eligible_amount": _money(eligible - gross),
        "patient_cap": applied_cap,
        "currency": cur,
        "rule_reference": rule_reference,
        "requires_human_verification": True,
        "limitations": [
            "Chi la uoc tinh so hoc dua tren ty le va muc tran duoc cung cap.",
            "Khong tu xac dinh dung tuyen, doi tuong, muc huong, pham vi duoc chi tra, dong chi tra hoac tran quyen loi.",
            "Can co so BHYT/co so kham chua benh xac nhan theo quy dinh tai thoi diem su dung."
        ]
    }


def build_cost_intelligence_report(
    *, cost_items: Iterable[Mapping[str, Any]],
    bhyt: Optional[Mapping[str, Any]] = None,
    medication_items: Optional[Iterable[Mapping[str, Any]]] = None,
    lab_items: Optional[Iterable[Mapping[str, Any]]] = None
) -> dict[str, Any]:
    '''Cross-domain roll-up. Medication/lab lists are descriptive cost subsets, not treatment advice.'''
    journey = analyze_patient_journey_cost(cost_items)
    med = normalize_cost_items(medication_items or [])
    lab = normalize_cost_items(lab_items or [])
    for label, subset in (("medication", med), ("lab", lab)):
        subset_currencies = {x["currency"] for x in subset}
        if len(subset_currencies) > 1:
            raise CostIntelligenceError(f"mixed currencies in {label} items")
        if subset_currencies and journey["line_count"] and subset_currencies != {journey["currency"]}:
            raise CostIntelligenceError(f"{label} currency must match journey currency")
    report = {
        "schema_version": "1.0",
        "journey_cost": journey,
        "medication_costs": {
            "line_count": len(med),
            "total": _money(sum((Decimal(x["amount"]) for x in med), Decimal("0"))),
            "currency": med[0]["currency"] if med else journey["currency"],
            "items": med,
            "safety_note": "Khong tu de xuat doi thuoc, thay doi lieu hoac ngung thuoc."
        },
        "lab_costs": {
            "line_count": len(lab),
            "total": _money(sum((Decimal(x["amount"]) for x in lab), Decimal("0"))),
            "currency": lab[0]["currency"] if lab else journey["currency"],
            "items": lab,
            "safety_note": "Khong tu ket luan xet nghiem co can thiet; can bac si danh gia."
        },
        "bhyt": estimate_bhyt_payment(**dict(bhyt)) if bhyt is not None else {
            "status": "not_calculated",
            "reason": "Chua co du lieu quyen loi BHYT da duoc xac minh."
        },
        "evidence_policy": "Moi so tien phai truy vet duoc ve source_quote/source_ref hoac tai lieu nguon.",
        "clinical_boundary": "Day la cong cu tong hop tai chinh, khong phai cong cu chan doan hay chi dinh dieu tri."
    }
    return report
