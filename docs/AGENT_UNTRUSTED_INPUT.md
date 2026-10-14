# Agent untrusted-input audit and provider handoff — Phase 9G

User Message, persisted Agent Message, imported Markdown, RelationshipMessage,
speaker label, Memory summary and any future provider/RAG output are data.
Only server-owned prompts create LLM system messages. Signed JWT verification
issues AuthenticatedActor; prompt content cannot issue one. Owner checks and
server confirmation remain deterministic services outside LangGraph.

Current production path: normalize → consent-gated Memory load → SafetyResult
classification → conditional routing. Safety precedes ordinary analysis and all
Memory mutations. Memory recall happens before classification; high risk does
not invoke analysis or mutation nodes. Safety receives current/bounded recent
Agent messages, never historical Memory or imported RelationshipMessage.
Normal paths classify/extract FIU, deterministically select one to three frozen
references, analyze, plan, validate output and resolve Memory intent.

context_payload serializes history and the current request as JSON under one user
message. An embedded role/speaker value such as system remains a JSON field; it
cannot become an LLM system message. Historical Memory enters analysis only as
separately labeled historical data with source/time, never a current F fact.
Reference excerpts are server-selected general knowledge, not observed user facts.
Node read/write contracts restrict state mutation; no arbitrary tool dispatcher,
network uploader, owner-switch action or delete execution tool exists in the graph.

Natural language can request legitimate consent/pause/resume/revoke controls under
the existing explicit-user contract. It cannot execute public Undo or deletion:
AgentService enables guarded Undo, and deletion stays pending_confirmation.
The server challenge must still bind exact owner/action/target/snapshot/expiry;
an alleged confirmation in chat has no authority. External imported text and
Memory content never become current-user intent in the resolver. The standalone
Python undo contract is intentionally separate from guarded public Undo.

Formal imported-chat analysis **is not implemented**. Upload/bind/finalize writes
separate RelationshipMessages; AgentService builds history from its own Messages.
The 9G tests import malicious sender labels/body text through real signed services,
then run an ordinary Agent request and prove absence from every captured LLM
payload. No artificial import-to-analysis workflow is claimed.

Safety testing uses reviewed synthetic high-risk fixtures and a deterministic
MockLLM returning explicit SafetyResult. It witnesses actual node execution through
LangGraph and signed REST/POST SSE, validates safety-only progress, and checks
durable Run/Message identity and unchanged Memory. Low-risk controls execute the
ordinary graph. These tests prove graph routing and authorization isolation,
**not classifier comprehension, live-model prompt-injection resistance or future
provider safety**. A malicious/incorrect provider can misclassify otherwise valid
structured output; schema validation and prompt placement cannot prove accuracy.
This limitation is explicit R-08 and requires Phase 11 behavioral eval before
real-user model admission. No external model call occurs in 9G.

Future provider/RAG/import integration must retain authenticated structured scope,
explicit import-analysis consent, source provenance and byte/token bounds. Retrieved
documents/tool results remain in data messages with source labels; no retrieved
text can override system instructions, create tool authority, access another owner,
grant consent or confirm deletion. Any future action tool requires a deterministic
allowlist and independent owner/challenge authorization after model proposals.
Evaluate disguised instructions, multilingual dangerous requests, false positives,
truncated sources and Memory poisoning with a real configured provider in a
separately authorized task. Keep FEATURE_RAG=false fully functional. Provider-copy
retention/deletion and failure/redaction contracts must be documented before use.
