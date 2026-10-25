
import json
import os
from functools import lru_cache

import boto3


@lru_cache(maxsize=1)
def get_app_secrets():
    """Load application secrets from AWS when cloud mode is enabled."""

    if os.getenv("AWS_SECRETS_MODE", "").lower() != "true":
        return {}

    secret_name = os.getenv(
        "AWS_SECRET_NAME", "ai-email-assistant/production"
    )
    region = os.getenv("AWS_REGION", "ap-south-1")

    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


def get_secret_value(name):
    """Prefer explicitly configured environment variables, then AWS secrets."""

    value = os.getenv(name)
    if value:
        return value

    return get_app_secrets().get(name)
