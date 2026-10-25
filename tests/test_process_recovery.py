
import tempfile
import unittest
from pathlib import Path

import audit_store


class TestProcessingRecovery(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = audit_store.DB_PATH
        audit_store.DB_PATH = Path(self.temp_dir.name) / "test.db"

    def tearDown(self):
        audit_store.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_failed_message_can_be_retried(self):
        message_id = "test-message-002"

        self.assertTrue(audit_store.start_processing(message_id))
        audit_store.mark_failed(message_id, ValueError("Simulated failure"))

        record = audit_store.get_processing_record(message_id)
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error_type"], "ValueError")

        # A failed message should be eligible for another attempt.
        self.assertTrue(audit_store.start_processing(message_id))

        record = audit_store.get_processing_record(message_id)
        self.assertEqual(record["status"], "in_progress")
        self.assertIsNone(record["error_type"])

    def test_processed_message_is_not_reprocessed(self):
        message_id = "test-message-003"

        self.assertTrue(audit_store.start_processing(message_id))
        audit_store.mark_processed(message_id)

        self.assertFalse(audit_store.start_processing(message_id))


if __name__ == "__main__":
    unittest.main(verbosity=2)
