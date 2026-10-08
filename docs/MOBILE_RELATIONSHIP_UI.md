# Relationship/Profile UI — Phase 7B

`PersonViewModel` has its own ID and nullable display nickname.
`RelationshipProfileViewModel` has a different ID, display name, person,
nullable relationship label and interaction time, known/missing lists,
optional historical metadata and analysis summary, and explicit Demo source.
There is no default romantic relationship or inferred boyfriend/girlfriend/ex.

Person is a contact; Relationship is its contextual relation. Imported
RelationshipMessage uses self/person/system and stored provenance; an Agent
conversation message uses user/assistant. The profile contract contains no
imported message body, and no profile metadata becomes an assistant bubble.
Source IDs are synthetic UI scopes, never authenticated owners/database IDs.

## Local profile interaction

`ShellDataSource.readRelationships()` supplies fresh nested ViewModels through
the existing DataSourceProvider. Screen imports only typed presentation data,
not fixture files. RelationshipScreen memoizes one read per source instance,
tracks only the selected ID, and derives every card from the selected profile.
Switching A/B replaces the complete card content, including person nickname,
label, interaction time, known/missing information and history metadata.

Demo A is a generic classmate relation with clearly synthetic activity metadata.
Demo B has a missing nickname, type, interaction time, history and analysis.
Missing values render **未提供**, with an empty history/analysis explanation;
no substitute name, date, romantic status or conclusion is invented. Empty
injected sources show EmptyState and omit scoped Chat/Import actions. Neither
demo has a completed analysis. No private chat fixtures are used.

The profile includes title/current relationship, Person, known information,
missing information, history and analysis placeholders, source explanation,
Chat/Import/History navigation and disabled real editing. History and Import
remain Phase 7A shells and say their business features are unconnected.
Navigation does not start a task or upload/parse/analyze a file.

Chat navigation passes the selected synthetic relationshipId via Router params.
Chat's template shows that scope; unsupported IDs display **关系未提供** rather
than falling back to A's profile. Changing Chat scope clears its local state.
Back returns to the still-mounted profile with the same selected relationship.
Reload/remount resets profile selection to the first supplied entry; it never
stores a preferred relationship or authenticated account.

Loading/error/empty controls retain the 7A Demo state seam. Error Retry resets
the local scenario and restores the selected card. The regular profile view
does not also display the old misleading empty-profile shell beneath real Demo
cards. Nothing is fetched, logged, persisted or written to Memory.

## Layout, accessibility and future integration

Reuse ScreenContainer, theme tokens and the Stack; cards wrap inside bounded
scrolling width. Selector controls expose labels, native selected state, Web
aria-pressed and a selected border. Disabled edit has disabled semantics.
Headers and missing-data explanations remain readable in light/dark modes.
Tests locate controls by role/label, substitute an empty source, inspect fresh
fixture reads and verify A fields disappear after switching to B.

Phase 8 requires an owner-scoped resource/controller and adapter. Existing
server Agent answers do not supply this structured profile ViewModel; the
future contract must be coordinated without exposing internal memory evidence
or treating imported chat as an Agent conversation. Read this UI contract with
[Imported messages](IMPORTED_MESSAGES.md), [Agent API](AGENT_API.md) and
[Chat UI](MOBILE_CHAT_UI.md). Phase 7B does not modify those server contracts.

Browser smoke covers both themes at 320/360/412px, A/B switching, scoped Chat,
Back, Import shell and reload policy. Screenshots and zero-request/error evidence
are recorded in [7B acceptance](PHASE_7B_ACCEPTANCE.md). Android native smoke
and TalkBack are NOT RUN; Web/Jest do not substitute for native validation.
