"""Single configuration switch for all future LLM consumers."""

import httpx

from app.core.config import Settings
from app.llm.errors import LLMConfigurationError
from app.llm.mock import MockLLMProvider
from app.llm.openai_compatible import OpenAICompatibleProvider
from app.llm.provider import LLMProvider


def create_llm_provider(
    settings: Settings, *, client: httpx.AsyncClient | None = None
) -> LLMProvider:
    if settings.llm_provider == "mock":
        return MockLLMProvider(model=settings.llm_model or "mock")
    if settings.llm_provider == "openai_compatible":
        if settings.llm_api_key is None or settings.llm_base_url is None:
            raise LLMConfigurationError() from None
        return OpenAICompatibleProvider(
            base_url=settings.llm_base_url.get_secret_value(),
            api_key=settings.llm_api_key,
            model=settings.llm_model or "",
            timeout_seconds=settings.llm_timeout_seconds,
            max_output_tokens=settings.llm_max_output_tokens,
            temperature=settings.llm_temperature,
            thinking=settings.llm_thinking,
            client=client,
        )
    raise LLMConfigurationError() from None
