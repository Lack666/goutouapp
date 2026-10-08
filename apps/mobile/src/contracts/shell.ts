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
  readSurface: (id: SurfaceId, scenario: DemoScenario) => SurfaceState;
}
