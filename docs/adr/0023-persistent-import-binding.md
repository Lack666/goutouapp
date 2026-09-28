# ADR 0023 — Persistent import job and explicit binding boundary

Date: 2026-09-28. Status: accepted for Phase 5B.

The Phase 5A parser has no identity or persistence authority. We persist only
its summary and raw speaker counts in `chat_import_jobs` and
`chat_import_speakers`. The service rejects fatal parse results instead of
creating failed jobs; a failed parse has no viable transcript fingerprint to
bind or resume. Source bytes and message bodies remain outside job metadata.

Identity binding is a user action through `AuthenticatedActor`. The job owner
is the only possible `self`; `person` and Relationship targets are validated in
the same owner scope by the service and composite foreign keys. The V1
one-to-one gate requires one self, one person, and explicit disposition of all
other labels. No LLM or nickname heuristic participates.

Ready is a reversible pre-import state. Any binding edit increments a revision
and returns the job to awaiting binding; marking ready rechecks all rules under
a job row lock. Cancellation is terminal for this phase and preserves metadata
for audit. Duplicate transcript fingerprints provide only a hint; occurrence
identity and idempotent merge are Phase 5C concerns. An imported occurrence
must include source position within a verified job, never a message fingerprint
alone. Phase 5D may add upload artifacts and explicit Person creation.
