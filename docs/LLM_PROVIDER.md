# Phase 2C LLM Provider architecture

The internal `app.llm.LLMProvider` protocol exposes three text-only operations:
`chat`, `stream`, and `structured_output`. Future application code should call
this protocol or `create_llm_provider(settings)`, never a vendor SDK directly.
It returns only `LLMMessage`, `ChatResult`, `Usage`, `StreamChunk`, or a validated
caller-supplied Pydantic model. No Agent schema or prompt is defined here.

## Selection and configuration

- `LLM_PROVIDER=mock` needs no API key, URL, network, or database. Queue a
  response for each operation before calling it; an unconfigured queue raises
  `LLMConfigurationError`. Its chat, stream, structured and error queues let
  tests specify independent outcomes.
- `LLM_PROVIDER=openai_compatible` requires `LLM_API_KEY`, `LLM_BASE_URL` and
  `LLM_MODEL`. `LLM_TIMEOUT_SECONDS` defaults to 30; there are no retries.
  The factory validates configuration when requested. FastAPI import/startup
  never constructs a real provider or contacts a model API.
- `LLM_BASE_URL` is the prefix **before** `/chat/completions`. Official examples
  include [OpenAI](https://platform.openai.com/docs/api-reference/chat/create)
  (`https://api.openai.com/v1`),
  [DeepSeek](https://api-docs.deepseek.com/guides/harness)
  (`https://api.deepseek.com`), and
  [Qwen Model Studio](https://help.aliyun.com/en/model-studio/first-api-call-to-qwen)
  (a region-specific `.../compatible-mode/v1` URL). This phase verifies the
  shared wire format with a fake transport; it makes no live vendor call or
  claim that every model supports every option.

`LLM_API_KEY` and `LLM_BASE_URL` are masked `SecretStr` settings. The provider's
repr is redacted, errors use fixed messages, and neither the provider nor the
app logs request bodies, response bodies, Authorization headers, or raw
transport exceptions. Configured remote URLs must use HTTPS; local HTTP is
allowed only for localhost. URLs containing credentials, query strings, or
fragments are rejected. The ignored `.env` file is for local configuration.
The default HTTPX client is closed after each operation; an injected client is
owned and closed by its caller. FastAPI startup creates neither kind of client.

## Response handling

- `chat` sends typed role/content messages and optional model/temperature to
  Chat Completions. The provider validates and maps the first choice, model,
  finish reason, and optional token usage into `ChatResult`. Unknown fields,
  including `reasoning_content`, are discarded. It never exposes hidden
  chain-of-thought.
- `structured_output` sends `response_format={"type":"json_object"}` and
  validates the returned content with `schema.model_validate_json(...,
  strict=True)`. Invalid JSON, missing required fields and wrong types produce
  `LLMStructuredOutputError`; no values are guessed or filled. JSON object mode
  is a formatting request, not a schema guarantee. Official
  [DeepSeek](https://api-docs.deepseek.com/guides/json_mode/) and
  [Qwen](https://help.aliyun.com/en/model-studio/qwen-structured-output)
  guidance requires the caller's messages to ask for JSON. A later Agent phase
  will own any prompt wording.
- `stream` parses server-sent `data:` frames, maps incremental content, finish
  reason and optional usage into `StreamChunk`, and closes the response context.
  A missing `[DONE]` or malformed frame is an invalid response. It does not
  implement WebSocket or a transport endpoint.

Errors are `LLMConfigurationError`, `LLMAuthenticationError`,
`LLMProviderError`, `LLMTimeoutError`, `LLMRateLimitError`,
`LLMUnavailableError`, `LLMInvalidResponseError`, and
`LLMStructuredOutputError`. HTTP 401/403, 429, 5xx and transport failures map
to stable types. The raw HTTPX exception and upstream error body stay inside
the provider boundary. See [ADR 0007](adr/0007-llm-provider-boundary.md).

## Offline verification

The tests use `httpx.MockTransport` and deterministic mock queues; they need
neither internet nor an LLM key. Run `uv run --locked pytest -q
apps/server/tests/test_llm_mock.py apps/server/tests/test_llm_openai_compatible.py`
or `.\make.cmd verify` from the repository root. The latter also runs the
inherited PostgreSQL, Golden, upstream, Ruff and secret gates.
