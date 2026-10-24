
from audit_store import (
    start_processing,
    record_classification,
    mark_processed,
    mark_failed,
)

SAMPLES = [
    {
        "id": "demo-001",
        "category": "Work",
        "urgency": "high",
        "needs_reply": True,
        "status": "processed",
    },
    {
        "id": "demo-002",
        "category": "Personal",
        "urgency": "low",
        "needs_reply": True,
        "status": "processed",
    },
    {
        "id": "demo-003",
        "category": "Finance",
        "urgency": "low",
        "needs_reply": False,
        "status": "processed",
    },
    {
        "id": "demo-004",
        "category": "Promotions",
        "urgency": "low",
        "needs_reply": False,
        "status": "failed",
    },
    {
        "id": "demo-005",
        "category": "Work",
        "urgency": "medium",
        "needs_reply": True,
        "status": "processed",
    },
]


def main():
    for sample in SAMPLES:
        message_id = sample["id"]

        if not start_processing(message_id):
            print(f"Skipping existing demo record: {message_id}")
            continue

        record_classification(
            message_id=message_id,
            category=sample["category"],
            urgency=sample["urgency"],
            needs_reply=sample["needs_reply"],
        )

        if sample["status"] == "failed":
            mark_failed(message_id, RuntimeError("Synthetic demo failure"))
        else:
            mark_processed(message_id)

    print(f"Demo records saved to: {__import__('audit_store').DB_PATH}")
    print("These are synthetic records; no Gmail or Gemini calls were made.")


if __name__ == "__main__":
    main()
