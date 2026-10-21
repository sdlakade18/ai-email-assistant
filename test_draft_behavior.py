
import unittest
from unittest.mock import MagicMock, patch

from gmail_actions import create_reply_draft


class TestDraftBehavior(unittest.TestCase):
    def setUp(self):
        self.service = MagicMock()
        self.email = {
            "id": "test-message-001",
            "thread_id": "test-thread-001",
            "subject": "Test subject",
            "sender": "sender@example.com",
        }

    @patch("gmail_actions.find_existing_draft_for_thread")
    def test_existing_draft_is_reused(self, find_existing):
        existing_draft = {"id": "existing-draft-001"}
        find_existing.return_value = existing_draft

        draft, was_created = create_reply_draft(
            self.service,
            self.email,
            "Test reply",
        )

        self.assertEqual(draft, existing_draft)
        self.assertFalse(was_created)
        self.service.users().drafts().create.assert_not_called()

    @patch("gmail_actions.find_existing_draft_for_thread")
    def test_new_draft_is_created(self, find_existing):
        find_existing.return_value = None

        # Mock the original email's Message-ID header.
        self.service.users().messages().get().execute.return_value = {
            "payload": {
                "headers": [
                    {"name": "Message-ID", "value": "<original@example.com>"}
                ]
            }
        }

        expected_draft = {"id": "new-draft-001"}
        self.service.users().drafts().create().execute.return_value = (
            expected_draft
        )

        draft, was_created = create_reply_draft(
            self.service,
            self.email,
            "Test reply",
        )

        self.assertEqual(draft, expected_draft)
        self.assertTrue(was_created)
        create_call = self.service.users().drafts().create.call_args_list

        self.assertEqual(len(create_call), 2)
        self.assertEqual(
            create_call[1].kwargs["userId"],
            "me",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
