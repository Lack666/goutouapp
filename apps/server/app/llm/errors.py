"""Stable, content-free errors at the LLM boundary."""

from typing import ClassVar


class LLMError(Exception):
    code: ClassVar[str] = "llm_error"
    public_message: ClassVar[str] = "LLM operation failed"

    def __init__(self) -> None:
        super().__init__(self.public_message)


class LLMConfigurationError(LLMError):
    code = "llm_configuration_error"
    public_message = "LLM provider configuration is invalid"


class LLMProviderError(LLMError):
    code = "llm_provider_error"
    public_message = "LLM provider rejected the request"


class LLMAuthenticationError(LLMProviderError):
    code = "llm_authentication_error"
    public_message = "LLM provider authentication failed"


class LLMTimeoutError(LLMError):
    code = "llm_timeout"
    public_message = "LLM provider timed out"


class LLMRateLimitError(LLMProviderError):
    code = "llm_rate_limit"
    public_message = "LLM provider rate limit reached"


class LLMUnavailableError(LLMError):
    code = "llm_unavailable"
    public_message = "LLM provider is unavailable"


class LLMInvalidResponseError(LLMError):
    code = "llm_invalid_response"
    public_message = "LLM provider returned an invalid response"


class LLMStructuredOutputError(LLMError):
    code = "llm_invalid_structured_output"
    public_message = "LLM provider returned invalid structured output"
