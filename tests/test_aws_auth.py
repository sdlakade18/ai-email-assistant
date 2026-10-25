
import json
import os
import unittest
from unittest.mock import patch, MagicMock

from google.oauth2.credentials import Credentials

import email_processor


class TestAWSAuthentication(unittest.TestCase):

    @patch("email_processor.boto3.client")
    def test_loads_credentials_from_secrets_manager(self, mock_boto_client):
        secret = {
            "GMAIL_CREDENTIALS_JSON": json.dumps({
                "installed": {
                    "client_id": "test-client-id",
                    "client_secret": "test-client-secret",
                    "auth_uri": "https://example.com/auth",
                    "token_uri": "https://example.com/token"
                }
            }),
            "GMAIL_TOKEN_JSON": json.dumps({
                "token": "test-access-token",
                "refresh_token": "test-refresh-token",
                "token_uri": "https://example.com/token",
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "scopes": email_processor.SCOPES
            }),
            "GEMINI_API_KEY": "test-gemini-key",
            "SLACK_WEBHOOK_URL": "https://example.com/webhook",
            "LANGSMITH_API_KEY": "test-langsmith-key"
        }

        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret)
        }
        mock_boto_client.return_value = mock_client

        with patch.dict(os.environ, {
            "AWS_SECRETS_MODE": "true",
            "AWS_SECRET_NAME": "ai-email-assistant/production",
            "AWS_REGION": "ap-south-1"
        }):
            with patch.object(
                email_processor.Credentials,
                "from_authorized_user_info",
                return_value=MagicMock(
                    valid=True,
                    has_scopes=MagicMock(return_value=True)
                )
            ) as mock_credentials:
                creds = email_processor.authenticate()

        mock_boto_client.assert_called_once_with(
            "secretsmanager",
            region_name="ap-south-1"
        )
        mock_client.get_secret_value.assert_called_once_with(
            SecretId="ai-email-assistant/production"
        )
        mock_credentials.assert_called_once()
        self.assertIsNotNone(creds)


if __name__ == "__main__":
    unittest.main()
