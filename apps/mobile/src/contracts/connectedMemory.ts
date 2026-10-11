import type { UUID } from '../api/generated/client';
import type { MemoryControlViewModel, MemoryRecordViewModel } from './settings';

export interface MemoryScope {
  readonly personId: UUID | null;
  readonly relationshipId: UUID | null;
}
export interface ConnectedMemoryControl extends MemoryControlViewModel {
  readonly readEnabled: boolean;
  readonly writeEnabled: boolean;
  readonly updatedAt: string | null;
}
export interface ConnectedMemoryRecord
  extends
    MemoryScope,
    Pick<MemoryRecordViewModel, 'summary' | 'createdAt' | 'expiresAt' | 'state'> {
  readonly id: UUID;
  readonly subjectId: UUID;
  readonly type: string;
  readonly source: string;
  readonly provenance: string;
  readonly updatedAt: string;
  readonly retention: string;
  readonly historicalNotice: string;
}
export interface ConnectedUndoPreview extends MemoryScope {
  readonly operationId: UUID;
  readonly memoryId: UUID;
  readonly type: string;
  readonly createdAt: string;
}
export type MemoryAction = 'undo' | 'delete_one' | 'delete_person' | 'delete_all';
export interface ConnectedMemoryChallenge extends MemoryScope {
  readonly id: UUID;
  readonly ownerId: UUID;
  readonly action: Exclude<MemoryAction, 'undo'>;
  readonly targetId: UUID | null;
  readonly expectedCount: number;
  readonly revokeConsent: boolean;
  readonly issuedAt: string;
  readonly expiresAt: string;
  readonly notice: string;
}
export interface ConnectedMemoryReceipt extends MemoryScope {
  readonly id: UUID;
  readonly action: MemoryAction;
  readonly status: 'undone' | 'deleted';
  readonly affectedCount: number;
  readonly targetId: UUID | null;
  readonly undoneMemoryId: UUID | null;
  readonly performedAt: string;
  readonly replayed: boolean;
  readonly primaryStoreOnly: boolean;
  readonly notice: string;
}
export type MemoryMutationPhase =
  | 'idle'
  | 'preparing'
  | 'awaiting_user_confirmation'
  | 'executing'
  | 'completed'
  | 'stale_or_conflict'
  | 'expired'
  | 'failed'
  | 'unknown_outcome';
export interface ConnectedMemoryView {
  readonly scope: MemoryScope;
  readonly control: ConnectedMemoryControl | null;
  readonly items: readonly ConnectedMemoryRecord[];
  readonly cursor: string | null;
  readonly detail: ConnectedMemoryRecord | null;
  readonly undo: ConnectedUndoPreview | null;
  readonly challenge: ConnectedMemoryChallenge | null;
  readonly receipt: ConnectedMemoryReceipt | null;
  readonly allConsentChoice: boolean | null;
  readonly retention: string;
  readonly historicalNotice: string;
  readonly phase: MemoryMutationPhase;
  readonly status: 'idle' | 'loading' | 'ready' | 'error';
  readonly error: string | null;
  readonly feedback: string | null;
  readonly canRetry: boolean;
}
