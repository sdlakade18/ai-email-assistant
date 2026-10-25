
import json
import os
import unittest
from unittest.mock import patch, MagicMock

from aws_secrets import get_app_secrets, get_secret_value


class TestAWSSecrets(unittest.TestCase):

    def tearDown(self):
        get_app_secrets.cache_clear()

    @patch("aws_secrets.boto3.client")
    def test_loads_secret_from_aws(self, mock_boto):
        get_app_secrets.cache_clear()

        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps({
                "GEMINI_API_KEY": "fake-test-key"
            })
        }
        mock_boto.return_value = mock_client

        with patch.dict(os.environ, {
            "AWS_SECRETS_MODE": "true",
            "AWS_REGION": "ap-south-1"
        }, clear=False):
            with patch.dict(os.environ, {}, clear=True):
                os.environ["AWS_SECRETS_MODE"] = "true"
                os.environ["AWS_REGION"] = "ap-south-1"
                os.environ["AWS_SECRET_NAME"] = "test-secret"
                self.assertEqual(
                    get_secret_value("GEMINI_API_KEY"),
                    "fake-test-key"
                )


if __name__ == "__main__":
    unittest.main()
