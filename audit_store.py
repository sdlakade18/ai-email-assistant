
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "email_assistant.db"


def utc_now():
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection(db_path=None):
    """Open the database and ensure the audit table exists."""

    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS email_processing (
                message_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                category TEXT,
                urgency TEXT,
                needs_reply INTEGER,
                draft_id TEXT,
                error_type TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()

        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def start_processing(message_id):
    """Start processing unless this email is already completed."""

    now = utc_now()

    with get_connection() as connection:
        existing = connection.execute(
            """
            SELECT status
            FROM email_processing
            WHERE message_id = ?
            """,
            (message_id,),
        ).fetchone()

        if existing and existing["status"] == "processed":
            return False

        connection.execute(
            """
            INSERT INTO email_processing (
                message_id, status, created_at, updated_at
            )
            VALUES (?, 'in_progress', ?, ?)
            ON CONFLICT(message_id) DO UPDATE SET
                status = 'in_progress',
                error_type = NULL,
                updated_at = excluded.updated_at
            """,
            (message_id, now, now),
        )

    return True


def record_classification(
    message_id,
    category,
    urgency,
    needs_reply,
):
    """Save the classification without storing email content."""

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE email_processing
            SET status = 'classified',
                category = ?,
                urgency = ?,
                needs_reply = ?,
                updated_at = ?
            WHERE message_id = ?
            """,
            (
                category,
                urgency,
                int(needs_reply),
                utc_now(),
                message_id,
            ),
        )


def record_draft(message_id, draft_id):
    """Record the Gmail draft ID after successful draft creation."""

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE email_processing
            SET draft_id = ?,
                updated_at = ?
            WHERE message_id = ?
            """,
            (draft_id, utc_now(), message_id),
        )


def mark_processed(message_id):
    """Mark an email as successfully processed."""

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE email_processing
            SET status = 'processed',
                error_type = NULL,
                updated_at = ?
            WHERE message_id = ?
            """,
            (utc_now(), message_id),
        )


def mark_failed(message_id, error):
    """Record the error type without storing the full error message."""

    error_type = type(error).__name__

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO email_processing (
                message_id, status, error_type,
                created_at, updated_at
            )
            VALUES (?, 'failed', ?, ?, ?)
            ON CONFLICT(message_id) DO UPDATE SET
                status = 'failed',
                error_type = excluded.error_type,
                updated_at = excluded.updated_at
            """,
            (
                message_id,
                error_type,
                utc_now(),
                utc_now(),
            ),
        )


def get_processing_record(message_id):
    """Retrieve the audit record for one message."""

    with get_connection() as connection:
        record = connection.execute(
            """
            SELECT *
            FROM email_processing
            WHERE message_id = ?
            """,
            (message_id,),
        ).fetchone()

        return dict(record) if record else None
