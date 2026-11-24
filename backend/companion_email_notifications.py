"""Email delivery for explicitly consented and approved Companion reminders."""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from .temporal_action_worker import RetryableActionError
except ImportError:
    from temporal_action_worker import RetryableActionError


def make_reminder_email_handler(db):
    """Send only to the owner's verified Auth email with task-scoped idempotency."""
    def send_reminder(user_id: str, arguments: dict) -> dict:
        if arguments.get("delivery_channel") != "email":
            raise ValueError("Email delivery was not explicitly selected.")
        if arguments.get("email_consent") is not True or not arguments.get("email_consent_recorded_at"):
            raise ValueError("Explicit email reminder consent is required.")
        task_id = str(arguments.get("_action_task_id", "")).strip()
        if not task_id:
            raise ValueError("A persisted action task ID is required for idempotent delivery.")

        api_key = os.getenv("RESEND_API_KEY", "").strip()
        from_email = os.getenv("RESEND_FROM_EMAIL", "").strip()
        if not api_key or not from_email:
            raise ValueError("Resend email service is not configured.")

        try:
            auth_result = db.auth.admin.get_user_by_id(user_id)
        except Exception as exc:
            raise RetryableActionError("Could not verify reminder recipient.") from exc
        user = getattr(auth_result, "user", None) or auth_result
        email_address = getattr(user, "email", None)
        verified_at = getattr(user, "email_confirmed_at", None)
        if not email_address or not verified_at:
            raise ValueError("A verified account email is required for reminders.")

        title = str(arguments.get("title", "")).strip()
        due_at = str(arguments.get("due_at", "")).strip()
        if not title or len(title) > 180 or not due_at:
            raise ValueError("Reminder title and due time are required.")

        payload = {
            "from": from_email,
            "to": [email_address],
            "subject": f"Y TẾ MỞ — Nhắc lịch: {title}",
            "text": (
                f"Bạn có một lời nhắc đã xác nhận trong Y TẾ MỞ.\n\n"
                f"Nội dung: {title}\nThời gian: {due_at}\n\n"
                "Đây là email nhắc lịch, không phải tư vấn y khoa."
            ),
        }
        request = Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": f"ytemo-reminder-{task_id}",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            # Resend documents 409 for concurrent idempotent requests; retry it
            # with the same task key and payload. Retry throttling/server errors.
            if exc.code == 409 or exc.code == 429 or exc.code >= 500:
                raise RetryableActionError(f"Resend temporarily returned HTTP {exc.code}.") from exc
            raise ValueError(f"Resend rejected the reminder with HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RetryableActionError("Resend network request failed.") from exc

        message_id = result.get("id")
        if not message_id:
            raise RetryableActionError("Email provider did not return a message ID.")
        return {"provider": "resend", "message_id": message_id, "recipient": email_address}

    return send_reminder
