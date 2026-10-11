import type { components } from './generated/client';
import { asUUID } from './uuid';
import { awareTimestamp } from './importAdapter';
import { ApiError } from './errors';
import type {
  ConnectedMemoryControl,
  ConnectedMemoryRecord,
  ConnectedUndoPreview,
  ConnectedMemoryChallenge,
  ConnectedMemoryReceipt,
  MemoryAction,
} from '../contracts/connectedMemory';
export function memoryCheck(value: unknown): asserts value {
  if (!value) throw new ApiError('protocol');
}
const nullableID = (value: string | null) => (value === null ? null : asUUID(value));
const text = (value: string) => {
  memoryCheck(typeof value === 'string');
  return value;
};
const count = (value: number) => {
  memoryCheck(Number.isSafeInteger(value) && value >= 0);
  return value;
};
export function memoryControlView(
  dto: components['schemas']['MemoryControlView'],
): ConnectedMemoryControl {
  memoryCheck(
    [
      dto.consent_enabled,
      dto.paused,
      dto.effective_read_enabled,
      dto.effective_write_enabled,
    ].every((v) => typeof v === 'boolean'),
  );
  return {
    consentEnabled: dto.consent_enabled,
    paused: dto.paused,
    readEnabled: dto.effective_read_enabled,
    writeEnabled: dto.effective_write_enabled,
    updatedAt: dto.updated_at === null ? null : awareTimestamp(dto.updated_at),
  };
}
export function memoryRecordView(
  dto: components['schemas']['MemoryRecordView'],
): ConnectedMemoryRecord {
  memoryCheck(['active', 'expired'].includes(dto.state));
  return {
    id: asUUID(dto.id),
    subjectId: asUUID(dto.subject_id),
    type: text(dto.type),
    summary: text(dto.content),
    personId: nullableID(dto.person_id),
    relationshipId: nullableID(dto.relationship_id),
    source: text(dto.source),
    provenance: text(dto.provenance_summary),
    createdAt: awareTimestamp(dto.created_at),
    updatedAt: awareTimestamp(dto.updated_at),
    expiresAt: awareTimestamp(dto.expires_at),
    state: dto.state as 'active' | 'expired',
    retention: text(dto.retention_policy_summary),
    historicalNotice: text(dto.historical_notice),
  };
}
export function memoryListView(dto: components['schemas']['MemoryListResult']) {
  memoryCheck(Array.isArray(dto.items) && dto.items.length <= 50);
  memoryCheck(
    dto.next_cursor === null ||
      (typeof dto.next_cursor === 'string' &&
        dto.next_cursor.length > 0 &&
        dto.next_cursor.length <= 256),
  );
  const items = dto.items.map(memoryRecordView);
  memoryCheck(items.every((item) => item.state === 'active'));
  return {
    items,
    cursor: dto.next_cursor,
    retention: text(dto.retention_policy_summary),
    historicalNotice: text(dto.historical_notice),
  };
}
export function memoryUndoView(
  dto: components['schemas']['UndoPreview'],
): ConnectedUndoPreview | null {
  memoryCheck(typeof dto.available === 'boolean');
  if (!dto.available) return null;
  memoryCheck(dto.latest_operation_id && dto.memory_id && dto.created_at && dto.type);
  return {
    operationId: asUUID(dto.latest_operation_id),
    memoryId: asUUID(dto.memory_id),
    type: text(dto.type),
    createdAt: awareTimestamp(dto.created_at),
    personId: nullableID(dto.person_id ?? null),
    relationshipId: nullableID(dto.relationship_id ?? null),
  };
}
export function memoryChallengeView(
  dto: components['schemas']['MemoryConfirmationChallenge'],
): ConnectedMemoryChallenge {
  memoryCheck(
    ['delete_one', 'delete_person', 'delete_all'].includes(dto.action) &&
      typeof dto.revoke_consent_after_delete === 'boolean',
  );
  memoryCheck(Date.parse(dto.expires_at) > Date.parse(dto.issued_at));
  return {
    id: asUUID(dto.confirmation_id),
    ownerId: asUUID(dto.owner_user_id),
    action: dto.action as ConnectedMemoryChallenge['action'],
    targetId: nullableID(dto.target_id),
    personId: nullableID(dto.person_id),
    relationshipId: nullableID(dto.relationship_id),
    expectedCount: count(dto.expected_count),
    revokeConsent: dto.revoke_consent_after_delete,
    issuedAt: awareTimestamp(dto.issued_at),
    expiresAt: awareTimestamp(dto.expires_at),
    notice: text(dto.deletion_scope_notice),
  };
}
export function memoryReceiptView(
  dto: components['schemas']['MemoryMutationReceipt'],
): ConnectedMemoryReceipt {
  memoryCheck(['undo', 'delete_one', 'delete_person', 'delete_all'].includes(dto.action));
  memoryCheck(dto.status === (dto.action === 'undo' ? 'undone' : 'deleted'));
  memoryCheck(typeof dto.replayed === 'boolean' && dto.primary_store_only === true);
  return {
    id: asUUID(dto.mutation_id),
    action: dto.action as MemoryAction,
    status: dto.status as ConnectedMemoryReceipt['status'],
    affectedCount: count(dto.affected_count),
    targetId: nullableID(dto.target_id),
    personId: nullableID(dto.person_id),
    relationshipId: nullableID(dto.relationship_id),
    undoneMemoryId: nullableID(dto.undone_memory_id),
    performedAt: awareTimestamp(dto.performed_at),
    replayed: dto.replayed,
    primaryStoreOnly: dto.primary_store_only,
    notice: text(dto.deletion_scope_notice),
  };
}
