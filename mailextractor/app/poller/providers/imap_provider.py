import imaplib
import logging
import re
import time
from email import message_from_bytes
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)


class IMAPProvider:

    def __init__(
        self,
        host: str,
        port: int = 993,
        username: str = "",
        password: str = "",
        use_ssl: bool = True,
        mailbox: str = "INBOX"
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.mailbox = mailbox
        self.connection = None

    def connect(self):
        try:
            if self.use_ssl:
                connection = imaplib.IMAP4_SSL(self.host, self.port, timeout=60)
            else:
                connection = imaplib.IMAP4(self.host, self.port, timeout=60)

            connection.login(self.username, self.password)

            status, _ = connection.select(self.mailbox, readonly=True)
            if status != "OK":
                raise Exception(f"Failed to select mailbox: {self.mailbox}")

            self.connection = connection
            logger.info(f"IMAP connection established",
                        extra={"event_type": "IMAP_CONNECTION_ESTABLISHED"})
            return connection

        except imaplib.IMAP4.error as e:
            logger.error("IMAP authentication failed",
                         extra={"event_type": "IMAP_AUTH_FAILED", "error": str(e)})
            raise
        except Exception as e:
            logger.error("IMAP connection failed",
                         extra={"event_type": "IMAP_CONNECTION_FAILED", "error": str(e)})
            raise

    def disconnect(self):
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info("IMAP connection closed",
                            extra={"event_type": "IMAP_CONNECTION_CLOSED"})
            except Exception as e:
                logger.warning("IMAP connection close error",
                               extra={"event_type": "IMAP_CONNECTION_CLOSE_ERROR", "error": str(e)})
            finally:
                self.connection = None

    def fetch_mailbox_state(self) -> dict:
        """Fetch current UIDVALIDITY and UIDNEXT from the server."""
        try:
            status, data = self.connection.status(self.mailbox, "(UIDVALIDITY UIDNEXT)")
            if status == "OK" and data:
                raw = data[0]
                uidvalidity = re.search(rb"UIDVALIDITY (\d+)", raw)
                uidnext = re.search(rb"UIDNEXT (\d+)", raw)
                return {
                    "uidvalidity": uidvalidity.group(1).decode() if uidvalidity else None,
                    "uidnext": uidnext.group(1).decode() if uidnext else None,
                }
        except Exception as e:
            logger.warning(f"Could not fetch mailbox state: {e}",
                           extra={"event_type": "IMAP_MAILBOX_STATE_FAILED"})
        return {"uidvalidity": None, "uidnext": None}

    def fetch_uids(self, since_uid: int, search_filter: str | None = None) -> list[int]:
        """Search for UIDs >= since_uid, optionally narrowed by an IMAP search filter."""
        uid_range = f"UID {since_uid}:*"
        criteria = f"{uid_range} {search_filter}" if search_filter else uid_range

        try:
            status, data = self.connection.uid("search", None, criteria)
        except Exception:
            logger.warning(f"UID SEARCH failed with filter '{search_filter}', retrying without filter",
                           extra={"event_type": "IMAP_SEARCH_INVALID"})
            try:
                status, data = self.connection.uid("search", None, uid_range)
            except Exception:
                logger.exception("UID SEARCH failed", extra={"event_type": "IMAP_SEARCH_FAILED"})
                return []

        if status != "OK" or not data or not data[0]:
            return []

        uids = [int(u) for u in data[0].split() if int(u) >= since_uid]
        logger.info(f"Found {len(uids)} new UIDs (since {since_uid})",
                    extra={"event_type": "IMAP_UIDS_RETRIEVED", "count": len(uids)})
        return uids

    def fetch_messages(self, uids: list[int], batch_size: int = 50, max_retries: int = 3) -> list[dict]:
        """Fetch and parse full messages for the given UID list, in batches."""
        emails = []
        for i in range(0, len(uids), batch_size):
            batch = uids[i:i + batch_size]
            uid_set = ",".join(str(u) for u in batch)
            
            # Retry logic
            for attempt in range(max_retries):
                try:
                    status, msg_data = self.connection.uid("fetch", uid_set, "(RFC822)")
                    if status != "OK":
                        logger.warning(f"UID FETCH failed for batch {i}, attempt {attempt+1}/{max_retries}",
                                   extra={"event_type": "IMAP_FETCH_BATCH_FAILED"})
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        break  # Give up after max retries
                    
                    for item in msg_data:
                        if not isinstance(item, tuple) or len(item) != 2:
                            continue
                        parsed = self._parse_message(item[0], item[1])
                        if parsed:
                            emails.append(parsed)
                    break  # Success, move to next batch
                    
                except Exception as e:
                    logger.exception(f"Error fetching batch {i}, attempt {attempt+1}/{max_retries}",
                                 extra={"event_type": "IMAP_FETCH_BATCH_ERROR"})
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                    # If last attempt fails, continue to next batch

        logger.info(f"Fetched {len(emails)} messages",
                    extra={"event_type": "IMAP_FETCH_COMPLETE", "count": len(emails)})
        return emails

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
                    logger.warning(f"Could not parse date: {date_str}",
                                   extra={"event_type": "IMAP_DATE_PARSE_FAILED"})

            attachments, html_body, plain_body = self._extract_message_parts(msg)

            return {
                "message_id": msg.get("Message-ID"),
                "subject": self._decode_header_value(msg.get("Subject")),
                "sender": self._decode_header_value(msg.get("From")),
                "recipient": self._decode_header_value(msg.get("To")),
                "date": date,
                "body": plain_body,
                "html_body": html_body,
                "raw_headers": {k: str(v) for k, v in msg.items()},
                "attachments": attachments,
                "imap_uid": uid,
                "email_account": self.username,
            }
        except Exception as e:
            logger.exception("Error parsing IMAP message",
                             extra={"event_type": "IMAP_MESSAGE_PARSE_ERROR", "error": str(e)})
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
