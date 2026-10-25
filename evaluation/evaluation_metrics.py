
def calculate_metrics(results):
    """
    Calculate classification accuracy using successful predictions only.

    Each result should contain:
      expected: dict with category, urgency, needs_reply
      predicted: dict with category, urgency, needs_reply
      success: bool
    """
    successful = [item for item in results if item.get("success")]

    metrics = {
        "examples_total": len(results),
        "examples_evaluated": len(successful),
        "examples_failed": len(results) - len(successful),
    }

    if not successful:
        metrics["category_accuracy"] = None
        metrics["urgency_accuracy"] = None
        metrics["reply_accuracy"] = None
        return metrics

    total = len(successful)

    metrics["category_accuracy"] = sum(
        item["expected"]["category"] == item["predicted"]["category"]
        for item in successful
    ) / total

    metrics["urgency_accuracy"] = sum(
        item["expected"]["urgency"] == item["predicted"]["urgency"]
        for item in successful
    ) / total

    metrics["reply_accuracy"] = sum(
        item["expected"]["needs_reply"] == item["predicted"]["needs_reply"]
        for item in successful
    ) / total

    return metrics
