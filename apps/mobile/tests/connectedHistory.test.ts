import { HistoryController } from '../src/data/historyController';
import { relationshipHistoryView } from '../src/api/importAdapter';
import { historyKey } from '../src/contracts/history';
import { asUUID } from '../src/api/uuid';
import { setup, sessions, rel, other, person, jobId, json, token } from './importSupport';
import type { components } from '../src/api/generated/client';
afterEach(async () => {
  for (const session of sessions.splice(0)) await session.logout();
});
const id = (index: number) => asUUID(`00000000-0000-4000-8000-${String(index).padStart(12, '0')}`);
const message = (
  index: number,
  relationshipId = rel,
): components['schemas']['RelationshipMessageResponse'] => ({
  id: id(index),
  relationship_id: relationshipId,
  import_job_id: jobId,
  source_index: index,
  timestamp_utc: '2024-01-01T00:00:00.000001Z',
  original_timestamp: '2024-01-01 08:00:00',
  source_timezone: 'Asia/Shanghai',
  sender_kind: 'person',
  person_id: person,
  raw_speaker_label: '匿名🥰',
  content: '同内容的不同消息',
  content_type: 'text',
  message_fingerprint: 'c'.repeat(64),
});
it('relationship DTO preserves every public provenance/time/sender field and stable ID', () => {
  const item = relationshipHistoryView(message(1), rel);
  expect(item).toMatchObject({
    kind: 'relationship',
    provenance: 'server',
    sender: 'person',
    rawSpeakerLabel: '匿名🥰',
    sourceIndex: 1,
    datasetId: jobId,
    originalTimestamp: '2024-01-01 08:00:00',
    sourceTimezone: 'Asia/Shanghai',
    personId: person,
  });
  expect(item.timestamp).toBe('2024-01-01T00:00:00.000001Z');
  expect(historyKey(item)).toContain(id(1));
});
it.each([
  { sender_kind: 'assistant' },
  { relationship_id: other },
  { timestamp_utc: '2024-01-01T00:00:00' },
  { person_id: null },
  { id: 'demo-a' },
])('rejects malformed/cross-domain or foreign DTO %p', (patch) => {
  expect(() =>
    relationshipHistoryView(
      { ...message(1), ...patch } as components['schemas']['RelationshipMessageResponse'],
      rel,
    ),
  ).toThrow();
});
it('opaque cursor is forwarded unchanged and overlapping server IDs merge without content dedup', async () => {
  const opaque = 'uninterpreted+/= cursor';
  let calls = 0;
  const { transport, session, requests } = await setup(async (r) => {
    if (r.url.includes('/messages')) {
      calls++;
      if (calls === 1) return json({ items: [message(1), message(2)], next_cursor: opaque });
      expect(new URL(r.url).searchParams.get('cursor')).toBe(opaque);
      return json({ items: [message(2), message(3)], next_cursor: null });
    }
  });
  const history = new HistoryController(transport, session, 2);
  await history.open('relationship', rel);
  await history.load(true);
  expect(history.snapshot().items.map((m) => m.id)).toEqual([id(1), id(2), id(3)]);
  expect(history.snapshot().cursor).toBeNull();
  expect(
    requests
      .filter((r) => r.url.includes('/messages'))
      .every((r) => new URL(r.url).searchParams.get('limit') === '2'),
  ).toBe(true);
});
it('1001 occurrences across eleven pages preserve equal timestamps, repeated text and server order', async () => {
  const { transport, session } = await setup(async (r) => {
    if (r.url.includes('/messages')) {
      const start = Number(new URL(r.url).searchParams.get('cursor') ?? 0);
      return json({
        items: Array.from({ length: Math.min(100, 1001 - start) }, (_, i) =>
          message(start + i + 1),
        ),
        next_cursor: start + 100 < 1001 ? String(start + 100) : null,
      });
    }
  });
  const history = new HistoryController(transport, session);
  await history.open('relationship', rel);
  while (history.snapshot().cursor) await history.load(true);
  expect(history.snapshot().items).toHaveLength(1001);
  expect(new Set(history.snapshot().items.map((m) => m.id)).size).toBe(1001);
  expect(history.snapshot().items.at(-1)?.id).toBe(id(1001));
});
it('concurrent More requests execute once; final-page More is a no-op', async () => {
  let calls = 0;
  const { transport, session } = await setup(async (r) =>
    r.url.includes('/messages')
      ? json({ items: [message(++calls)], next_cursor: calls === 1 ? 'opaque' : null })
      : undefined,
  );
  const history = new HistoryController(transport, session, 1);
  await history.open('relationship', rel);
  await Promise.all([history.load(true), history.load(true), history.load(true)]);
  await history.load(true);
  expect(calls).toBe(2);
  expect(history.snapshot().items).toHaveLength(2);
});
it('page failure retains known rows/cursor and controlled More retry continues them', async () => {
  let calls = 0;
  const { transport, session } = await setup(async (r) => {
    if (r.url.includes('/messages')) {
      calls++;
      if (calls === 2) return json({ error: { code: 'import_failed', message: 'private' } }, 503);
      return json({
        items: [message(calls === 1 ? 1 : 2)],
        next_cursor: calls === 1 ? 'opaque' : null,
      });
    }
  });
  const history = new HistoryController(transport, session, 1);
  await history.open('relationship', rel);
  await history.load(true);
  expect(history.snapshot().status).toBe('error');
  expect(history.snapshot().cursor).toBe('opaque');
  expect(history.snapshot().items).toHaveLength(1);
  await history.load(true);
  expect(history.snapshot().items).toHaveLength(2);
  expect(history.snapshot().status).toBe('ready');
});
it('empty formal history stays empty and refresh after import reads actual new rows', async () => {
  let imported = false;
  const { transport, session } = await setup(async (r) =>
    r.url.includes('/messages')
      ? json({ items: imported ? [message(1)] : [], next_cursor: null })
      : undefined,
  );
  const history = new HistoryController(transport, session);
  await history.open('relationship', rel);
  expect(history.snapshot().items).toHaveLength(0);
  imported = true;
  await history.load();
  expect(history.snapshot().items).toHaveLength(1);
});
it('refresh after external Dataset erasure drops cached rows and the old cursor', async () => {
  let erased = false;
  const { transport, session, requests } = await setup(async (r) =>
    r.url.includes('/messages')
      ? json({ items: erased ? [] : [message(1)], next_cursor: erased ? null : 'old-page' })
      : undefined,
  );
  const history = new HistoryController(transport, session, 1);
  await history.open('relationship', rel);
  expect(history.snapshot().cursor).toBe('old-page');
  erased = true;
  await history.load();
  expect(history.snapshot().items).toEqual([]);
  expect(history.snapshot().cursor).toBeNull();
  expect(
    new URL(requests.filter((r) => r.url.includes('/messages')).at(-1)!.url).searchParams.has(
      'cursor',
    ),
  ).toBe(false);
});
it('reopening an externally erased Conversation clears its cached body and denies the old scope', async () => {
  let erased = false;
  const { transport, session } = await setup(async (r) => {
    if (!r.url.includes('/conversations/')) return undefined;
    if (erased) return json({ error: { code: 'not_found', message: 'private' } }, 404);
    if (!r.url.includes('/messages')) return json({ id: other, relationship_id: null });
    return json({
      items: [
        {
          id: id(1),
          conversation_id: other,
          role: 'assistant',
          content: 'synthetic answer',
          created_at: '2024-01-01T00:00:00Z',
        },
      ],
      next_cursor: 'old-page',
    });
  });
  const history = new HistoryController(transport, session, 1);
  await history.open('agent', other);
  expect(history.snapshot().items).toHaveLength(1);
  erased = true;
  await history.open('agent', other);
  expect(history.snapshot().status).toBe('error');
  expect(history.snapshot().items).toEqual([]);
  expect(history.snapshot().cursor).toBeNull();
  expect(history.snapshot().parentId).toBeNull();
});
it('switching relationship aborts old pages, resets cursors and rejects ignored-abort late responses', async () => {
  let resolve!: (value: Response) => void;
  let captured: AbortSignal | undefined;
  const { transport, session } = await setup(async (r) => {
    if (r.url.includes('/messages') && r.url.includes(rel)) {
      captured = r.signal;
      return new Promise((done) => {
        resolve = done;
      });
    }
    if (r.url.includes(`/relationships/${other}`))
      return r.url.includes('/messages')
        ? json({ items: [message(2, other)], next_cursor: null })
        : json({ id: other, person_id: person });
  });
  const history = new HistoryController(transport, session);
  const first = history.open('relationship', rel);
  while (!resolve) await new Promise((done) => setTimeout(done, 0));
  const second = history.open('relationship', other);
  expect(captured?.aborted).toBe(true);
  resolve(json({ items: [message(1)], next_cursor: 'old' }));
  await Promise.all([first, second]);
  expect(history.snapshot().items.map((m) => m.id)).toEqual([id(2)]);
  expect(history.snapshot().parentId).toBe(other);
  expect(history.snapshot().cursor).toBeNull();
});
it('logout and User B clear scope, cursor and rows and reject late responses', async () => {
  const { transport, session } = await setup(async (r) =>
    r.url.includes('/messages') ? json({ items: [message(1)], next_cursor: 'opaque' }) : undefined,
  );
  const history = new HistoryController(transport, session, 1);
  await history.open('relationship', rel);
  await session.logout();
  expect(history.snapshot().items).toEqual([]);
  expect(history.snapshot().parentId).toBeNull();
  expect(history.snapshot().cursor).toBeNull();
  await session.connect(token(other), async () => undefined);
  expect(history.snapshot().items).toEqual([]);
});
it('route unmount clears records/cursor; background resume verifies and refreshes original owned scope', async () => {
  const { transport, session } = await setup(async (r) =>
    r.url.includes('/messages') ? json({ items: [message(1)], next_cursor: null }) : undefined,
  );
  const history = new HistoryController(transport, session);
  await history.open('relationship', rel);
  history.pause();
  expect(history.snapshot().items).toEqual([]);
  await history.resume();
  expect(history.snapshot().items).toHaveLength(1);
  history.leave();
  await history.resume();
  expect(history.snapshot().items).toEqual([]);
});
it('Agent/Relationship switches use different endpoints and never relabel external Person as assistant', async () => {
  const { transport, session, requests } = await setup(async (r) => {
    if (r.url.includes('/conversations/') && !r.url.includes('/messages'))
      return json({ id: other, relationship_id: null });
    if (r.url.includes('/conversations/') && r.url.includes('/messages'))
      return json({
        items: [
          {
            id: id(2),
            conversation_id: other,
            role: 'assistant',
            content: '服务器合成回答',
            created_at: '2026-10-10T00:00:00Z',
          },
        ],
        next_cursor: null,
      });
    if (r.url.includes('/relationships/') && r.url.includes('/messages'))
      return json({ items: [message(1)], next_cursor: null });
  });
  const history = new HistoryController(transport, session);
  await history.open('relationship', rel);
  expect(history.snapshot().items[0]?.kind).toBe('relationship');
  await history.open('agent', other);
  expect(history.snapshot().items[0]).toMatchObject({ kind: 'agent', role: 'assistant' });
  expect(history.snapshot().items).toHaveLength(1);
  expect(requests.some((r) => r.url.includes(`/conversations/${other}/messages`))).toBe(true);
});
it('invalid/foreign relationship and mismatched Agent scope fail closed without reading messages', async () => {
  const { transport, session, requests } = await setup(async (r) =>
    r.url.includes('/conversations/') ? json({ id: other, relationship_id: null }) : undefined,
  );
  const history = new HistoryController(transport, session);
  await history.open('relationship', 'demo-a');
  expect(history.snapshot().status).toBe('error');
  await history.open('agent', other, rel);
  expect(history.snapshot().items).toEqual([]);
  expect(requests.some((r) => r.url.includes('/messages'))).toBe(false);
});
it('malformed repeated cursor and oversized pages are rejected and retain no invented rows', async () => {
  const { transport, session } = await setup(async (r) =>
    r.url.includes('/messages')
      ? json({ items: [message(1), message(2)], next_cursor: null })
      : undefined,
  );
  const history = new HistoryController(transport, session, 1);
  await history.open('relationship', rel);
  expect(history.snapshot().status).toBe('error');
  expect(history.snapshot().items).toEqual([]);
});
it('collection has a finite bound and explicitly stops further More requests', async () => {
  const { transport, session } = await setup(async (r) =>
    r.url.includes('/messages')
      ? json({
          items: [message(Number(new URL(r.url).searchParams.get('cursor') ?? 1))],
          next_cursor: String(Number(new URL(r.url).searchParams.get('cursor') ?? 1) + 1),
        })
      : undefined,
  );
  const history = new HistoryController(transport, session, 1, 2);
  await history.open('relationship', rel);
  await history.load(true);
  await history.load(true);
  expect(history.snapshot().items).toHaveLength(2);
  expect(history.snapshot().bounded).toBe(true);
});
