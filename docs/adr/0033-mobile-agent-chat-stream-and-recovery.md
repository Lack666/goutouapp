# ADR0033 — Mobile Agent Chat stream and outcome recovery

Status: Accepted for Phase8C engineering implementation; native proof remains separate.

The existing POST SSE is a V1 progress protocol with committed answer and a terminal
event. Completed operation keys replay across REST/SSE; active generators cannot be
reattached. Public History exposes Message IDs but no operation association.

Use the existing generated REST client/auth/session/origin and one ApiTransport with
an explicitly enabled Agent allowlist. Native streaming uses installed expo/fetch,
not an extra native package. An independent bounded incremental decoder validates
only public V1 envelopes and data. Page generations and session epochs reject stale
events; explicit timeout/abort races cover broken lower-level cancellation.

Retain an immutable logical body/key before dispatch. Unknown outcomes block new
implicit attempts; controlled same-key REST/SSE retries rely on existing server
semantics. History does not establish terminal operation status. Pending metadata
is bounded session memory, with no offline resubmission after restart. A durable
outbox/reconciliation API requires later explicit reliability scope.

Show formal user messages only from History and merge committed assistant answers
by their public Message ID. No body-based deduplication, fabricated timestamp/FIU,
synthetic Connected fallback or token-level animation is introduced. Memory receipt
is read-only. Web/socket evidence and on-device evidence remain distinct.
