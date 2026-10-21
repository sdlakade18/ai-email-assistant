
import logging

from email_processor import (
    get_gmail_service,
    fetch_unread_emails,
)
from gmail_actions import (
    get_or_create_label,
    apply_label,
    create_reply_draft,
)
from llm.factory import get_llm_provider


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


CATEGORY_LABELS = {
    "Work": "AI/Work",
    "Personal": "AI/Personal",
    "Finance": "AI/Finance",
    "Promotions": "AI/Promotions",
    "Social": "AI/Social",
    "Updates": "AI/Updates",
    "Spam": "AI/Spam",
    "Other": "AI/Other",
}


def main():
    service = get_gmail_service()
    provider = get_llm_provider()

    # Keep this at 1 while testing to conserve Gemini quota.
    emails = fetch_unread_emails(service, limit=1)

    if not emails:
        print("No unprocessed unread emails found.")
        return

    # Create or retrieve category labels.
    label_ids = {
        label_name: get_or_create_label(service, label_name)
        for label_name in set(CATEGORY_LABELS.values())
    }

    processed_label_id = get_or_create_label(
        service,
        "AI/Processed",
    )

    urgency_label_id = get_or_create_label(
        service,
        "AI/High-Urgency",
    )

    for email in emails:
        message_id = email["id"]

        try:
            # 1. Classify the email.
            result = provider.classify_email(
                subject=email["subject"],
                body=email["body"],
            )

            # 2. Apply its category label.
            category_label_name = CATEGORY_LABELS[result.category]
            apply_label(
                service,
                message_id,
                label_ids[category_label_name],
            )

            # 3. Apply a high-urgency label when appropriate.
            if result.urgency == "high":
                apply_label(
                    service,
                    message_id,
                    urgency_label_id,
                )

            # 4. Create a draft if a reply is needed.
            # This creates a draft only; it never sends an email.
            if result.needs_reply:
                draft_text = (
                    "Hi,\n\n"
                    "Thank you for your email. I have received it "
                    "and will review it shortly.\n\n"
                    "Regards"
                )

                create_reply_draft(
                    service=service,
                    email_record=email,
                    reply_text=draft_text,
                )

            # 5. Mark processed only after previous operations succeed.
            apply_label(
                service,
                message_id,
                processed_label_id,
            )

            print(
                f"Processed: {email['subject']} | "
                f"Category: {result.category} | "
                f"Urgency: {result.urgency} | "
                f"Needs reply: {result.needs_reply}"
            )

        except Exception:
            # Never log the email body, tokens, or API key.
            logger.exception(
                "Failed to process message ID %s.",
                message_id,
            )


if __name__ == "__main__":
    main()
