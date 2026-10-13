import { erasureHTTPError } from '../src/api/erasureErrors';
import { importHTTPError } from '../src/api/importErrors';
import { operationInventory } from '../src/api/generated/client';

it('exposes only three signed exact-target erasure contracts', () => {
  const operations = operationInventory.filter((op) => op.path.startsWith('/api/v1/erasures'));
  expect(operations.map((op) => [op.method, op.path])).toEqual([
    ['post', '/api/v1/erasures/execute'],
    ['post', '/api/v1/erasures/prepare'],
    ['get', '/api/v1/erasures/receipts/{receipt_id}'],
  ]);
  expect(operations.every((op) => op.bearer)).toBe(true);
});
it.each([
  'confirmation_expired',
  'confirmation_mismatch',
  'target_changed',
  'target_busy',
  'target_deleted',
  'idempotency_conflict',
])('maps %s without retaining private response fields', (code) => {
  const error = erasureHTTPError(
    409,
    JSON.stringify({ error: { code, message: 'private-sentinel' } }),
  );
  expect(error.message).not.toContain('private-sentinel');
  expect(error.kind).toBe('conflict');
});
it('drops unknown/malformed errors and preserves authentication invalidation', () => {
  expect(erasureHTTPError(401, 'private-sentinel').kind).toBe('unauthorized');
  expect(erasureHTTPError(409, '{bad').message).not.toContain('{bad');
  expect(erasureHTTPError(503, '{"error":{"code":"private-sentinel"}}').kind).toBe('unavailable');
});
it('explains deleted canonical dataset instead of suggesting a silent reimport', () => {
  expect(importHTTPError(409, '{"error":{"code":"dataset_deleted"}}').message).toContain('已删除');
});
