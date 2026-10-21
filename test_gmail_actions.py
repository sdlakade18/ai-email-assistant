
from email_processor import (
    get_gmail_service,
    fetch_unread_emails,
)
from gmail_actions import create_reply_draft


def main():
    service = get_gmail_service()
    emails = fetch_unread_emails(service, limit=10)

    if not emails:
        print("No unread emails found. Nothing changed.")
        return

    email = emails[0]

    reply_text = (
        "Hi,\n\n"
        "Thank you for your email. I have received it "
        "and will review it shortly.\n\n"
        "Regards"
    )

    draft, was_created = create_reply_draft(
        service=service,
        email_record=email,
        reply_text=reply_text,
    )

    if was_created:
        print("New reply draft created successfully.")
    else:
        print("An existing draft was reused; no duplicate was created.")

    print(f"Draft ID: {draft['id']}")


if __name__ == "__main__":
    main()
