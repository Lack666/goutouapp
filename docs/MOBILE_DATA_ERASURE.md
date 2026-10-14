# Connected Mobile self-service erasure — Phase 9F

History lets the signed owner choose a real Relationship and read canonical
Dataset summaries from `GET /api/v1/relationships/{relationship_id}/datasets`.
This remains available after force stop and login: IDs come from PostgreSQL,
never message content, local import state, list position or a Demo UUID.
Only successfully imported canonical Jobs appear; a duplicate ready Job cannot
become a deletion target. Tombstones remain visible with zero current messages
and cannot prepare a new deletion. Provenance includes format/parser/timezone,
source time range, import receipt counts/time and current formal count.

Chat reads the selected owned Conversation through the existing public GET.
Both panels use generated DTOs and the same signed transport/session composition.
Prepare displays the server's exact domain, target, Relationship, counts,
confirmation ID, expiry and retained metadata. Only the explicit confirmation
button sends Execute. Cancel, Back, target change, background, logout and mode
change invalidate unsubmitted confirmations. Demo never calls these endpoints.

The controller binds owner, domain, target, relationship scope, confirmation,
immutable operation key and session epoch. States are `idle`, `preparing`,
`awaiting_confirmation`, `executing`, `completed`, `expired`, `stale`,
`target_busy`, `failed` and `unknown_outcome`. Expiry before submission requires
a new Prepare. Busy does not mutate or time out a Run: a user may refresh and
try again after the server's blocker resolves. Long unresolved Runs currently
require a separate authorized reliability workflow; no automatic deletion exists.

Execute invalidates the exact cached History/cursor, relevant import selection
or Chat request/attempt state. Late completions are generation/epoch guarded.
After a valid Execute response the controller GETs the durable Receipt, refreshes
authoritative History, reloads Dataset metadata or Conversation listing, and
checks old Conversation GET returns 404. A refresh failure is shown separately
from an already confirmed Receipt. Other Datasets and Conversations stay intact.

A lost response stays `unknown_outcome` even if a list is empty. During the same
session, recovery replays the original frozen body/key; a known Receipt can be
inspected without another mutation. No retry creates a new key to bypass Busy,
expiry, a tombstone or uncertainty. Attempts are bounded to 20; metadata windows
are bounded to 200 summaries in pages of 30. There is no persistent deletion
outbox: process restart loses the key and never auto-executes. The App reloads
server state and explains that prior operation attribution may remain unknown.

Dataset erasure physically removes its formal RelationshipMessages and speaker
records under the 9E contract. Canonical Job tombstone/dedup metadata and receipts
remain. Identical same-scope Finalize can return `dataset_deleted`. Conversation
erasure removes all its formal Messages, retains minimal Run/key metadata and
a tombstone; old GET/Agent requests return 404 and recreating its UUID returns409.
Memory, consent, Person, Relationship and other chat domains are independent.
Use existing separate Memory Controls to erase Memory. Neither flow erases an
account or all personal data. Old backups may still contain historical content;
release requires controlled authoritative reconciliation. Primary-loss disaster
recovery, independent deletion journal and production scheduling remain absent.

Validation uses anonymous fixtures only: `pnpm --filter @goutou/mobile test`,
`pnpm --filter @goutou/mobile smoke:erasure`, PostgreSQL dataset-discovery tests,
and independent native scripts in `scripts/native/phase9f_*.json` via the private
Android fixture. Native preconditions use host REST where explicitly marked;
Prepare/Confirm/Execute/Receipt/Refresh are real App actions and signed requests.
Fixture fault controls never mount on the production API. No credential or chat
body enters evidence; request-body digests prove native replay identity.

Acceptance status and exact independent evidence: [9F report](PHASE_9F_ACCEPTANCE.md)
and [matrix](PHASE_9F_MATRIX.json). Web evidence cannot satisfy Android acceptance.
