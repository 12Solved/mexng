import os

from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")

    if DATABASE_URL is None:
        raise ValueError("DATABASE_URL is not set")

    # Email provider configuration
    EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "gmail")  # "gmail" or "imap"
    FILE_EXTRACT_PATH = os.getenv("FILE_EXTRACT_PATH", "/")
    # Gmail configuration
    GMAIL_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "app/poller/credentials.json")
    GMAIL_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "app/poller/token.json")

    # IMAP configuration
    IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
    IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
    IMAP_USERNAME = os.getenv("IMAP_USERNAME", "")
    IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "")
    IMAP_USE_SSL = os.getenv("IMAP_USE_SSL", "true").lower() == "true"
    IMAP_MAILBOX = os.getenv("IMAP_MAILBOX", "INBOX")

config = Config()
