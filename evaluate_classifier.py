
import json
import logging
import random
import time
from pathlib import Path

from llm.factory import get_llm_provider
from evaluation_metrics import calculate_metrics

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "evaluation_dataset.json"

logging.basicConfig(level=logging.WARNING)


def main():
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not dataset:
        raise ValueError("Evaluation dataset is empty.")

    provider = get_llm_provider()
    results = []

    print(f"Evaluating {len(dataset)} synthetic examples...\n")

    for index, example in enumerate(dataset):
        if index > 0:
            wait_seconds = 5 + random.uniform(0, 1)
            print(
                f"Waiting {wait_seconds:.1f} seconds "
                "before next API call..."
            )
            time.sleep(wait_seconds)

        expected = example["expected"]

        try:
            prediction = provider.classify_email(
                subject=example["subject"],
                body=example["body"],
            )

            predicted = {
                "category": prediction.category,
                "urgency": prediction.urgency,
                "needs_reply": prediction.needs_reply,
            }

            results.append({
                "id": example["id"],
                "success": True,
                "expected": expected,
                "predicted": predicted,
            })

            print(f"Example: {example['id']}")
            for field in ("category", "urgency", "needs_reply"):
                print(
                    f"  {field}: expected={expected[field]}, "
                    f"predicted={predicted[field]}, "
                    f"match={expected[field] == predicted[field]}"
                )

        except Exception as exc:
            results.append({
                "id": example["id"],
                "success": False,
                "expected": expected,
                "predicted": {},
                "error_type": type(exc).__name__,
            })

            print(
                f"Example: {example['id']} — failed "
                f"({type(exc).__name__})"
            )

        print()

    metrics = calculate_metrics(results)

    print("=== Evaluation Results ===")
    print(f"Examples in dataset: {metrics['examples_total']}")
    print(f"Successfully evaluated: {metrics['examples_evaluated']}")
    print(f"Failed evaluations: {metrics['examples_failed']}")

    for name, key in (
        ("Category accuracy", "category_accuracy"),
        ("Urgency accuracy", "urgency_accuracy"),
        ("Reply-decision accuracy", "reply_accuracy"),
    ):
        value = metrics[key]
        formatted = f"{value:.1%}" if value is not None else "N/A"
        print(f"{name}: {formatted}")


if __name__ == "__main__":
    main()
