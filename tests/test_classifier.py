
from llm.factory import get_llm_provider


def main():
    provider = get_llm_provider()

    result = provider.classify_email(
        subject="Project status update required",
        body=(
            "Hi, please send me the project status report "
            "by 3 PM tomorrow so I can prepare for the review."
        ),
    )

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
