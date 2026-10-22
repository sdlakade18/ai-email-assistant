
from llm.gemini_provider import GeminiProvider


def main():
    provider = GeminiProvider()

    result = provider.classify_email(
        subject="Synthetic project status update",
        body=(
            "The project milestone is complete. "
            "Please review the attached schedule by Friday."
        ),
    )

    print("Gemini classification succeeded.")
    print(f"Category: {result.category}")
    print(f"Urgency: {result.urgency}")
    print(f"Needs reply: {result.needs_reply}")
    print(f"Summary: {result.short_summary}")


if __name__ == "__main__":
    main()
