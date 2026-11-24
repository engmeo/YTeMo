"""Low-latency multi-model gateway for Y TE MO.

Supports separate OpenAI-compatible endpoints per profile (vLLM, SGLang,
llama.cpp server) and an optional OpenRouter free-model pool. It does not
download weights at API startup or run an ensemble for routine turns.
"""
from __future__ import annotations

import json
import os
import time
from typing import Iterator
from pathlib import Path
from typing import Any

import requests

REGISTRY_PATH = Path(__file__).with_name("model_registry.json")


class ModelGatewayError(RuntimeError):
    pass


def load_model_registry() -> dict[str, Any]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_vietnamese(value: str) -> str:
    import unicodedata
    text = (value or "").casefold().replace("đ", "d")
    return "".join(
        char for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )


_INTENT_TERMS = {
    "medication": (
        "thuoc", "lieu", "tuong tac", "tac dung phu", "don thuoc",
        "uong thuoc", "vien thuoc", "tiem", "mg", "mcg", "ml",
    ),
    "laboratory": (
        "xet nghiem", "ket qua", "hba1c", "glucose", "creatinin",
        "cholesterol", "triglycerid", "men gan", "cong thuc mau",
    ),
    "cost": (
        "chi phi", "gia tien", "vien phi", "hoa don", "tong tien",
        "bao nhieu tien", "chi tra",
    ),
    "insurance": (
        "bhyt", "bao hiem y te", "muc huong", "dung tuyen", "trai tuyen",
    ),
    "care_navigation": (
        "dat lich", "lich kham", "benh vien", "phong kham", "bac si",
        "chuyen khoa", "di kham",
    ),
    "clinical": (
        "trieu chung", "dau bung", "sot", "chan doan", "dieu tri",
        "benh nen", "ket luan y khoa", "nguy co", "phac do",
    ),
}

_EMERGENCY_TERMS = (
    "kho tho", "khong tho duoc", "dau nguc", "bat tinh", "hon me",
    "dot quy", "meo mieng", "liet nua nguoi", "chay mau khong cam",
    "co giat", "soc phan ve", "phu luoi", "tu tu", "muon tu sat",
)

_COMPLEXITY_TERMS = (
    "nhieu benh", "nhieu thuoc", "tuong tac thuoc", "benh nen",
    "dien bien", "mau thuan", "phan biet", "so sanh", "tong hop",
    "danh gia nguy co", "khong ro nguyen nhan", "nhieu ket qua",
)


def route_request(message: str, evidence_context: str = "") -> dict[str, Any]:
    """Transparent multi-signal routing; no extra LLM call is added to TTFT."""
    normalized = _normalize_vietnamese(message)
    evidence = _normalize_vietnamese(evidence_context)
    intents = [
        name for name, terms in _INTENT_TERMS.items()
        if any(_normalize_vietnamese(term) in normalized for term in terms)
    ]
    import re
    emergency = False
    for term in _EMERGENCY_TERMS:
        normalized_term = _normalize_vietnamese(term)
        for match in re.finditer(re.escape(normalized_term), normalized):
            prefix = normalized[max(0, match.start() - 28):match.start()]
            if re.search(r"\b(khong|chua|khong bi|khong con)\s*$", prefix):
                continue
            emergency = True
            break
        if emergency:
            break
    complexity_reasons = [
        term for term in _COMPLEXITY_TERMS
        if _normalize_vietnamese(term) in normalized
    ]
    if len(intents) >= 2:
        complexity_reasons.append("multiple_intent_domains")
    if len(normalized) >= 900:
        complexity_reasons.append("long_context")
    if normalized.count("?") >= 2:
        complexity_reasons.append("multiple_questions")
    if any(term in evidence for term in ("abstention", "conflict", "unresolved", "retrieval_error")):
        complexity_reasons.append("evidence_uncertainty")

    if emergency:
        profile = "fast"
    elif complexity_reasons:
        profile = "reasoning"
    elif intents:
        profile = "medical"
    else:
        profile = "fast"

    return {
        "profile": profile,
        "intents": intents or ["general"],
        "emergency_signal": emergency,
        "complexity_reasons": complexity_reasons,
    }


def choose_profile(
    message: str,
    evidence_context: str = "",
    requested_profile: str | None = None,
) -> str:
    """Select inference budget; clinical authorization and safety are separate."""
    allowed = {"fast", "reasoning", "medical"}
    if requested_profile in allowed:
        return requested_profile
    return route_request(message, evidence_context)["profile"]


def _endpoint_config(profile: str) -> tuple[str, str, str]:
    backend = os.getenv("YTEMO_MODEL_BACKEND", "openrouter").strip().lower()
    suffix = profile.upper()
    if backend == "local":
        endpoint = os.getenv(
            f"YTEMO_{suffix}_BASE_URL",
            os.getenv("YTEMO_LOCAL_MODEL_BASE_URL", "http://127.0.0.1:8001/v1"),
        ).rstrip("/")
        key = os.getenv(
            f"YTEMO_{suffix}_API_KEY",
            os.getenv("YTEMO_LOCAL_MODEL_API_KEY", "local"),
        )
    elif backend == "openrouter":
        endpoint = os.getenv(
            f"YTEMO_{suffix}_BASE_URL",
            os.getenv("YTEMO_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        ).rstrip("/")
        key = os.getenv(f"YTEMO_{suffix}_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
    else:
        raise ModelGatewayError("YTEMO_MODEL_BACKEND chỉ nhận local hoặc openrouter.")
    if not key:
        raise ModelGatewayError(f"Thiếu API key cho profile {profile}.")
    return backend, endpoint, key


def _model_for_profile(profile: str) -> str:
    env_key = {
        "fast": "YTEMO_FAST_MODEL",
        "reasoning": "YTEMO_REASONING_MODEL",
        "medical": "YTEMO_MEDICAL_MODEL",
    }[profile]
    return os.getenv(env_key, os.getenv("YTEMO_DEFAULT_MODEL", "openrouter/free"))


def generate(
    messages: list[dict[str, str]],
    profile: str = "fast",
    max_tokens: int = 700,
    temperature: float = 0.2,
    model_override: str | None = None,
) -> dict[str, Any]:
    if profile not in {"fast", "reasoning", "medical"}:
        raise ValueError("Unknown model profile.")
    backend, endpoint, key = _endpoint_config(profile)
    model = (model_override or _model_for_profile(profile)).strip()
    if not model or len(model) > 200:
        raise ValueError("Invalid model override.")
    timeout = max(5, min(int(os.getenv("YTEMO_MODEL_TIMEOUT_SECONDS", "18")), 30))
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max(64, min(int(max_tokens), 1800)),
        "temperature": max(0.0, min(float(temperature), 1.0)),
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if backend == "openrouter":
        headers["X-Title"] = "Y TE MO"
        site_url = os.getenv("OPENROUTER_SITE_URL")
        if site_url:
            headers["HTTP-Referer"] = site_url
    started = time.perf_counter()
    try:
        response = requests.post(
            f"{endpoint}/chat/completions",
            headers=headers,
            json=payload,
            timeout=(3, timeout),
        )
        response.raise_for_status()
        body = response.json()
        text = body["choices"][0]["message"]["content"]
        if isinstance(text, list):
            text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
        if not isinstance(text, str) or not text.strip():
            raise ModelGatewayError("Model provider returned an empty response.")
        usage = body.get("usage") or {}
        return {
            "text": text.strip(),
            "model": body.get("model", model),
            "profile": profile,
            "provider": backend,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
        }
    except requests.Timeout as exc:
        raise ModelGatewayError("Model timeout; retry with the fast profile or try again later.") from exc
    except requests.RequestException as exc:
        raise ModelGatewayError(f"Model provider unavailable: {type(exc).__name__}") from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ModelGatewayError("Model provider returned an invalid response.") from exc



def generate_stream(
    messages: list[dict[str, str]],
    profile: str = "fast",
    max_tokens: int = 700,
    temperature: float = 0.2,
) -> Iterator[str]:
    """Yield provider text deltas as they arrive; never buffer the full answer."""
    if profile not in {"fast", "reasoning", "medical"}:
        raise ValueError("Unknown model profile.")
    backend, endpoint, key = _endpoint_config(profile)
    model = _model_for_profile(profile)
    timeout = max(5, min(int(os.getenv("YTEMO_MODEL_TIMEOUT_SECONDS", "18")), 30))
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max(64, min(int(max_tokens), 1800)),
        "temperature": max(0.0, min(float(temperature), 1.0)),
        "stream": True,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if backend == "openrouter":
        headers["X-Title"] = "Y TE MO"
        site_url = os.getenv("OPENROUTER_SITE_URL")
        if site_url:
            headers["HTTP-Referer"] = site_url

    try:
        with requests.post(
            f"{endpoint}/chat/completions",
            headers=headers,
            json=payload,
            timeout=(3, timeout),
            stream=True,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else raw_line
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content")
                if isinstance(content, str) and content:
                    yield content
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and isinstance(part.get("text"), str):
                            if part["text"]:
                                yield part["text"]
    except requests.Timeout as exc:
        raise ModelGatewayError("Model stream timeout; provider stopped sending data.") from exc
    except requests.RequestException as exc:
        raise ModelGatewayError(f"Model stream unavailable: {type(exc).__name__}") from exc


def model_catalog() -> dict[str, Any]:
    registry = load_model_registry()
    return {
        "policy": registry["policy"],
        "models": [
            {
                "id": item["id"],
                "display_name": item["display_name"],
                "roles": item["role"],
                "license": item["license"],
                "license_status": item["license_status"],
                "runtime_profile": item["runtime_profile"],
                "default_enabled": item["default_enabled"],
            }
            for item in registry["models"]
        ],
        "active_backend": os.getenv("YTEMO_MODEL_BACKEND", "openrouter"),
        "profiles": {
            profile: {
                "model": _model_for_profile(profile),
                "endpoint_configured": bool(
                    os.getenv(f"YTEMO_{profile.upper()}_BASE_URL")
                    or os.getenv("YTEMO_LOCAL_MODEL_BASE_URL")
                    or os.getenv("YTEMO_OPENROUTER_BASE_URL")
                    or os.getenv("YTEMO_MODEL_BACKEND", "openrouter") == "openrouter"
                ),
            }
            for profile in ("fast", "reasoning", "medical")
        },
    }


def generate_companion_response(prompt: str, message: str, evidence_context: str = "") -> dict[str, Any]:
    profile = choose_profile(message, evidence_context)
    max_tokens = 500 if profile == "fast" else 1000
    return generate([{"role": "user", "content": prompt}], profile=profile, max_tokens=max_tokens)
