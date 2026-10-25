
import logging
import os
from aws_secrets import get_secret_value
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def send_slack_message(text: str) -> None:
    """Send a message to Slack using an incoming webhook."""

    webhook_url = get_secret_value("SLACK_WEBHOOK_URL")

    if not webhook_url:
        raise RuntimeError(
            "SLACK_WEBHOOK_URL is not configured."
        )

    response = requests.post(
        webhook_url,
        json={"text": text},
        timeout=10,
    )

    if not response.ok:
        # Do not log the webhook URL or full request details.
        raise RuntimeError(
            f"Slack notification failed with HTTP {response.status_code}."
        )

    logger.info("Slack notification sent successfully.")

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def send_slack_message(text: str) -> None:
    """Send a message to Slack using an incoming webhook."""

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url:
        raise RuntimeError(
            "SLACK_WEBHOOK_URL is not configured."
        )

    response = requests.post(
        webhook_url,
        json={"text": text},
        timeout=10,
    )

    if not response.ok:
        # Do not log the webhook URL or full request details.
        raise RuntimeError(
            f"Slack notification failed with HTTP {response.status_code}."
        )

    logger.info("Slack notification sent successfully.")
