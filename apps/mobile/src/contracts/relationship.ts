export interface PersonViewModel {
  readonly id: string;
  readonly nickname: string | null;
}
export interface RelationshipProfileViewModel {
  readonly id: string;
  readonly displayName: string;
  readonly person: PersonViewModel;
  readonly label: string | null;
  readonly lastInteraction: string | null;
  readonly known: readonly string[];
  readonly missing: readonly string[];
  readonly historySummary: string | null;
  readonly analysisSummary: string | null;
  readonly source: 'demo' | 'server';
}
// Imported RelationshipMessage (self/person/system) is deliberately absent.
// Summary metadata never becomes an Agent assistant message.
