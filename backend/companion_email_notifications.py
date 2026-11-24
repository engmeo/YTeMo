"""Email delivery for explicitly approved Companion reminders via Resend."""
from __future__ import annotations

import hashlib
import json
import os
from urllib.request import Request, urlopen


def make_reminder_email_handler(db):
    """Return a worker handler that sends only to the owner's verified Auth email."""
    def send_reminder(user_id: str, arguments: dict) -> dict:
        if arguments.get("delivery_channel") != "email":
            raise ValueError("Email delivery was not explicitly selected.")
        api_key = os.getenv("RESEND_API_KEY", "").strip()
        from_email = os.getenv("RESEND_FROM_EMAIL", "").strip()
        if not api_key or not from_email:
            raise RuntimeError("Resend email service is not configured.")

        auth_result = db.auth.admin.get_user_by_id(user_id)
        user = getattr(auth_result, "user", None) or auth_result
        email_address = getattr(user, "email", None)
        verified_at = getattr(user, "email_confirmed_at", None)
        if not email_address or not verified_at:
            raise ValueError("A verified account email is required for reminders.")

        title = str(arguments.get("title", "")).strip()
        due_at = str(arguments.get("due_at", "")).strip()
        if not title or not due_at:
            raise ValueError("Reminder title and due time are required.")

        idempotency_key = hashlib.sha256(
            f"{user_id}|{title}|{due_at}".encode("utf-8")
        ).hexdigest()
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
                "Idempotency-Key": idempotency_key,
            },
            method="POST",
        )
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
        message_id = result.get("id")
        if not message_id:
            raise RuntimeError("Email provider did not return a message ID.")
        return {"provider": "resend", "message_id": message_id, "recipient": email_address}

    return send_reminder
