import type { ChatScreenViewModel } from './chat';
import type { RelationshipProfileViewModel } from './relationship';
import type { ImportDemoKind, ImportWizardViewModel } from './import';
import type { HistoryPageViewModel } from './history';
import type { SettingsViewModel } from './settings';
export type SurfaceId = 'home' | 'chat' | 'relationship' | 'import' | 'history' | 'settings';
export type DemoScenario = 'empty' | 'loading' | 'error';
export interface SurfaceViewModel {
  readonly id: SurfaceId;
  readonly title: string;
  readonly description: string;
  readonly emptyTitle: string;
  readonly emptyDescription: string;
}
export type SurfaceState =
  | { readonly status: 'loading' }
  | { readonly status: 'empty'; readonly view: SurfaceViewModel }
  | { readonly status: 'error'; readonly message: string };

// UI-facing read seam only. Auth, wire DTOs and network adapters belong to Phase 8.
export interface ShellDataSource {
  readonly kind: 'demo';
  readChat: (relationshipId: string | null) => ChatScreenViewModel;
  readRelationships: () => readonly RelationshipProfileViewModel[];
  readImport: (kind: ImportDemoKind) => ImportWizardViewModel;
  readHistory: () => HistoryPageViewModel;
  readSettings: () => SettingsViewModel;
  readSurface: (id: SurfaceId, scenario: DemoScenario) => SurfaceState;
}
