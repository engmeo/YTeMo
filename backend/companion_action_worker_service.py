"""Standalone process entrypoint for the Companion action worker."""
import os

from supabase import create_client

from companion_email_notifications import make_reminder_email_handler
from temporal_action_worker import register_handler, serve


def main() -> None:
    url = os.environ["SUPABASE_URL"]
    secret = os.environ["SUPABASE_SECRET_KEY"]
    if not os.getenv("RESEND_API_KEY") or not os.getenv("RESEND_FROM_EMAIL"):
        raise RuntimeError("RESEND_API_KEY and RESEND_FROM_EMAIL are required.")
    db = create_client(url, secret)
    register_handler("create_reminder", make_reminder_email_handler(db))
    print("Companion worker started; email reminder handler registered.", flush=True)
    serve(db)


if __name__ == "__main__":
    main()
