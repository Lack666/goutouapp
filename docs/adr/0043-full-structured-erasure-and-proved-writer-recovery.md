# ADR 0043: full structured erasure and proved writer recovery

Accepted for explicitly authorized Phase9H. Frozen Skill, Golden83, semantic Graph
nodes and provider selection remain unchanged. Public production approval is separate.

Person selects its exact owned UUID and all structurally linked Relationships,
Conversations, import Jobs, messages, raw artifacts and Memory/Undo. Relationship
selects one relationship and preserves its Person and other relationships. Text
mentions never enlarge scope. A Person speaker in an outside/unbound Job rejects
erasure. Owner includes unbound imports, general Conversations, owner-only Memory,
controls and inactive upload reservations. Unknown raw-file attribution blocks Owner.

Writes acquire the active owner barrier before domain locks. Erasure uses PostgreSQL
FOR NO KEY UPDATE, conflicting with application SHARE writes without the old FK
KEY SHARE deadlock. Five-minute challenges bind exact domain/UUID, dependency IDs,
content digests and counts. Changed dependencies invalidate preparation. Execute
requires explicit confirmation and immutable owner/key/payload; same-key replay
returns one durable receipt before target lookup. Owner is operator-only through
a signed private stdin request and an owner-specific literal confirmation phrase.
No broad cascade, confirm boolean, production identity or account endpoint is added.

Bodies, speaker/profile labels, Memory and Undo are removed or scrubbed. UUIDs,
original Agent keys/fingerprints, canonical import dedup metadata, count-only receipts
and timestamps remain anti-resurrection metadata for the owner fence lifetime.
Owner tombstoning permanently rejects protected reads/writes under old local JWTs
and UUID recreation. Owned Data erasure does not close a provider identity/account.
Raw unlink is monotonic and cannot roll back with SQL: failures yield no receipt;
SQL rolls back and exact retry completes physical cleanup. No cross-store atomicity
or external-copy erasure is claimed.

Every new AgentRun owns an OS-locked token file in a trusted private shared root.
The original writer acknowledges release only after runtime and persistence end.
Cancellation, disconnect, lost DB pools and age do not prove executor death.
Strong process-lifetime references retain locks across coroutine cancellation.
Offline recovery holds the same OS lock through committed-effect inspection and
receipt commit. It preserves Messages/Memory and original keys, sets failed with
writer_stopped, and records Memory outcome as unknown. It never creates Completed
or reruns Provider. Erasure requires a matching receipt, not recovered_at alone.
Legacy, absent/moved fences and unverified topology remain fail-closed and quarantined
for authoritative operator investigation; no force or timeout reset is available.

Synthetic pg_dump/pg_restore stays quarantined until a frozen complete current
primary supplies exact profile/resource tombstones, keys, Memory and unchanged
erasure/recovery receipts. Unacknowledged writers, missing post-backup effects/fences,
tampered receipts or missing primary deny release. Empty restored raw roots are
required. Independently durable authority and production total-primary-loss recovery
remain separate deployment work.

Mobile uses selected formal details, explicit confirmation, receipt GET and
authoritative 404/list refresh. It invalidates affected session caches before Execute,
guards late responses by owner epoch, retains one immutable volatile unknown attempt
for original-key replay, and clears it on identity change/restart. No durable outbox
or automatic erasure is introduced. Historical evidence stays immutable; changed
executables require new current-source native runs and full service/root regressions.

Native compiled-source evidence also requires an actual Android-accessibility
build marker, enabled only by the existing development acceptance-observer flag.
Metro receives the source/dependency/Expo/Metro/TypeScript configuration digest at
cold build time; the helper cold-starts App JS and checks the compiled digest
before canonical actions and after every open/restart. A disk hash or source-map
sourcesContent alone is insufficient: CI Metro was observed serving an old
compiled Settings string while its source map already described current files.
Missing, stale or conflicting loaded markers fail the scene and the9H gate.
No production App diagnostic, public API, model key or user-content field is added.

The original pre-marker regression on October20 failed Expo's official SDK57
compatibility gate after all backend and repository tests passed. Retain that
failure. Align only four exact patch versions: expo57.0.30, expo-constants57.0.22,
expo-linking57.0.13 and expo-router57.0.28, with the pnpm lockfile. This preserves
SDK57, React Native0.86.3 and the workspace supply-chain policy. Official guidance:
https://docs.expo.dev/workflow/upgrading-expo-sdk-walkthrough/ . Dependency changes
invalidate earlier final-source evidence; run all independent suites, all thirteen
native scenes, the complete wire supplement and both full root gates again.

Retain the r16 Conversation receipt-query failure and its screenshot/coordinates.
The unlabeled Chat FlatList ends above a fixed composer; using screen height for
scroll direction made the helper oscillate at an inverted clipped control. Detect
the actual scrollable viewport as well as the historical labeled History list.
All24 attempts, validity checks, canonical commands and service assertions remain;
three geometry/click/refusal regressions are required. This tooling-only fix changes
the executable fingerprint, so all final validation must run again afterward.
