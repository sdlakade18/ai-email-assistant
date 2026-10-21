
import tempfile
from pathlib import Path

from audit_store import (
    start_processing,
    record_classification,
    record_draft,
    mark_processed,
    get_processing_record,
)


def main():
    # Use a temporary database so the test doesn't touch
    # your actual audit history.
    with tempfile.TemporaryDirectory() as folder:
        test_db = Path(folder) / "test.db"

        # The current implementation uses DB_PATH by default.
        # For this test, use the explicit database path by
        # temporarily overriding the module's DB_PATH.
        import audit_store
        audit_store.DB_PATH = test_db

        message_id = "test-message-001"

        assert start_processing(message_id) is True

        record_classification(
            message_id,
            category="Work",
            urgency="high",
            needs_reply=True,
        )

        record_draft(message_id, "test-draft-001")
        mark_processed(message_id)

        record = get_processing_record(message_id)

        assert record["status"] == "processed"
        assert record["category"] == "Work"
        assert record["urgency"] == "high"
        assert record["needs_reply"] == 1
        assert record["draft_id"] == "test-draft-001"

        # Completed messages must not start again.
        assert start_processing(message_id) is False

        print("Audit database tests passed.")


if __name__ == "__main__":
    main()
