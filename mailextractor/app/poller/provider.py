"""Mail providers: fetch mail (IMAP or local .eml glob) into a common dict shape."""
from abc import ABC, abstractmethod
from typing import TypedDict, Optional, Any, Iterator
from datetime import datetime, timedelta
import imaplib
from logging import Logger
import json
import time
import re
import glob
from email import message_from_bytes, policy
from email.header import decode_header, make_header
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
import hashlib
from bs4 import BeautifulSoup
import os

from mailextractor.models import Email, Attachment

def _html_to_plain(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)

class AttachmentDict(TypedDict):
    filename: str
    content_type: str
    size: int
    content: bytes

class MailDict(TypedDict):
    message_id: str
    subject: str
    sender: str
    recipient: str
    date: datetime
    body: str
    html_body: str
    raw_headers: dict[str, str]
    attachments: list[AttachmentDict]
    imap_uid: Optional[int]
    email_account: str
    hash: str

class Checkpoint(TypedDict):
    dt: Optional[datetime]
    hash: Optional[str]

class BaseProvider(ABC):
    """Common interface: connect, iterate_mails, disconnect; tracks a date/hash checkpoint."""
    def __init__(self, logger: Optional[Logger], checkpoint_path: str | datetime):
        self._checkpoint_path = checkpoint_path
        self._logger = logger

    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    def update_checkpoint(self, checkpoint: Checkpoint) -> None:
        cp = self._checkpoint_path
        if isinstance(cp, datetime):
            self._checkpoint_path = checkpoint["dt"]
            if self._logger: self._logger.info(f"Checkpoint updated in-memory (dt={checkpoint['dt']})", extra={"event_type": "CHECKPOINT_UPDATED"})
            return
        with open(cp, "w") as f:
            json.dump({
                "dt": checkpoint["dt"].isoformat() if checkpoint["dt"] else None,
                "hash": checkpoint["hash"],
            }, f)
        if self._logger: self._logger.info(f"Checkpoint written to {cp} (dt={checkpoint['dt']})", extra={"event_type": "CHECKPOINT_UPDATED"})

    def get_checkpoint(self) -> Checkpoint:
        cp = self._checkpoint_path
        if isinstance(cp, datetime):
            if self._logger: self._logger.info(f"Using in-memory checkpoint {cp}", extra={"event_type": "CHECKPOINT_LOADED"})
            return {"dt": cp, "hash": None}
        try:
            with open(cp, "r") as f:
                data = json.load(f)
                dt_raw = data.get("dt")
                if self._logger: self._logger.info(f"Checkpoint loaded from {cp} (dt={dt_raw})", extra={"event_type": "CHECKPOINT_LOADED"})
                return {
                    "dt": datetime.fromisoformat(dt_raw) if dt_raw else None,
                    "hash": data.get("hash"),
                }
        except FileNotFoundError:
            if self._logger: self._logger.warning(f"Checkpoint file not found, creating {cp}", extra={"event_type": "CHECKPOINT_CREATED"})
            with open(cp, "w") as f:
                json.dump({"dt": None, "hash": None}, f)
            return {"dt": None, "hash": None}

    @abstractmethod
    def iterate_mails(self) -> Iterator[MailDict]:
        ...

    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, *exc):
        self.disconnect()
        return False

class IMAPProvider(BaseProvider):
    """Fetches mail over IMAP, batched with retries, filtered by checkpoint date/hash."""
    def __init__(self, host: str, port: int, username: str, password: str, use_ssl: bool, mailbox: str, logger: Optional[Logger] = None, checkpoint_path: str | datetime = 'checkpoint.txt', batch_size: int = 50, max_retries: int = 3):
        super().__init__(logger, checkpoint_path)
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_ssl = use_ssl
        self._mailbox = mailbox

        self._batch_size = batch_size
        self._max_retries = max_retries
        
        self._connection = None

    def connect(self) -> None:
        try:
            if self._use_ssl:
                connection = imaplib.IMAP4_SSL(self._host, self._port, timeout=60)
            else:
                connection = imaplib.IMAP4(self._host, self._port, timeout=60)
            connection.login(self._username, self._password)
            status, _ = connection.select(self._mailbox, readonly=True)
            if status != "OK":
                raise Exception(f"Failed to select mailbox: {self._mailbox}")
            self._connection = connection
            if self._logger: self._logger.info(f"IMAP connection established", extra={"event_type": "IMAP_CONNECTION_ESTABLISHED"})
            return
        except imaplib.IMAP4.error as e:
            if self._logger: self._logger.error("IMAP authentication failed", extra={"event_type": "IMAP_AUTH_FAILED", "error": str(e)})
            raise
        except Exception as e:
            if self._logger: self._logger.error("IMAP connection failed", extra={"event_type": "IMAP_CONNECTION_FAILED", "error": str(e)})
            raise
        return None

    def disconnect(self) -> None:
        if self._connection:
            try:
                self._connection.close()
                self._connection.logout()
                if self._logger: self._logger.info("IMAP connection closed", extra={"event_type": "IMAP_CONNECTION_CLOSED"})
            except Exception as e:
                if self._logger: self._logger.warning("IMAP connection close error", extra={"event_type": "IMAP_CONNECTION_CLOSE_ERROR", "error": str(e)})
            finally:
                self._connection = None
        return None

    def iterate_mails(self) -> Iterator[MailDict]:
        cp = self.get_checkpoint()
        dt = cp['dt']
        hash = cp['hash']
        uids = self._fetch_uids(cp['dt'])
        batch_size = self._batch_size
        max_retries = self._max_retries
        n_emails = 0
        for i in range(0, len(uids), batch_size):
            batch = uids[i:i + batch_size]
            uid_set = ",".join(str(u) for u in batch)

            # Retry logic
            for attempt in range(max_retries):
                try:
                    status, msg_data = self._connection.uid("fetch", uid_set, "(RFC822)")
                    if status != "OK":
                        if self._logger: self._logger.warning(f"UID FETCH failed for batch {i}, attempt {attempt+1}/{max_retries}", extra={"event_type": "IMAP_FETCH_BATCH_FAILED"})
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        break  # Give up after max retries
                    for item in msg_data:
                        if not isinstance(item, tuple) or len(item) != 2:
                            continue
                        parsed = self._parse_message(item[0], item[1])
                        if dt and (parsed['date'] < dt):
                            continue
                        if hash and (hash == parsed['hash']):
                            continue
                        
                        yield parsed
                        n_emails = n_emails + 1
                    break  # Success, move to next batch
                except Exception as e:
                    if self._logger: self._logger.exception(f"Error fetching batch {i}, attempt {attempt+1}/{max_retries}", extra={"event_type": "IMAP_FETCH_BATCH_ERROR"})
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                    # If last attempt fails, continue to next batch
        if self._logger: self._logger.info(f"Fetched {n_emails} messages", extra={"event_type": "IMAP_FETCH_COMPLETE", "count": n_emails})

    def _fetch_uids(self, dt: Optional[datetime] = None) -> list[int]:
        try:
            if dt is None:
                criteria = "ALL"
            else:
                # IMAP SINCE format: 01-Jan-2026 (day has no leading zero requirement,
                # but %d gives zero-padded which servers accept)
                criteria = f'SINCE {dt.strftime("%d-%b-%Y")}'
            status, data = self._connection.uid("search", None, criteria)
            uids = [int(u) for u in data[0].split()]
            if self._logger: self._logger.info(f"Found {len(uids)} new UIDs (since {dt})", extra={"event_type": "IMAP_UIDS_RETRIEVED", "count": len(uids)})
        except Exception as e:
            if self._logger: self._logger.exception(f"UID SEARCH failed with filter '{criteria}'", extra={"event_type": "IMAP_SEARCH_FAILED", "error": str(e)})
            raise
        return uids

    def _parse_message(self, response_line: bytes, raw_email: bytes) -> dict | None:
        try:
            uid_match = re.search(rb"UID (\d+)", response_line)
            uid = uid_match.group(1).decode() if uid_match else None

            msg = message_from_bytes(raw_email)

            date = None
            date_str = msg.get("Date")
            if date_str:
                try:
                    date = parsedate_to_datetime(date_str)
                except Exception:
                    if self._logger: self._logger.warning(f"Could not parse date: {date_str}", extra={"event_type": "IMAP_DATE_PARSE_FAILED"})

            attachments, html_body, plain_body = self._extract_message_parts(msg)

            subject = self._decode_header_value(msg.get("Subject"))
            sender = self._decode_header_value(msg.get("From"))
            recipient = self._decode_header_value(msg.get("To"))
            date = date
    
            hash = hashlib.sha256(f"{subject}|{sender}|{recipient}|{date.isoformat() if date else ''}".encode()).hexdigest()
            
            return {
                "message_id": msg.get("Message-ID"),
                "subject": subject,
                "sender": sender,
                "recipient": recipient,
                "date": date,
                "body": plain_body,
                "html_body": html_body,
                "raw_headers": {k: str(v) for k, v in msg.items()},
                "attachments": attachments,
                "imap_uid": uid,
                "email_account": self._username,
                "hash": hash
            }
        except Exception as e:
            if self._logger: self._logger.exception("Error parsing IMAP message", extra={"event_type": "IMAP_MESSAGE_PARSE_ERROR", "error": str(e)})
            raise
            return None

    def _decode_header_value(self, value: str | None) -> str | None:
        if not value:
            return None
        return str(make_header(decode_header(value)))

    def _extract_message_parts(self, msg):
        attachments = []
        html_body = None
        plain_body = None

        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue

            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in disposition:
                filename = part.get_filename()
                if filename:
                    payload = part.get_payload(decode=True)
                    attachments.append({
                        "filename": self._decode_header_value(filename),
                        "content_type": content_type,
                        "size": len(payload) if payload else 0,
                        "content": payload,
                    })
            elif content_type == "text/html" and html_body is None:
                payload = part.get_payload(decode=True)
                if payload:
                    html_body = payload.decode("utf-8", errors="replace")
            elif content_type == "text/plain" and plain_body is None:
                payload = part.get_payload(decode=True)
                if payload:
                    plain_body = payload.decode("utf-8", errors="replace")

        return attachments, html_body, plain_body

class GLOBProvider(BaseProvider):
    """Reads local .eml files matching glob patterns, filtered by checkpoint date/hash."""
    def __init__(self, patterns: list[str], logger: Optional[Logger] = None, checkpoint_path: str | datetime = 'checkpoint.txt'):
        super().__init__(logger, checkpoint_path)
        self._patterns = patterns

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None

    def iterate_mails(self) -> Iterator[MailDict]:
        cp = self.get_checkpoint()
        dt = cp['dt']
        hash = cp['hash']

        email_paths = []
        for pattern in self._patterns:
            matched = glob.glob(pattern)
            if matched:
                email_paths.extend(matched)
            else:
                email_paths.append(pattern) # Add the original pattern if no matches found

        if not email_paths:
            if self._logger: self._logger.warning(f"No email files found.", extra={"event_type": "GLOB_NO_EMAIL"})

        success_count = 0
        skipped_count = 0
        failure_count = 0

        for email_path in email_paths:
            try:
                parsed = self._parse_message(email_path)
                if dt and parsed['date'] and parsed['date'] < dt:
                    skipped_count += 1
                    continue
                if hash and hash == parsed['hash']:
                    skipped_count += 1
                    continue
                yield parsed
                success_count += 1
            except Exception as e:
                if self._logger: self._logger.exception(e, extra={"event_type": "GLOB_ERROR"})
                failure_count += 1
                raise
        if self._logger: self._logger.info(f"Fetched {success_count} messages. Skipped {skipped_count}. Failed {failure_count}", extra={"event_type": "GLOB_FETCH_COMPLETE", "count": success_count})

    def _parse_message(self, email_path) -> dict | None:
        if not os.path.exists(email_path):
            raise Exception(f"{email_path}: File not found")

        with open(email_path, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)

        attachments = []
        html_body = None
        plain_body = None

        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = part.get_content_disposition()
                content_type = part.get_content_type()

                if content_disposition == "attachment":
                    file_content = part.get_payload(decode=True)
                    filename = part.get_filename()
                    attachments.append(AttachmentDict(
                        filename=filename,
                        content_type=content_type,
                        size=len(file_content) if file_content else 0,
                        content=file_content
                    ))
                elif content_type == "text/html" and content_disposition is None and html_body is None:
                    html_body = part.get_content()
                elif content_type == "text/plain" and content_disposition is None and plain_body is None:
                    plain_body = part.get_content()
        else:
            if msg.get_content_type() == "text/html":
                html_body = msg.get_content()
            else:
                plain_body = msg.get_content()

        body = plain_body if plain_body is not None else (_html_to_plain(html_body) if html_body else "")
        raw_headers = dict(msg.items())

        subject = msg.get('Subject')
        sender = msg.get('From')
        recipient = msg.get('To')

        date = None
        date_str = msg.get('Date')
        if date_str:
            try:
                date = parsedate_to_datetime(date_str)
            except Exception:
                if self._logger: self._logger.warning(f"Could not parse date: {date_str}", extra={"event_type": "GLOB_DATE_PARSE_FAILED"})

        hash = hashlib.sha256(f"{subject}|{sender}|{recipient}|{date.isoformat() if date else ''}".encode()).hexdigest()

        res = {
            "message_id": msg.get('Message-ID'),
            "subject": subject,
            "sender": sender,
            "recipient": recipient,
            "date": date,
            "body": body,
            "html_body": html_body,
            "raw_headers": raw_headers,
            "attachments": attachments,
            "imap_uid": None,
            "email_account": email_path,
            "hash": hash
        }
        return res

def get_provider(config, logger: Optional[Logger] = None, checkpoint_path: str | datetime = 'checkpoint.txt') -> BaseProvider:
    """Build the provider selected by config.EMAIL_PROVIDER (imap or glob)."""
    provider_type = config.EMAIL_PROVIDER.lower()
    if provider_type == "gmail":
        if logger: logger.error("gmail provider no longer supported", extra={"event_type": "NOT_SUPPORTED_PROVIDER"})
        raise ValueError("gmail provider no longer supported")
    elif provider_type == "imap":
        if not config.IMAP_USERNAME or not config.IMAP_PASSWORD:
            raise ValueError("IMAP_USERNAME and IMAP_PASSWORD must be set for IMAP provider")
        provider = IMAPProvider(
            host=config.IMAP_HOST,
            port=config.IMAP_PORT,
            username=config.IMAP_USERNAME,
            password=config.IMAP_PASSWORD,
            use_ssl=config.IMAP_USE_SSL,
            mailbox=config.IMAP_MAILBOX,
            logger = logger,
            checkpoint_path = checkpoint_path
        )
        if logger: logger.info(f"Using IMAP provider ({config.IMAP_HOST})", extra={"event_type": "PROVIDER_SELECTED"})
    elif provider_type == "glob":
        if not config.GLOB_PATTERNS:
            raise ValueError("GLOB_PATTERNS must be set for GLOB provider")
        provider = GLOBProvider(
            patterns=[p.strip() for p in config.GLOB_PATTERNS.split(",") if p.strip()],
            logger = logger,
            checkpoint_path = checkpoint_path
        )
        if logger: logger.info(f"Using GLOB provider", extra={"event_type": "PROVIDER_SELECTED"})
    else:
        raise ValueError(f"Unknown EMAIL_PROVIDER: {provider_type}. Use 'imap' or 'glob'")
    return provider