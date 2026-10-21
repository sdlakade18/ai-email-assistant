
import base64
import logging
from email.message import EmailMessage

from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

PROCESSED_LABEL = "AI/Processed"


def get_or_create_label(service, label_name):
    """Return a Gmail label ID, creating the label if necessary."""

    response = (
        service.users()
        .labels()
        .list(userId="me")
        .execute()
    )

    for label in response.get("labels", []):
        if label.get("name") == label_name:
            return label["id"]

    created = (
        service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )

    logger.info("Created Gmail label: %s", label_name)
    return created["id"]


def apply_label(service, message_id, label_id):
    """Apply a Gmail label to a message."""

    return (
        service.users()
        .messages()
        .modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id]},
        )
        .execute()
    )


def find_existing_draft_for_thread(service, thread_id):
    """Find an existing draft in the same email thread."""

    page_token = None

    while True:
        response = (
            service.users()
            .drafts()
            .list(
                userId="me",
                maxResults=100,
                pageToken=page_token,
            )
            .execute()
        )

        for draft in response.get("drafts", []):
            draft_message = draft.get("message", {})

            if draft_message.get("threadId") == thread_id:
                return draft

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return None

def create_reply_draft(service, email_record, reply_text):
    """Create a reply draft in the original email thread."""

    original_message_id = email_record["id"]
    thread_id = email_record["thread_id"]
    existing_draft = find_existing_draft_for_thread(
    service,
    thread_id,
)

    if existing_draft:
        logger.info(
        "Draft already exists for thread; skipping creation."
    )
        return existing_draft
    subject = email_record.get("subject", "")

    # Retrieve the original Message-ID and References headers.
    original = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=original_message_id,
            format="metadata",
            metadataHeaders=["Message-ID", "References", "In-Reply-To"],
        )
        .execute()
    )

    headers = original.get("payload", {}).get("headers", [])

    def header_value(name):
        for header in headers:
            if header.get("name", "").lower() == name.lower():
                return header.get("value", "")
        return ""

    original_rfc_id = header_value("Message-ID")
    references = header_value("References")

    if not original_rfc_id:
        raise ValueError(
            "Original email has no Message-ID; cannot safely "
            "prepare a threaded reply."
        )

    message = EmailMessage()
    message["To"] = email_record["sender"]

    if subject.lower().startswith("re:"):
        message["Subject"] = subject
    else:
        message["Subject"] = f"Re: {subject}" if subject else "Re:"

    message["In-Reply-To"] = original_rfc_id
    message["References"] = (
        f"{references} {original_rfc_id}".strip()
        if references
        else original_rfc_id
    )

    message.set_content(reply_text)

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("utf-8")

    draft = (
        service.users()
        .drafts()
        .create(
            userId="me",
            body={
                "message": {
                    "threadId": thread_id,
                    "raw": encoded_message,
                }
            },
        )
        .execute()
    )

    logger.info("Created a reply draft for message ID %s", original_message_id)
    return draft
