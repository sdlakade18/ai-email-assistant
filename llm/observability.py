
import os
import time
import logging
from functools import wraps

from dotenv import load_dotenv
from langsmith import Client, traceable

load_dotenv()

logger = logging.getLogger(__name__)


def trace_classification(func):
    """Trace classification metadata without recording email content."""

    @wraps(func)
    def wrapper(self, subject: str, body: str, *args, **kwargs):
        started_at = time.perf_counter()
        succeeded = False

        try:
            # Trace only safe metadata, not the subject or body.
            @traceable(
                name="email_classification",
                run_type="chain",
                process_inputs=lambda inputs: {
                    "subject_present": bool(subject.strip()),
                    "body_present": bool(body.strip()),
                },
                process_outputs=lambda output: {
                    "classification_completed": True,
                },
            )
            def run_classification():
                return func(self, subject, body, *args, **kwargs)

            result = run_classification()
            succeeded = True
            return result

        finally:
            elapsed_ms = round(
                (time.perf_counter() - started_at) * 1000, 2
            )
            logger.info(
                "Classification metrics: success=%s latency_ms=%s",
                succeeded,
                elapsed_ms,
            )

    return wrapper
