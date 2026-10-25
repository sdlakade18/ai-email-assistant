
from slack_notifier import send_slack_message


if __name__ == "__main__":
    send_slack_message(
        "Test notification from the AI Email Assistant. "
        "Slack integration is working."
    )
    print("Slack test completed.")
