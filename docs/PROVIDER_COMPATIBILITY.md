# DeepSeek compatibility (2026-10-26)

Reuse OpenAICompatibleProvider and the existing protocol. No vendor SDK or runtime
rewrite. Current official model ID is `deepseek-flash` (documented serving version
DeepSeek-V4.1-Flash-1017). Configure it privately; no deprecated alias is baked into
the app default. Default app provider remains Mock and no startup performs I/O.

Official references checked2026-10-26:
[models/pricing](https://api-docs.deepseek.com/quick_start/pricing/),
[CNY pricing](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/),
[JSON output](https://api-docs.deepseek.com/guides/json_mode/),
[thinking](https://api-docs.deepseek.com/guides/thinking_mode/).

JSON object mode promises JSON, not project Schema validity. The adapter includes
the caller's JSON Schema in system instructions and still validates strictly with
Pydantic. Semantic/source/action validators remain mandatory. Existing model-level
source and action rules are now explicitly explained in their separate prompts;
baseline failures remain evidence. No retries or relaxed parsing are introduced.

Server settings: LLM_PROVIDER=openai_compatible, LLM_API_KEY, LLM_BASE_URL,
LLM_MODEL, LLM_TIMEOUT_SECONDS, LLM_MAX_OUTPUT_TOKENS, LLM_TEMPERATURE and
LLM_THINKING=enabled/disabled. Generic compatible services may reject thinking;
leave it unset there. DeepSeek eval explicitly disables thinking. Vendor hidden
reasoning fields are always discarded. Thinking mode ignores temperature per
official docs; the supplied temperature must not be represented as effective then.

Live scripts additionally require EVAL_LIVE_OPT_IN=true. Backend-only fallback
reads exactly one key from ignored root api.txt; ordinary app code never reads that
file. No key in CLI arguments, client, EXPO_PUBLIC, logs or checked-in evidence.
Smoke tests use Chinese and Emoji and formally validate SafetyResult. Full Agent
E2E uses signed development JWT, real FastAPI/service/graph/adapter/PostgreSQL and
REST/SSE. See immutable JSON evidence and PHASE_11_ACCEPTANCE for actual results.

Streaming requests usage frames and requires content, finish_reason=stop and DONE.
Empty, unfinished, truncated, malformed and schema-invalid output fail safely.
Timeout/429/5xx/connection failures map to existing content-free errors. No automatic
retry, hidden paid calls, new operation keys, fake completion or raw exceptions.

Pricing snapshot: CNY per million tokens for Flash, peak cache hit0.04, miss2,
output8; off-peak half. Estimates deliberately use the peak upper bound and do
not claim invoice reconciliation. Cache classes must sum to input usage; missing
usage/cache classes yield unknown cost (null), never0. No actual currency conversion.
Price version `deepseek-flash-2026-10-26-peak-cny` requires review before later live use.
Unknown model pricing refuses budget admission; model overrides are equally checked.

Each live process reserves at most30 requests,500000 tokens and5 CNY by default;
private EVAL_MAX_REQUESTS/EVAL_MAX_TOKENS/EVAL_MAX_COST_CNY configure limits.
Before sending, reserve UTF-8 input bytes plus4096 framing tokens and capped output
tokens at peak miss/output rates. Reservations are never refunded on failure or
unknown outcomes. Exhaustion stops further cases. They are conservative upper
bounds, not vendor usage. A new explicit script process is a separate budget;
the report also sums all recorded development attempts and lists unknown attempts.
