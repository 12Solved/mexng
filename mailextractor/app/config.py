import os

from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")

    if DATABASE_URL is None:
        raise ValueError("DATABASE_URL is not set")

    # Email provider configuration
    EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "imap")  # "imap" or "glob"
    FILE_EXTRACT_PATH = os.getenv("FILE_EXTRACT_PATH", "/")

    # IMAP configuration
    IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
    IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
    IMAP_USERNAME = os.getenv("IMAP_USERNAME", "")
    IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "")
    IMAP_USE_SSL = os.getenv("IMAP_USE_SSL", "true").lower() == "true"
    IMAP_MAILBOX = os.getenv("IMAP_MAILBOX", "INBOX")

    # GLOB configuration (comma-separated file glob patterns)
    GLOB_PATTERNS = os.getenv("GLOB_PATTERNS", "")

    # Poller checkpoint file (keep separate per provider/run to avoid clobbering the live poller's state)
    CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", "checkpoint.txt") or None  # "" -> no checkpoint, fetch everything

config = Config()
