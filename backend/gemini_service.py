"""Shared Gemini client and retry policy for Y TE MO."""
import os
import re
import time

from google import genai
from google.genai import types


class GeminiServiceError(RuntimeError):
    """Gemini request failed after applying the shared retry policy."""


_client = None


def get_gemini_client(api_key=None):
    global _client

    if _client is not None:
        return _client

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise GeminiServiceError("Thieu GEMINI_API_KEY trong cau hinh backend.")

    try:
        _client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(
                timeout=30000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
    except Exception as exc:
        raise GeminiServiceError(
            f"Khong the khoi tao Gemini client: {type(exc).__name__}: {str(exc)[:300]}"
        ) from exc

    return _client


def _error_status(exc):
    status = getattr(exc, "code", None)
    if status is None:
        status = getattr(exc, "status_code", None)

    response = getattr(exc, "response", None)
    if status is None and response is not None:
        status = getattr(response, "status_code", None)

    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _is_temporary_error(exc):
    retryable_codes = {429, 500, 502, 503, 504}
    if _error_status(exc) in retryable_codes:
        return True

    message = str(exc).lower()
    return any(term in message for term in (
        "deadline_exceeded",
        "timed out",
        "timeout",
        "temporarily unavailable",
        "high demand",
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
                f"GEMINI TAM THOI LOI (lan {attempt + 1}/3). "
                f"Thu lai sau {delay} giay...",
                flush=True,
            )
            time.sleep(delay)

    raise GeminiServiceError(
        f"Gemini khong phan hoi sau toi da 3 lan thu. "
        f"Model={model}. Loi cuoi: "
        f"{type(last_error).__name__}: {str(last_error)[:500]}"
    ) from last_error
