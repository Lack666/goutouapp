export type HistorySourceKind = 'agent' | 'relationship';
interface HistoryBase {
  readonly id: string;
  readonly relationshipId: string | null;
  readonly content: string;
  readonly timestamp: string;
  readonly datasetId: string;
  readonly sourceIndex: number;
  readonly provenance: 'synthetic-demo';
}
export interface AgentHistoryItemViewModel extends HistoryBase {
  readonly kind: 'agent';
  readonly role: 'user' | 'assistant';
}
export interface RelationshipHistoryItemViewModel extends HistoryBase {
  readonly kind: 'relationship';
  readonly relationshipId: string;
  readonly sender: 'self' | 'person' | 'system';
  readonly rawSpeakerLabel: string;
}
export type HistoryItemViewModel = AgentHistoryItemViewModel | RelationshipHistoryItemViewModel;
export interface HistoryPageViewModel {
  readonly agent: readonly AgentHistoryItemViewModel[];
  readonly relationship: readonly RelationshipHistoryItemViewModel[];
}
export interface HistoryFilterState {
  readonly kind: HistorySourceKind;
  readonly relationshipId: string | null;
}
export const HISTORY_PAGE_SIZE = 30;
export const historyKey = (item: HistoryItemViewModel) =>
  `${item.kind}:${item.relationshipId ?? 'general'}:${item.datasetId}:${item.sourceIndex}:${item.id}`;
const compareString = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
export function sortHistory<T extends HistoryItemViewModel>(items: readonly T[]): T[] {
  return [...items].sort(
    (a, b) =>
      Date.parse(a.timestamp) - Date.parse(b.timestamp) ||
      compareString(a.datasetId, b.datasetId) ||
      a.sourceIndex - b.sourceIndex ||
      compareString(a.id, b.id),
  );
}
export function filterHistory(
  model: HistoryPageViewModel,
  filter: HistoryFilterState,
): HistoryItemViewModel[] {
  const items: readonly HistoryItemViewModel[] =
    filter.kind === 'agent' ? model.agent : model.relationship;
  return sortHistory(items.filter((m) => m.relationshipId === filter.relationshipId));
}
