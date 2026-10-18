
import email
import logging
from pathlib import Path
import base64
import re
from html.parser import HTMLParser
from email.utils import parseaddr
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def authenticate():
    """Authenticate with Google and return valid OAuth credentials."""

    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            "credentials.json is missing from the project root."
        )

    creds = None

    # Reuse credentials from a previous login.
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES,
        )

    # Refresh an expired access token if possible.
    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = None

    # Open the browser when authorization is needed.
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            SCOPES,
        )

        creds = flow.run_local_server(port=0)

    # Persist the token locally for subsequent runs.
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    # Restrict file permissions on systems that support chmod.
    try:
        TOKEN_FILE.chmod(0o600)
    except OSError:
        logger.warning("Could not restrict token file permissions.")

    logger.info("Google OAuth authentication successful.")
    return creds


def list_unread_messages(service, limit=10):
    """Return a bounded list of unread inbox message references."""

    response = (
        service.users()
        .messages()
        .list(
            userId="me",
            q="in:inbox is:unread",
            maxResults=limit,
        )
        .execute()
    )

    return response.get("messages", [])


def get_email_details(service, message_id):
    """Fetch one email's full payload."""

    return (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="full",
        )
        .execute()
    )


def get_header(headers, name):
    """Find a header by name, ignoring case."""

    for header in headers or []:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")

    return ""


def decode_body(data):
    """Decode a Gmail URL-safe Base64 body."""
    if not data:
        return ""

    padded = data + "=" * (-len(data) % 4)
    decoded = base64.urlsafe_b64decode(padded)

    return decoded.decode("utf-8", errors="replace")


"""def extract_body(payload):
    

    plain_parts = []
    html_parts = []

    def visit(part):
        data = (part.get("body") or {}).get("data")
        mime_type = part.get("mimeType", "")

        if data:
            content = decode_body(data)

            if mime_type == "text/plain":
                plain_parts.append(content)
            elif mime_type == "text/html":
                html_parts.append(content)

        for child in part.get("parts", []) or []:
            visit(child)

    visit(payload)

    if plain_parts:
        return "\n".join(plain_parts).strip()

    if html_parts:
        parser = HTMLTextExtractor()
        parser.feed("\n".join(html_parts))
        return re.sub(
            r"\s+", " ", "".join(parser.parts)
        ).strip()

    return ""
"""


import base64
import logging
import re
from html.parser import HTMLParser


logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """Convert HTML email content into readable text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip_depth += 1
        elif not self.skip_depth and tag in {
            "p", "div", "br", "li", "tr"
        }:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        elif not self.skip_depth and tag in {
            "p", "div", "li", "tr"
        }:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)


def decode_body(data):
    """Decode a Gmail URL-safe Base64 body."""
    if not data:
        return ""

    try:
        padded = data + "=" * (-len(data) % 4)
        raw = base64.urlsafe_b64decode(padded)
        return raw.decode("utf-8", errors="replace")
    except (ValueError, TypeError):
        logger.warning("Could not decode an email body part")
        return ""


def extract_body(payload):
    """Extract plain text, falling back to HTML."""

    plain_parts = []
    html_parts = []

    def visit(part):
        # Do not process attachment content as the email body.
        if part.get("filename"):
            return

        headers = part.get("headers", [])
        disposition = ""

        for header in headers:
            if header.get("name", "").lower() == "content-disposition":
                disposition = header.get("value", "").lower()
                break

        if "attachment" in disposition:
            return

        mime_type = part.get("mimeType", "")
        body_data = (part.get("body") or {}).get("data")

        if body_data:
            decoded = decode_body(body_data)

            if mime_type == "text/plain":
                plain_parts.append(decoded)
            elif mime_type == "text/html":
                html_parts.append(decoded)

        for child in part.get("parts", []) or []:
            visit(child)

    visit(payload)

    if plain_parts:
        return "\n".join(plain_parts).strip()

    if html_parts:
        parser = HTMLTextExtractor()
        parser.feed("\n".join(html_parts))
        parser.close()

        return re.sub(
            r"\s+", " ", "".join(parser.parts)
        ).strip()

    return ""


def fetch_unread_emails(service, limit=10):
    """Return structured records for unread inbox messages."""

    references = list_unread_messages(service, limit)
    emails = []

    for reference in references:
        message = get_email_details(service, reference["id"])
        payload = message.get("payload", {})
        headers = payload.get("headers", [])

        sender = get_header(headers, "From")

        emails.append({
            "id": message["id"],
            "thread_id": message.get("threadId", ""),
            "sender": parseaddr(sender)[1] or sender,
            "subject": get_header(headers, "Subject") or "(No subject)",
            "date": get_header(headers, "Date"),
            "body": extract_body(payload),
            "labels": message.get("labelIds", []),
        })

    return emails


def get_gmail_service():
    """Build an authenticated Gmail API client."""
    creds = authenticate()

    service = build(
        "gmail",
        "v1",
        credentials=creds,
        cache_discovery=False,
    )

    return service



def main():
    try:
        service = get_gmail_service()
        emails = fetch_unread_emails(service, limit=10)

        print(f"Fetched {len(emails)} unread emails.")

        for email in emails:
            print("-" * 50)
            print(f"ID: {email['id']}")
            print(f"From: {email['sender']}")
            print(f"Subject: {email['subject']}")
            print(f"Date: {email['date']}")
            print(f"Body length: {len(email['body'])} characters")
            print(f"Body preview: {email['body'][:500]}")

    except Exception:
        logger.exception("Email fetching failed.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
