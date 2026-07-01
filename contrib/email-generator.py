#!/usr/bin/env python3
"""
Generate dummy .eml files for testing.

Usage:
    python email-generator <count> <dst_dir>

Example:
    python email-generator 50 ./test-emails
"""

import argparse
import os
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

SUBJECT_WORDS = [
    "Invoice", "Receipt", "Order", "Confirmation", "Notification",
    "Update", "Report", "Statement", "Reminder", "Alert",
    "Newsletter", "Offer", "Promotion", "Summary", "Request",
    "Delivery", "Shipment", "Refund", "Payment", "Subscription",
]

BODY_SENTENCES = [
    "Please find the details attached.",
    "Your request has been processed successfully.",
    "We wanted to keep you updated on the latest changes.",
    "Thank you for your continued support.",
    "This is an automated message, please do not reply.",
    "Kindly review the information below.",
    "Let us know if you have any questions.",
    "Action may be required on your part.",
    "We appreciate your patience.",
    "Your account has been updated.",
    "A new transaction has been recorded.",
    "Please confirm receipt of this message.",
    "The following items require your attention.",
    "No further action is needed at this time.",
    "Contact our support team for assistance.",
]

FIRST_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank"]
LAST_NAMES  = ["Smith", "Jones", "Brown", "Taylor", "Wilson", "Davis", "Clark"]
DOMAINS     = ["example.com", "mail.test", "demo.org", "fakemail.io"]

def _random_address() -> tuple[str, str]:
    """Return (display_name, email_address)."""
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    local = name.lower().replace(" ", ".")
    domain = random.choice(DOMAINS)
    return name, f"{local}@{domain}"


def _random_subject(number: int) -> str:
    """Subject with a number and 1-3 random words."""
    words = random.sample(SUBJECT_WORDS, k=random.randint(1, 3))
    return f"{number} - {' '.join(words)}"


def _random_body(max_bytes: int = 700) -> str:
    """Build a short plain-text body that stays under max_bytes."""
    lines: list[str] = []
    used = 0
    # greeting
    greeting = f"Dear {random.choice(FIRST_NAMES)},\n\n"
    lines.append(greeting)
    used += len(greeting.encode())

    sentences = random.sample(BODY_SENTENCES, k=len(BODY_SENTENCES))
    for sentence in sentences:
        chunk = sentence + " "
        if used + len(chunk.encode()) > max_bytes:
            break
        lines.append(chunk)
        used += len(chunk.encode())

    sign_off = f"\n\nRegards,\n{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}\n"
    if used + len(sign_off.encode()) <= max_bytes:
        lines.append(sign_off)

    return "".join(lines)


def _random_date() -> str:
    """RFC 2822 date within the past 90 days."""
    delta = timedelta(days=random.randint(0, 90), seconds=random.randint(0, 86400))
    dt = datetime.now(tz=timezone.utc) - delta
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def generate_eml(number: int) -> bytes:
    """Build a single .eml file and return its raw bytes."""
    msg = EmailMessage()

    sender_name, sender_addr = _random_address()
    recip_name,  recip_addr  = _random_address()

    msg["From"]       = f"{sender_name} <{sender_addr}>"
    msg["To"]         = f"{recip_name} <{recip_addr}>"
    msg["Subject"]    = _random_subject(number)
    msg["Message-ID"] = f"<{uuid.uuid4().hex}@{sender_addr.split('@')[1]}>"
    msg["Date"]       = _random_date()
    msg["MIME-Version"] = "1.0"

    msg.set_content(_random_body())

    return bytes(msg)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate dummy .eml files for testing."
    )
    parser.add_argument("count", type=int, help="Number of emails to generate")
    parser.add_argument("dst",   type=str, help="Destination directory")
    args = parser.parse_args()

    if args.count < 1:
        parser.error("count must be at least 1")

    os.makedirs(args.dst, exist_ok=True)

    for i in range(1, args.count + 1):
        eml_bytes = generate_eml(i)
        filename  = os.path.join(args.dst, f"email-{i:04d}.eml")
        with open(filename, "wb") as f:
            f.write(eml_bytes)
        print(f"  [{i:>{len(str(args.count))}}] {filename}  ({len(eml_bytes)} bytes)")

    print(f"\nDone — {args.count} email(s) written to '{args.dst}'")


if __name__ == "__main__":
    main()
