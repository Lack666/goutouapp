export interface MemoryControlViewModel {
  readonly consentEnabled: boolean;
  readonly paused: boolean;
}
export type MemoryControlAction = 'grant' | 'revoke' | 'pause' | 'resume';
export function previewMemoryControl(
  state: MemoryControlViewModel,
  action: MemoryControlAction,
): MemoryControlViewModel {
  switch (action) {
    case 'grant':
      return { ...state, consentEnabled: true };
    case 'revoke':
      return { consentEnabled: false, paused: true };
    case 'pause':
      return { ...state, paused: true };
    case 'resume':
      return state.consentEnabled ? { ...state, paused: false } : state;
  }
}
export interface MemoryRecordViewModel {
  readonly id: string;
  readonly summary: string;
  readonly subject: 'user' | 'object' | 'relationship';
  readonly personId: string | null;
  readonly relationshipId: string | null;
  readonly createdAt: string;
  readonly expiresAt: string;
  readonly state: 'active' | 'expired';
  readonly provenance: 'synthetic-demo';
}
export interface MemoryUndoPreviewViewModel {
  readonly summary: string;
  readonly expectedOperation: string;
  readonly executable: false;
}
export type MemoryDeleteTarget =
  | { readonly kind: 'one'; readonly recordId: string }
  | { readonly kind: 'person'; readonly personId: string }
  | { readonly kind: 'all'; readonly revokeConsent: boolean | null };
export interface MemoryDeleteConfirmationViewModel {
  readonly target: MemoryDeleteTarget;
  readonly scopeLabel: string;
  readonly affectedCount: number;
  readonly stage: 'review' | 'acknowledged';
  readonly executable: false;
}
export function deletionPreview(
  records: readonly MemoryRecordViewModel[],
  target: MemoryDeleteTarget,
): MemoryDeleteConfirmationViewModel {
  const selected = records.filter(
    (r) =>
      target.kind === 'all' ||
      (target.kind === 'one' ? r.id === target.recordId : r.personId === target.personId),
  );
  return {
    target,
    scopeLabel:
      target.kind === 'all'
        ? '全部主库 Memory（含过期记录）'
        : target.kind === 'person'
          ? `Person ${target.personId} 的对象/关系记忆`
          : `单条记忆 ${target.recordId}`,
    affectedCount: selected.length,
    stage: 'review',
    executable: false,
  };
}
export interface RetentionSummaryViewModel {
  readonly label: string;
  readonly notices: readonly string[];
}
export interface SettingsViewModel {
  readonly control: MemoryControlViewModel;
  readonly records: readonly MemoryRecordViewModel[];
  readonly undo: MemoryUndoPreviewViewModel | null;
  readonly retention: RetentionSummaryViewModel;
}
