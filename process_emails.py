
import logging,os
from collections import Counter
from audit_store import (
    start_processing,
    record_classification,
    record_draft,
    mark_processed,
    mark_failed,
)
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
from slack_notifier import send_slack_message


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

    # Keep at 1 while testing to conserve Gemini quota.
    emails = fetch_unread_emails(service, limit=1)

    if not emails:
        print("No unprocessed unread emails found.")
        return

    label_ids = {
        label_name: get_or_create_label(service, label_name)
        for label_name in set(CATEGORY_LABELS.values())
    }

    processed_label_id = get_or_create_label(
        service, "AI/Processed"
    )
    urgency_label_id = get_or_create_label(
        service, "AI/High-Urgency"
    )

    category_counts = Counter()
    processed_count = 0
    failed_count = 0
    urgent_count = 0
    drafts_created = 0


    for email in emails:
        message_id = email["id"]

        try:
            # Skip emails already completed in the audit database.
            if not start_processing(message_id):
                logger.info(
                    "Skipping already processed message ID %s.",
                    message_id,
                )
                continue

            result = provider.classify_email(
                subject=email["subject"],
                body=email["body"],
            )

            record_classification(
                message_id=message_id,
                category=result.category,
                urgency=result.urgency,
                needs_reply=result.needs_reply,
            )

            # Apply category label.
            category_label_name = CATEGORY_LABELS[result.category]
            apply_label(
                service,
                message_id,
                label_ids[category_label_name],
            )

            # Apply urgency label when appropriate.
            if result.urgency == "high":
                apply_label(
                    service,
                    message_id,
                    urgency_label_id,
                )

            # Create a draft only when the classifier says one is needed.

            if result.needs_reply:
                draft_text = (
                    "Hi,\n\n"
                    "Thank you for your email. I have received it "
                    "and will review it shortly.\n\n"
                    "Regards"
                )

                draft, was_created = create_reply_draft(
                    service=service,
                    email_record=email,
                    reply_text=draft_text,
                )

                record_draft(
                    message_id=message_id,
                    draft_id=draft["id"],
                )

                if was_created:
                    drafts_created += 1


            # Mark as processed only after the required actions succeed.
            apply_label(
                service,
                message_id,
                processed_label_id,
            )
            mark_processed(message_id)
            if result.urgency == "high":
                urgent_count += 1

            category_counts[result.category] += 1
            processed_count += 1

            logger.info(
                "Successfully processed message ID %s.",
                message_id,
            )

        except Exception as exc:
            failed_count += 1

            try:
                mark_failed(message_id, exc)
            except Exception:
                logger.exception(
                    "Could not save failure status for message ID %s.",
                    message_id,
                )

            # Do not log the email body or credentials.
            logger.exception(
                "Failed to process message ID %s.",
                message_id,
            )

    # Build one summary without exposing subjects, addresses, or bodies.
    summary_lines = [
    "AI Email Assistant - Processing Summary",
    f"Emails fetched: {len(emails)}",
    f"Successfully processed: {processed_count}",
    f"Failed: {failed_count}",
    f"High urgency: {urgent_count}",
    f"Reply drafts requested: {drafts_created}",
    "",
    "Categories:",
]

    if category_counts:
        for category, count in sorted(category_counts.items()):
            summary_lines.append(f"- {category}: {count}")
    else:
        summary_lines.append("No emails were successfully processed.")

    summary = "\n".join(summary_lines)

    try:
        send_slack_message(summary)
    except Exception:
        logger.exception(
            "Slack notification failed; email processing results "
            "may still have succeeded."
        )

    print("\n" + summary.replace("*", ""))



if __name__ == "__main__":
    if os.getenv("DRY_RUN", "true").lower() != "false":
        print(
            "Safety mode enabled: email processing is disabled. "
            "Set DRY_RUN=false only when ready to process real emails."
        )
    else:
        main()
