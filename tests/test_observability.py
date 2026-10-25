
import logging

from llm.observability import trace_classification

logging.basicConfig(level=logging.INFO)


class DummyClassifier:
    @trace_classification
    def classify_email(self, subject: str, body: str):
        # Simulated classification; no external API calls.
        return {"category": "Work", "urgency": "low"}


if __name__ == "__main__":
    classifier = DummyClassifier()
    result = classifier.classify_email(
        subject="Synthetic test subject",
        body="Synthetic test body. No real email data.",
    )

    assert result["category"] == "Work"
    assert result["urgency"] == "low"

    print("Observability wrapper test passed.")
