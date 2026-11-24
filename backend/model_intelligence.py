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


def choose_profile(message: str, evidence_context: str = "", requested_profile: str | None = None) -> str:
    """Select inference budget; clinical authorization and safety are separate."""
    allowed = {"fast", "reasoning", "medical"}
    if requested_profile in allowed:
        return requested_profile
    text = (message or "").casefold()
    evidence = (evidence_context or "").casefold()
    if any(term in text for term in (
        "nhiều bệnh", "nhiều thuốc", "tương tác thuốc", "bệnh nền",
        "kết quả xét nghiệm", "diễn biến", "mâu thuẫn", "không rõ nguyên nhân",
        "phân biệt", "so sánh", "đánh giá nguy cơ",
    )):
        return "reasoning"
    if any(term in evidence for term in ("abstention", "conflict", "unresolved")):
        return "reasoning"
    if any(term in text for term in ("liều", "thuốc", "chẩn đoán", "điều trị", "xét nghiệm")):
        return "medical"
    return "fast"


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
) -> dict[str, Any]:
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
