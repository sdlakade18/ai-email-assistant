
import os

from dotenv import load_dotenv

from llm.base import LLMProvider
from llm.gemini_provider import GeminiProvider


load_dotenv()


def get_llm_provider() -> LLMProvider:
    provider_name = os.getenv(
        "LLM_PROVIDER", "gemini"
    ).strip().lower()

    if provider_name == "gemini":
        return GeminiProvider()

    if provider_name in {"bedrock", "ollama"}:
        raise NotImplementedError(
            f"{provider_name} provider will be implemented "
            "as a later project milestone."
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER: {provider_name}"
    )
