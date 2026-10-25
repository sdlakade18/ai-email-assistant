
import unittest

from evaluation.evaluation_metrics import calculate_metrics


class TestEvaluationMetrics(unittest.TestCase):
    def test_accuracy_ignores_failed_requests(self):
        results = [
            {
                "success": True,
                "expected": {
                    "category": "Work",
                    "urgency": "high",
                    "needs_reply": True,
                },
                "predicted": {
                    "category": "Work",
                    "urgency": "high",
                    "needs_reply": True,
                },
            },
            {
                "success": False,
                "expected": {
                    "category": "Finance",
                    "urgency": "low",
                    "needs_reply": False,
                },
                "predicted": {},
            },
        ]

        metrics = calculate_metrics(results)

        self.assertEqual(metrics["examples_total"], 2)
        self.assertEqual(metrics["examples_evaluated"], 1)
        self.assertEqual(metrics["examples_failed"], 1)
        self.assertEqual(metrics["category_accuracy"], 1.0)
        self.assertEqual(metrics["urgency_accuracy"], 1.0)
        self.assertEqual(metrics["reply_accuracy"], 1.0)

    def test_empty_results(self):
        metrics = calculate_metrics([])

        self.assertEqual(metrics["examples_total"], 0)
        self.assertIsNone(metrics["category_accuracy"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
