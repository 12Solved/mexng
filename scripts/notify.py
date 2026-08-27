"""
Operator alert channel. `notify()` emails the digest when ALERT_SMTP_* is
configured and `recipients` are given, else prints. Never raises, never uses
`logging` (would recurse into the DB-backed logging pipeline).
"""
import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def _smtp_config() -> dict | None:
    host = os.getenv("ALERT_SMTP_HOST")
    if not host:
        return None
    user = os.getenv("ALERT_SMTP_USER") or None
    return {
        "host": host,
        "port": int(os.getenv("ALERT_SMTP_PORT", "587")),
        "user": user,
        "password": os.getenv("ALERT_SMTP_PASSWORD") or None,
        "from_addr": os.getenv("ALERT_SMTP_FROM") or user,
    }


def _print_digest(subject: str, body: str, meta: dict | None) -> None:
    print(f"[NOTIFY] {subject}")
    print(body)
    if meta:
        print(f"[NOTIFY meta] {meta}")


def _send_email(cfg: dict, recipients: list[str], subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = cfg["from_addr"]
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(cfg["host"], cfg["port"]) as smtp:
        smtp.ehlo()
        if smtp.has_extn("starttls"):
            smtp.starttls()
            smtp.ehlo()
        if cfg["user"]:
            smtp.login(cfg["user"], cfg["password"])
        smtp.send_message(msg)


def notify(
    subject: str,
    body: str,
    recipients: list[str] | None = None,
    meta: dict | None = None,
) -> None:
    cfg = _smtp_config()
    if not recipients or cfg is None:
        _print_digest(subject, body, meta)
        return

    try:
        _send_email(cfg, recipients, subject, body)
    except Exception as e:
        print(f"[NOTIFY] SMTP send failed ({e}); falling back to print")
        _print_digest(subject, body, meta)
