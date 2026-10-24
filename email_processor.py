
import base64
import logging
import os
import re
from email.utils import parseaddr
from html.parser import HTMLParser
from pathlib import Path
import json
import boto3
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]

MAX_EMAILS = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# --------------------------------------------------
# OAuth Authentication
# --------------------------------------------------

def authenticate_from_aws_secret():
    """Authenticate Gmail using credentials stored in AWS Secrets Manager."""

    secret_name = os.getenv(
        "AWS_SECRET_NAME",
        "ai-email-assistant/production",
    )
    region = os.getenv("AWS_REGION", "ap-south-1")

    client = boto3.client("secretsmanager", region_name=region)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])

        client_info = json.loads(secret["GMAIL_CREDENTIALS_JSON"])
        token_info = json.loads(secret["GMAIL_TOKEN_JSON"])

        if not isinstance(client_info, dict) or not isinstance(token_info, dict):
            raise ValueError("Gmail OAuth credentials and token must be JSON objects.")

        if not client_info.get("installed") and not client_info.get("web"):
            raise ValueError("Gmail OAuth client configuration is missing.")

    except Exception as exc:
        logger.error("Unable to load Gmail credentials from AWS Secrets Manager.")
        raise RuntimeError(
            "Could not load Gmail credentials from AWS Secrets Manager. "
            "Check the secret name, region, IAM permissions, and secret format."
        ) from exc

    creds = Credentials.from_authorized_user_info(
        token_info,
        scopes=SCOPES,
    )

    if not creds.has_scopes(SCOPES):
        raise RuntimeError(
            "The Gmail OAuth token lacks required scopes. "
            "Reauthorize Gmail locally and update GMAIL_TOKEN_JSON in Secrets Manager."
        )

    if not creds.valid:
        if not creds.expired or not creds.refresh_token:
            raise RuntimeError(
                "The Gmail OAuth token is invalid or has no refresh token. "
                "Reauthorize locally and update GMAIL_TOKEN_JSON in Secrets Manager."
            )

        old_refresh_token = creds.refresh_token

        try:
            creds.refresh(Request())
        except RefreshError as exc:
            raise RuntimeError(
                "Gmail token refresh failed. Reauthorize locally and update "
                "GMAIL_TOKEN_JSON in Secrets Manager."
            ) from exc

        if creds.refresh_token != old_refresh_token:
            raise RuntimeError(
                "Google returned a different refresh token. Update "
                "GMAIL_TOKEN_JSON in Secrets Manager before retrying."
            )

    logger.info("Google OAuth authentication successful using AWS Secrets Manager.")
    return creds

def authenticate():
    """Load, refresh, or obtain Google OAuth credentials."""
    if os.getenv("AWS_SECRETS_MODE", "").lower() == "true":
        return authenticate_from_aws_secret()
    if not CREDENTIALS_FILE.is_file():
        raise FileNotFoundError(
            "credentials.json is missing from the project root."
        )

    creds = None

    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(TOKEN_FILE)
            )
        except (ValueError, OSError):
            logger.warning(
                "Saved OAuth token is invalid or unreadable."
            )

    if creds and not creds.has_scopes(SCOPES):
        logger.warning("Saved token lacks required scopes.")
        creds = None

    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                logger.warning(
                    "Token refresh failed; reauthorization required."
                )
                creds = None
        else:
            creds = None

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            SCOPES,
        )
        creds = flow.run_local_server(port=0)

    # Save the token with restrictive permissions where supported.
    fd = os.open(
        str(TOKEN_FILE),
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )

    with os.fdopen(fd, "w", encoding="utf-8") as token_file:
        token_file.write(creds.to_json())

    try:
        TOKEN_FILE.chmod(0o600)
    except OSError:
        logger.warning(
            "Could not set token file permissions."
        )

    logger.info("Google OAuth authentication successful.")
    return creds


def get_gmail_service():
    """Build an authenticated Gmail API client."""

    creds = authenticate()

    return build(
        "gmail",
        "v1",
        credentials=creds,
        cache_discovery=False,
    )


# --------------------------------------------------
# Gmail API Operations
# --------------------------------------------------

def validate_limit(limit):
    """Validate the maximum number of emails to fetch."""

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer.")

    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50.")

    return limit



def list_unread_messages(service, limit=MAX_EMAILS):
    """Return unread inbox messages not yet processed by our AI."""

    limit = validate_limit(limit)

    response = (
        service.users()
        .messages()
        .list(
            userId="me",
            q="in:inbox is:unread -label:AI/Processed",
            maxResults=limit,
        )
        .execute()
    )

    return response.get("messages", [])

def get_email_details(service, message_id):
    """Fetch a single message's full payload."""

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
    """Find an email header without case sensitivity."""

    for header in headers or []:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")

    return ""


# --------------------------------------------------
# Email Body Parsing
# --------------------------------------------------

class HTMLTextExtractor(HTMLParser):
    """Extract readable text from HTML email content."""

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
    """Decode Gmail's URL-safe Base64 body data."""

    if not data:
        return ""

    try:
        padded = data + "=" * (-len(data) % 4)
        decoded = base64.b64decode(
            padded,
            altchars=b"-_",
            validate=True,
        )
        return decoded.decode("utf-8", errors="replace")
    except (ValueError, TypeError):
        logger.warning("Could not decode an email body part.")
        return ""


def extract_body(payload):
    """Prefer plain text, falling back to HTML."""

    plain_parts = []
    html_parts = []

    def visit(part):
        # Skip attachments rather than treating them as message text.
        if part.get("filename"):
            return

        disposition = get_header(
            part.get("headers", []),
            "Content-Disposition",
        ).lower()

        if "attachment" in disposition:
            return

        mime_type = part.get("mimeType", "")
        body_data = (part.get("body") or {}).get("data")

        if body_data:
            content = decode_body(body_data)

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
        parser.close()

        return re.sub(
            r"\s+",
            " ",
            "".join(parser.parts),
        ).strip()

    return ""


# --------------------------------------------------
# Email Processing
# --------------------------------------------------

def fetch_unread_emails(service, limit=MAX_EMAILS):
    """Fetch unread emails and return structured records."""

    references = list_unread_messages(service, limit)
    emails = []

    for reference in references:
        message_id = reference["id"]

        # Fail clearly if a message cannot be retrieved.
        # Do not silently report an incomplete batch as successful.
        message = get_email_details(service, message_id)

        payload = message.get("payload", {})
        headers = payload.get("headers", [])

        sender = get_header(headers, "From")

        emails.append({
            "id": message_id,
            "thread_id": message.get("threadId", ""),
            "sender": parseaddr(sender)[1] or sender,
            "subject": (
                get_header(headers, "Subject") or "(No subject)"
            ),
            "date": get_header(headers, "Date"),
            "body": extract_body(payload),
            "labels": message.get("labelIds", []),
        })

    return emails


# --------------------------------------------------
# Application Entry Point
# --------------------------------------------------

def main():
    try:
        service = get_gmail_service()
        emails = fetch_unread_emails(service)

        print(f"Fetched {len(emails)} unread emails.")

        for item in emails:
            print("-" * 50)
            print(f"ID: {item['id']}")
            print(f"From: {item['sender']}")
            print(f"Subject: {item['subject']}")
            print(f"Date: {item['date']}")
            print(f"Body length: {len(item['body'])} characters")
            print(f"Body preview: {item['body'][:200]}")

    except HttpError as exc:
        logger.error(
            "Gmail API request failed with HTTP status %s.",
            exc.resp.status,
        )
        raise SystemExit(1) from exc

    except (FileNotFoundError, RefreshError, ValueError):
        logger.exception("Configuration or authentication failed.")
        raise SystemExit(1)

    except Exception:
        logger.exception("Email processing failed.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
