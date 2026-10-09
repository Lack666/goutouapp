import type { UUID } from './generated/client';
import { ApiError } from './errors';
const pattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export function asUUID(value: string): UUID {
  if (!pattern.test(value)) throw new ApiError('validation');
  return value as UUID;
}
export function asUUIDv4(value: string): UUID {
  const id = asUUID(value);
  if (id[14] !== '4') throw new ApiError('validation');
  return id;
}
