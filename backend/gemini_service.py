"""OpenRouter-compatible AI service with shared retry policy."""
import os
import time
from types import SimpleNamespace

import requests


class GeminiServiceError(RuntimeError):
    """AI provider request failed."""


class OpenRouterHTTPError(RuntimeError):
    def __init__(self, status_code, message):
        self.status_code = status_code
        super().__init__(f"OpenRouter HTTP {status_code}: {message}")


class _OpenRouterModels:
    def __init__(self, api_key):
        self.api_key = api_key

    def generate_content(self, model, contents):
        selected_model = os.getenv("OPENROUTER_MODEL") or model or "openrouter/free"
        payload = {
            "model": selected_model,
            "messages": [{"role": "user", "content": str(contents)}],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "Y TE MO",
        }

        referer = os.getenv("OPENROUTER_SITE_URL")
        if referer:
            headers["HTTP-Referer"] = referer

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if not response.ok:
            try:
                detail = response.json().get("error", {}).get("message", "")
            except Exception:
                detail = response.text[:300]
            raise OpenRouterHTTPError(response.status_code, str(detail)[:300])

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenRouter returned an unexpected response format.") from exc

        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )

        return SimpleNamespace(text=content or "")


class _OpenRouterClient:
    def __init__(self, api_key):
        self.models = _OpenRouterModels(api_key)


_client = None


def get_gemini_client(api_key=None):
    """Keep the legacy function name to preserve existing Agent integrations."""
    global _client

    if _client is not None and api_key is None:
        return _client

    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise GeminiServiceError("Thieu OPENROUTER_API_KEY trong cau hinh backend.")

    try:
        client = _OpenRouterClient(key)
        if api_key is None:
            _client = client
        return client
    except Exception as exc:
        raise GeminiServiceError(
            f"Khong the khoi tao OpenRouter client: {type(exc).__name__}: {str(exc)[:300]}"
        ) from exc


def _error_status(exc):
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "code", None)
    response = getattr(exc, "response", None)
    if status is None and response is not None:
        status = getattr(response, "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _is_temporary_error(exc):
    if _error_status(exc) in {408, 429, 500, 502, 503, 504}:
        return True
    if isinstance(exc, requests.RequestException):
        return True
    message = str(exc).lower()
    return any(term in message for term in (
        "deadline_exceeded", "timed out", "timeout",
        "temporarily unavailable", "high demand",
    ))


def generate_content(model, contents, client=None):
    """One application-level retry policy: 3 attempts, delays 2s and 4s."""
    target = client if client is not None else get_gemini_client()
    delays = (2, 4)
    last_error = None

    for attempt in range(3):
        try:
            return target.models.generate_content(
                model=model,
                contents=contents,
            )
        except Exception as exc:
            last_error = exc
            if not _is_temporary_error(exc) or attempt == 2:
                break

            delay = delays[attempt]
            print(
                f"OPENROUTER TAM THOI LOI (lan {attempt + 1}/3). "
                f"Thu lai sau {delay} giay...",
                flush=True,
            )
            time.sleep(delay)

    raise GeminiServiceError(
        f"AI provider khong phan hoi sau toi da 3 lan thu. "
        f"Model={os.getenv('OPENROUTER_MODEL') or model or 'openrouter/free'}. "
        f"Loi cuoi: {type(last_error).__name__}: {str(last_error)[:500]}"
    ) from last_error