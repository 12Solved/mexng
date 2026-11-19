"""
Operator alert channel. `notify()` emails the digest when ALERT_SMTP_* is
configured and `recipients` are given, else prints (plain text only). An
optional `html` body is sent alongside the plain text as an alternative.
Never raises, never uses `logging` (would recurse into the DB-backed
logging pipeline).
"""
import os
import smtplib
import ssl
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

SMTP_TIMEOUT_SECONDS = 30
IMPLICIT_TLS_PORT = 465


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


def _send_email(cfg: dict, recipients: list[str], subject: str, body: str, html: str | None) -> None:
    msg = EmailMessage()
    msg["From"] = cfg["from_addr"]
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        # multipart/alternative: clients render the HTML, plain text is the fallback.
        msg.add_alternative(html, subtype="html")

    # Verifies the server certificate; smtplib's default context does not.
    context = ssl.create_default_context()

    if cfg["port"] == IMPLICIT_TLS_PORT:
        smtp = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=SMTP_TIMEOUT_SECONDS, context=context)
    else:
        smtp = smtplib.SMTP(cfg["host"], cfg["port"], timeout=SMTP_TIMEOUT_SECONDS)

    with smtp:
        smtp.ehlo()
        if cfg["port"] != IMPLICIT_TLS_PORT:
            if smtp.has_extn("starttls"):
                smtp.starttls(context=context)
                smtp.ehlo()
            elif cfg["user"]:
                # A missing STARTTLS offer may be a downgrade attack; login()
                # would leak the password. Unauthenticated relays may go plain.
                raise smtplib.SMTPNotSupportedError("server does not offer STARTTLS")
        if cfg["user"]:
            smtp.login(cfg["user"], cfg["password"])
        smtp.send_message(msg)


def notify(
    subject: str,
    body: str,
    recipients: list[str] | None = None,
    meta: dict | None = None,
    html: str | None = None,
) -> bool:
    try:
        if not recipients:
            _print_digest(subject, body, meta)
            return True

        cfg = _smtp_config()
        if cfg is None:
            print("[NOTIFY] ALERT_SMTP_HOST not set; not sent, falling back to print")
            _print_digest(subject, body, meta)
            return False

        _send_email(cfg, recipients, subject, body, html)
        return True
    except Exception as e:
        print(f"[NOTIFY] send failed ({e}); falling back to print")
        _print_digest(subject, body, meta)
        return False
