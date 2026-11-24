"""Low-latency model gateway for Y TE MO.

The gateway supports:
- a self-hosted OpenAI-compatible inference server (vLLM, SGLang, llama.cpp server);
- an optional OpenRouter-compatible endpoint;
- deterministic routing profiles without running an ensemble on every turn.

It deliberately does not download model weights at API startup. Model weights are
large artifacts and must be fetched explicitly on a controlled inference host.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests

REGISTRY_PATH = Path(__file__).with_name("model_registry.json")
DEFAULT_TIMEOUT = (3.0, 18.0)


class ModelGatewayError(RuntimeError):
    pass


def load_model_registry() -> dict[str, Any]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def choose_profile(message: str, evidence_context: str = "", requested_profile: str | None = None) -> str:
    """Choose a latency profile; safety gates remain outside this heuristic.

    Explicit high-risk evidence scopes and unresolved evidence are handled by
    clinical governance. This function only chooses an inference budget.
    """
    allowed = {"fast", "reasoning", "medical"}
    if requested_profile in allowed:
        return requested_profile
    text = (message or "").casefold()
    evidence = (evidence_context or "").casefold()
    complex_markers = (
        "nhiều bệnh", "nhiều thuốc", "tương tác thuốc", "bệnh nền",
        "kết quả xét nghiệm", "diễn biến", "mâu thuẫn", "không rõ nguyên nhân",
        "phân biệt", "so sánh", "tại sao", "đánh giá nguy cơ",
    )
    if any(marker in text for marker in complex_markers):
        return "reasoning"
    if any(marker in evidence for marker in ("abstention", "conflict", "unresolved")):
        return "reasoning"
    if any(marker in text for marker in ("liều", "thuốc", "chẩn đoán", "điều trị", "xét nghiệm")):
        return "medical"
    return "fast"


def _model_for_profile(profile: str) -> str:
    env_key = {
        "fast": "YTEMO_FAST_MODEL",
        "reasoning": "YTEMO_REASONING_MODEL",
        "medical": "YTEMO_MEDICAL_MODEL",
    }[profile]
    return os.getenv(env_key, os.getenv("YTEMO_DEFAULT_MODEL", "openrouter/free"))


def _endpoint_config() -> tuple[str, str, str]:
    backend = os.getenv("YTEMO_MODEL_BACKEND", "openrouter").strip().lower()
    if backend == "local":
        endpoint = os.getenv("YTEMO_LOCAL_MODEL_BASE_URL", "http://127.0.0.1:8001/v1").rstrip("/")
        key = os.getenv("YTEMO_LOCAL_MODEL_API_KEY", "local")
    elif backend == "openrouter":
        endpoint = os.getenv("YTEMO_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        key = os.getenv("OPENROUTER_API_KEY", "")
    else:
        raise ModelGatewayError("YTEMO_MODEL_BACKEND chỉ nhận local hoặc openrouter.")
    if not key:
        raise ModelGatewayError("Thiếu API key của model provider trong cấu hình backend.")
    return backend, endpoint, key


def generate(
    messages: list[dict[str, str]],
    profile: str = "fast",
    max_tokens: int = 700,
    temperature: float = 0.2,
) -> dict[str, Any]:
    if profile not in {"fast", "reasoning", "medical"}:
        raise ValueError("Unknown model profile.")
    backend, endpoint, key = _endpoint_config()
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
            "fast": os.getenv("YTEMO_FAST_MODEL", os.getenv("YTEMO_DEFAULT_MODEL", "openrouter/free")),
            "reasoning": os.getenv("YTEMO_REASONING_MODEL", os.getenv("YTEMO_DEFAULT_MODEL", "openrouter/free")),
            "medical": os.getenv("YTEMO_MEDICAL_MODEL", os.getenv("YTEMO_DEFAULT_MODEL", "openrouter/free")),
        },
    }


def generate_companion_response(prompt: str, message: str, evidence_context: str = "") -> dict[str, Any]:
    profile = choose_profile(message, evidence_context)
    max_tokens = 500 if profile == "fast" else 1000
    return generate([{"role": "user", "content": prompt}], profile=profile, max_tokens=max_tokens)
