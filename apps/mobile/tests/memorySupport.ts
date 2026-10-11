import { person, rel, other, jobId, json, token } from './importSupport';
import type { components } from '../src/api/generated/client';
import { ApiTransport } from '../src/api/transport';
import { MemoryController } from '../src/data/memoryController';
import { DevelopmentSession } from '../src/session/developmentSession';
import { createVolatileTokenStorage } from '../src/session/storage';
export { person, rel, other, jobId, json, token };
export const sessions: DevelopmentSession[] = [];
export const time = '2026-10-11T00:00:00Z';
export const control = (
  enabled = true,
  paused = false,
): components['schemas']['MemoryControlView'] => ({
  consent_enabled: enabled,
  paused,
  effective_read_enabled: enabled && !paused,
  effective_write_enabled: enabled && !paused,
  updated_at: time,
});
export const record = (): components['schemas']['MemoryRecordView'] => ({
  id: jobId,
  subject_id: person,
  type: 'relationship',
  content: '匿名合成的明确事实',
  person_id: person,
  relationship_id: rel,
  source: 'user_explicit',
  provenance_summary: 'Public synthetic source',
  created_at: time,
  updated_at: time,
  expires_at: '2026-11-17T00:00:00Z',
  state: 'active',
  retention_policy_summary: 'New memories expire 37 days after creation.',
  historical_notice: 'Historical information may no longer be accurate.',
});
export const preview = (): components['schemas']['UndoPreview'] => ({
  available: true,
  latest_operation_id: other,
  memory_id: jobId,
  type: 'relationship',
  person_id: person,
  relationship_id: rel,
  created_at: time,
});
export const challenge = (
  action = 'delete_one',
  target = jobId as string | null,
  revoke = false,
): components['schemas']['MemoryConfirmationChallenge'] => ({
  confirmation_id: other,
  owner_user_id: person,
  action,
  target_id: target as typeof jobId | null,
  person_id: action === 'delete_all' ? null : person,
  relationship_id: action === 'delete_one' ? rel : null,
  expected_count: 3,
  revoke_consent_after_delete: revoke,
  issued_at: time,
  expires_at: '2026-10-11T00:05:00Z',
  deletion_scope_notice: 'Only primary memory. Chats and backups are outside this operation.',
});
export async function setup(
  handler?: (request: Request) => Promise<Response | undefined>,
  clock = () => Date.parse(time),
) {
  const requests: Request[] = [];
  const session = new DevelopmentSession(createVolatileTokenStorage());
  sessions.push(session);
  let current = control();
  let prepared = challenge();
  const wire: typeof fetch = async (input) => {
    const request = new Request(input);
    requests.push(request.clone());
    const custom = await handler?.(request.clone());
    if (custom) return custom;
    const path = new URL(request.url).pathname;
    if (path === '/api/v1/memory/control') return json(current);
    if (path === '/api/v1/memory/consent') {
      const body = await request.json();
      current = control(body.enabled, body.enabled ? current.paused : true);
      return json(current);
    }
    if (path === '/api/v1/memory/pause' || path === '/api/v1/memory/resume') {
      if (current.consent_enabled) current = control(true, path.endsWith('pause'));
      return json(current);
    }
    if (path === '/api/v1/memories')
      return json({
        items: [record()],
        next_cursor: null,
        retention_policy_summary: record().retention_policy_summary,
        historical_notice: record().historical_notice,
      });
    if (path.startsWith('/api/v1/memories/')) return json(record());
    if (path.endsWith('/undo/preview')) return json(preview());
    if (path.endsWith('/prepare')) {
      const body = await request.json();
      prepared = path.includes('/all/')
        ? challenge('delete_all', null, body.revoke_consent_after_delete)
        : path.includes('/person/')
          ? challenge('delete_person', body.person_id)
          : challenge('delete_one', body.memory_id);
      return json(prepared);
    }
    if (path.endsWith('/undo') || path.endsWith('/execute')) {
      const body = await request.json();
      const undo = path.endsWith('/undo');
      return json({
        mutation_id: rel,
        operation_key: body.operation_key,
        action: undo ? 'undo' : prepared.action,
        status: undo ? 'undone' : 'deleted',
        affected_count: undo ? 1 : prepared.expected_count,
        target_id: undo ? jobId : prepared.target_id,
        person_id: undo ? person : prepared.person_id,
        relationship_id: undo ? rel : prepared.relationship_id,
        undone_memory_id: undo ? jobId : null,
        performed_at: time,
        replayed: false,
        primary_store_only: true,
        deletion_scope_notice: prepared.deletion_scope_notice,
      });
    }
    return json({ error: { code: 'mutation_not_found', message: 'private content' } }, 404);
  };
  const transport = new ApiTransport(
    'http://127.0.0.1:8000',
    session,
    wire,
    500,
    true,
    false,
    wire,
    500,
    false,
    500,
    true,
  );
  const controller = new MemoryController(transport, session, () => person, clock);
  await session.connect(token(), async () => undefined);
  return { controller, requests, session, transport };
}
