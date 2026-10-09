# History UI — Phase 7C

Two explicit local views separate **AI 对话** (Agent Chat History) and
**关系聊天** (Imported Relationship Chat History). Neither is a saved server
history. An explicit **加载历史样例（Demo）** action loads anonymous fixtures;
Chat's ephemeral input never writes to this source or appears as saved history.

## Typed domains and deterministic ordering

`src/contracts/history.ts` defines HistorySourceKind, distinct AgentHistoryItem-
ViewModel and RelationshipHistoryItemViewModel, HistoryFilterState and
HistoryPageViewModel. The discriminant `kind` prevents crossing user/assistant
roles with self/person/system senders. Strict TypeScript negative cases reject
cross-domain assignment. Rows render plain selectable text, source/role, raw
speaker label, historical timestamp, dataset/source index, relationship and
synthetic Demo provenance. A Person message is never labeled AI assistant.

`ShellDataSource.readHistory()` supplies fresh, separate arrays. Fixture history
contains 1,020 external messages per relation, system messages, Emoji, paragraphs,
equal timestamps and two datasets. The filter checks the exact relationship ID
before sorting by parsed historical instant, dataset ID, numeric source index
and row ID. Composite keys also include domain and scope. No content dedup exists;
overlapping exports remain a future limitation. Import/creation time is not
historical chat time. The future adapter must provide validated aware timestamps.

## Window, navigation and reset

One FlatList owns header, rows, footer and empty state, with no parent ScrollView.
Initial/batch render is 12 and windowSize is 5. Local data windows start at 30;
**查看更多（Demo）** extends the prefix by at most 30 until exhausted. Filtering/
sorting is memoized, and loading more slices a larger prefix without re-reading
or duplicating pages. The complete synthetic array is still held locally; this
is a bounded render/paging demonstration, not a device performance benchmark or
network-memory bound. There is no network cursor or `onEndReached` request.

Default scope is unselected. External history requires an explicit relationship;
the general AI sample has null scope. A Relationship/Import entry passes its
selected scope; History → Chat/Import keeps it. Unknown scope renders unavailable
and zero messages, with no fallback to another relationship. Repeated query
parameters also fail closed. Relationship choice updates Router params and
remounts its controller, clearing loaded state, kind and window; no A data carries
to B. Type switching starts the local window at 30. Reset/unmount/reload/restart
clears previews; Stack push/back can retain the mounted scoped controller.
Loading/error previews hide rows; Retry restores the existing local window.

## Phase 8 adapter seam and evidence

The external server endpoint already offers owner-scoped keyset `{items,next_cursor}`
with stable timestamp/Job/source-index/row-ID ordering and maximum 200 rows.
The future async adapter must reset resource and cursor on scope/domain changes,
append validated occurrences once and preserve server ordering. The AgentService
has internal conversation history but no equivalent general mobile history-list
contract in the current public Agent endpoints: coordinate it rather than infer
that `readHistory()` maps directly to an existing API. No OpenAPI client exists here.

Tests check every one of 1,020 occurrences, unique keys, reversed-input equal-time
stability, cross-dataset tie-breakers, all local page slices, bounded initial mounting,
type/scope switching, empty/missing scopes, source substitution, Chat separation
and route lifetime. Real browser exercises B-only history, More, AI separation and
scoped Chat in both themes at 320/360/412px. Android scroll/back/insets and TalkBack
were **NOT RUN** in 7C. Phase 7D adds complete six-page Web journeys, A/B domain/window
reset, invalid routes and repeated-scope recovery. Native evidence remains separately
qualified in [final acceptance](PHASE_7_FINAL_ACCEPTANCE.md).
See [acceptance](PHASE_7C_ACCEPTANCE.md) and [imported messages](IMPORTED_MESSAGES.md).
