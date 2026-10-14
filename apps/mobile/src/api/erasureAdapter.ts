import type { components } from './generated/client';
import { asUUID } from './uuid';
import { awareTimestamp } from './importAdapter';
import { ApiError } from './errors';

export type ErasureTarget = Readonly<components['schemas']['ErasureTarget']>;
export type ErasureChallenge = Readonly<components['schemas']['ErasureChallenge']>;
export type ErasureReceipt = Readonly<components['schemas']['ErasureResult']>;
export type Dataset = Readonly<components['schemas']['DatasetSummary']>;
export function check(value: unknown): asserts value {
  if (!value) throw new ApiError('protocol');
}
export const sameTarget = (a: ErasureTarget, b: ErasureTarget) =>
  a.domain === b.domain &&
  a.target_id === b.target_id &&
  (a.relationship_id ?? null) === (b.relationship_id ?? null);
export function targetView(dto: ErasureTarget): ErasureTarget {
  check(dto.domain === 'dataset' || dto.domain === 'conversation');
  check(dto.domain !== 'dataset' || dto.relationship_id != null);
  return Object.freeze({
    domain: dto.domain,
    target_id: asUUID(dto.target_id),
    relationship_id: dto.relationship_id == null ? null : asUUID(dto.relationship_id),
  });
}
const count = (n: number) => {
  check(Number.isSafeInteger(n) && n >= 0);
  return n;
};
function scopeView(dto: ErasureChallenge | ErasureReceipt, expected: ErasureTarget) {
  const target = targetView(dto);
  check(sameTarget(target, expected) && dto.memory_affected === false);
  return {
    ...target,
    confirmation_id: asUUID(dto.confirmation_id),
    message_count: count(dto.message_count),
    run_count: count(dto.run_count),
    memory_affected: false as const,
  };
}
export function challengeView(dto: ErasureChallenge, expected: ErasureTarget): ErasureChallenge {
  check(typeof dto.retained_metadata === 'string' && dto.retained_metadata.length <= 2000);
  return Object.freeze({
    ...scopeView(dto, expected),
    expires_at: awareTimestamp(dto.expires_at),
    retained_metadata: dto.retained_metadata,
  });
}
export function receiptView(
  dto: ErasureReceipt,
  expected: ErasureTarget,
  confirmation: string,
): ErasureReceipt {
  check(dto.status === 'deleted' && dto.confirmation_id === confirmation);
  return Object.freeze({
    ...scopeView(dto, expected),
    receipt_id: asUUID(dto.receipt_id),
    performed_at: awareTimestamp(dto.performed_at),
    status: 'deleted' as const,
  });
}
export function datasetView(dto: Dataset, relationship: string): Dataset {
  check(asUUID(dto.relationship_id) === relationship && typeof dto.deletable === 'boolean');
  check(dto.deletable === (dto.deleted_at === null));
  const counts = {
    imported_message_count: count(dto.imported_message_count),
    current_message_count: count(dto.current_message_count),
    ignored_message_count: count(dto.ignored_message_count),
    system_message_count: count(dto.system_message_count),
  };
  check(dto.deleted_at === null || counts.current_message_count === 0);
  for (const value of [dto.source_format, dto.parser_version, dto.source_timezone])
    check(typeof value === 'string' && value.length > 0 && value.length <= 100);
  return Object.freeze({
    dataset_job_id: asUUID(dto.dataset_job_id),
    relationship_id: asUUID(dto.relationship_id),
    ...counts,
    source_format: dto.source_format,
    parser_version: dto.parser_version,
    source_timezone: dto.source_timezone,
    first_timestamp_utc: awareTimestamp(dto.first_timestamp_utc),
    last_timestamp_utc: awareTimestamp(dto.last_timestamp_utc),
    imported_at: awareTimestamp(dto.imported_at),
    deleted_at: dto.deleted_at === null ? null : awareTimestamp(dto.deleted_at),
    deletable: dto.deletable,
  });
}
