import base64
import contextlib
import logging
from email import message_from_bytes
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailProvider:
    def __init__(
        self,
        credentials_path: str = "/credentials.json",
        token_path: str = "token.json",
    ):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._authenticate()

    def _authenticate(self):
        """
        Whole function just for user Auth. Checks expiry date, if expired try to use refresh token.
        If refresh token is also expired, then opens a new windows to log back in
        """
        creds = None

        with contextlib.suppress(FileNotFoundError):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("Gmail token refreshed",
                            extra={"event_type": "GMAIL_TOKEN_REFRESHED"})
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Gmail OAuth flow completed",
                            extra={"event_type": "GMAIL_AUTH_COMPLETED"})

            with open(self.token_path, "w") as f:
                f.write(creds.to_json())

        return build("gmail", "v1", credentials=creds)

    def fetch(self, limit: int = 50) -> list[dict]:
        """
        Function to fetch all emails IDs, limit can be changed.
        """
        kwargs = dict(userId="me", q="in:inbox", maxResults=limit)
        results = self.service.users().messages().list(**kwargs).execute()
        messages = results.get("messages", [])

        if not messages:
            logger.info("No Gmail messages found",
                        extra={"event_type": "GMAIL_NO_MESSAGES"})
            return []

        emails = []
        for msg_ref in messages:
            try:
                email_data = self._fetch_message(msg_ref["id"])
                if email_data:
                    emails.append(email_data)
            except Exception:
                logger.exception(
                    "Failed to fetch Gmail message",
                    extra={"event_type": "GMAIL_MESSAGE_FETCH_FAILED"},
                )

        logger.info(f"Fetched {len(emails)} Gmail messages",
                    extra={"event_type": "GMAIL_FETCH_COMPLETE"})
        return emails

    def _decode_header_value(self, value: str | None) -> str | None:
        if not value:
            return None
        return str(make_header(decode_header(value)))

    def _fetch_message(self, gmail_message_id: str) -> dict | None:
        """
        This fetches the actual email, since the fetch function only gets a list of IDs
        """
        raw = (
            self.service.users()
            .messages()
            .get(userId="me", id=gmail_message_id, format="raw")
            .execute()
        )

        raw_bytes = base64.urlsafe_b64decode(raw["raw"])
        msg = message_from_bytes(raw_bytes)

        date = None
        date_str = msg.get("Date")
        if date_str:
            try:
                date = parsedate_to_datetime(date_str)
            except Exception:
                logger.warning(f"Could not parse date: {date_str}",
                               extra={"event_type": "GMAIL_DATE_PARSE_FAILED"})

        attachments = []
        html_body = None
        plain_body = None

        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            if part.get_content_maintype() == "multipart":
                continue

            if "attachment" in disposition:
                filename = part.get_filename()
                if filename:
                    payload = part.get_payload(decode=True)
                    attachments.append(
                        {
                            "filename": self._decode_header_value(filename),
                            "content_type": content_type,
                            "size": len(payload) if payload else 0,
                            "content": payload,
                        }
                    )
            elif content_type == "text/html" and html_body is None:
                payload = part.get_payload(decode=True)
                if payload:
                    html_body = payload.decode("utf-8", errors="replace")
            elif content_type == "text/plain" and plain_body is None:
                payload = part.get_payload(decode=True)
                if payload:
                    plain_body = payload.decode("utf-8", errors="replace")

        return {
            "message_id": msg.get("Message-ID"),
            "subject": self._decode_header_value(msg.get("Subject")),
            "sender": self._decode_header_value(msg.get("From")),
            "recipient": self._decode_header_value(msg.get("To")),
            "date": date,
            "body": plain_body,
            "html_body": html_body,
            "raw_headers": dict(msg.items()),
            "attachments": attachments,
        }
