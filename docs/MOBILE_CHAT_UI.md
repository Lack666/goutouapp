# Chat UI — Phase 7B

This is an anonymous local Demo, using the existing SDK 57 theme and Router
Stack. No Agent API, SSE, authentication, persistence or memory mutation exists
in Mobile. Assistant content is an explicitly requested, predefined synthetic
example. Adding input never creates an assistant reply.

## Presentation contracts

`src/contracts/chat.ts` contains `AgentChatMessageViewModel` (stable ID,
user/assistant role, plain text, readable time, synthetic-demo/local-preview
source), `ChatThreadViewModel` (thread and optional relationship scope),
`ChatComposerState`, `ChatRunPresentationState` and `ChatScreenViewModel`.
Only public user/assistant content is allowed; imported self/person/system
speakers and tool/internal messages cannot use this role type. No hidden
reasoning, prompt, tool arguments, secrets or raw memory evidence is included.

`ShellDataSource.readChat(relationshipId)` is an injected, read-only demo template.
Its messages are available through **替换为合成对话示例**, which explicitly
replaces the displayed local list. The initial list is empty. Screen/components
do not import fixture modules. Reads allocate fresh nested values. Phase 8 must
add a real resource/controller and adapter; this synchronous Demo template is
not an API response or an automatically loaded conversation.

## List and composer

One React Native FlatList owns the scrolling header, optional state controls,
examples and message rows. It is not inside a ScrollView. Stable IDs, rather
than timestamps, supply keys; equal-time messages retain supplied order. Memoized
bubbles use plain selectable Text, wrapping Chinese, emoji and paragraphs without
executing HTML/Markdown. User/assistant labels, time and Demo provenance are
visible. Initial/batch rendering is 12 with windowSize 5. No list sorting,
pairwise lookup or full-list message conversion is done; append copies once.
The 1,000-message test checks unique keys, complete order, same-time preservation,
immutable append to 1,001 and at most 12 initially mounted rows. It is not a
device performance benchmark or proof of every offscreen row's native layout.

The fixed composer sits outside the list, within SafeAreaView and
KeyboardAvoidingView. Input is multiline, scrolls at its maximum height and has
a 2,000 UTF-16 code-unit limit (emoji can occupy two units). Native maxLength
and the controlled handler both enforce the limit. Empty/whitespace-only input
cannot be previewed; Clear empties the input. Starting, progressing and pending
confirmation disable typing and actions. Preview trims outer whitespace,
appends exactly one user bubble, clears input and reports **仅在本地预览，尚未发送给 AI**.
New-message content size triggers scrolling to the last message. The composer
always retains its Demo/no-send/no-save notice when the header scrolls away.

Draft, bubbles, feedback and selected preview state are React state scoped to
that mounted Chat route. Back that removes the route, reload and app restart
clear them. A still-mounted route retains local state; changing relationship
scope remounts ChatSession and clears draft/messages/feedback. Theme is separately
root-session scoped. No logging, storage, history write or upload occurs.

## Explicit state preview

**演示状态预览** expands a small local selector. All states are manually held;
no timer, heartbeat, token animation or network connection advances them.
The display state is independent of the local list; changing state does not
erase input or generate messages.

- idle: local ready/empty presentation, server unconnected.
- unavailable: unconnected explanation, no retryable network operation.
- starting: labeled loading demonstration; composer disabled.
- progressing: labeled progress demonstration; composer disabled.
- completed: predefined FIU teaching card, no new response or real analysis.
- failed: safe alert; Retry is explicitly **Demo state reset**, restoring idle
  while preserving local messages/draft. No SQL/provider/server exception is shown.
- pending_confirmation: explanatory text and disabled execution entry. It cannot
  submit an Undo/Delete or bypass the Phase 6B server-issued confirmation challenge.

Phase 4 SSE sends run_started/status/final_response/memory_status/
pending_confirmation/completed/failed. Future integration displays status and
then the complete public answer; it must not assume token-by-token streaming.
The current REST/SSE answer DTO does **not** expose structured FIU or a profile
resource. Phase 8 must coordinate a public mapping/contract before rendering
real FIU/profile data. Internal AgentResult is not a Mobile wire contract.

## FIU, safety and accessibility

`FiuPreviewItem` distinguishes facts with synthetic provenance, inferences with
an alternative explanation, and unknowns. The completed preview explicitly says
it has not analyzed input. It makes no success probability, psychological
diagnosis, mind-reading claim or manipulative recommendation. A neutral safety
notice reserves a place for future public Safety results; no client classifier
or model inference exists. The full analysis surface remains Phase 7C.

Input has a readable label and disabled semantics; preview/Clear are buttons;
message labels include sender; errors use alert and status/feedback use polite
announcements. Selection has native selected state and explicit Web aria-pressed
because this installed RN Web does not translate accessibilityState.selected.
Selected controls also have a visible border. Native TalkBack is NOT RUN.

## Evidence

Jest covers composer, role isolation, ordering, all seven states, FIU,
confirmation, substituted source, changed scope, local lifetime and no fetch/log.
Real Expo Web smoke covers Home → Chat → typing/preview → states → Home →
Relationship A/B → scoped Chat → Back, plus Import shell navigation. Six runs
cover light/dark at 320/360/412px. Last-bubble geometry is checked above the
composer, long messages scroll, and external/business requests and page errors
must be zero. Screenshots live under ignored `.cache/phase7b-*.png`; visual
review and exact results are recorded in [7B acceptance](PHASE_7B_ACCEPTANCE.md).
Android keyboard, insets, hardware Back and TalkBack remain NOT RUN.
