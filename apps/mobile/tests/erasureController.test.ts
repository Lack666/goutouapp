import { ErasureController } from '../src/data/erasureController';
import { ApiTransport } from '../src/api/transport';
import { ApiError } from '../src/api/errors';
import {
  challengeView,
  receiptView,
  datasetView,
  type ErasureTarget,
} from '../src/api/erasureAdapter';
import { DevelopmentSession } from '../src/session/developmentSession';
import { createVolatileTokenStorage } from '../src/session/storage';
import { person, rel, other, jobId, token, json } from './memorySupport';

const sessions: DevelopmentSession[] = [];
const now = Date.parse('2026-10-11T00:00:00Z');
const target: ErasureTarget = { domain: 'dataset', target_id: jobId, relationship_id: rel };
const challenge = (t = target) => ({
  ...t,
  confirmation_id: other,
  message_count: 3,
  run_count: 0,
  expires_at: '2026-10-11T00:05:00Z',
  memory_affected: false as const,
  retained_metadata: 'Metadata only',
});
const receipt = (t = target) => ({
  ...t,
  confirmation_id: other,
  receipt_id: person,
  message_count: 3,
  run_count: 0,
  performed_at: '2026-10-11T00:01:00Z',
  memory_affected: false as const,
  status: 'deleted' as const,
});
const dataset = () => ({
  dataset_job_id: jobId,
  relationship_id: rel,
  source_format: 'wechat_markdown_v1',
  parser_version: '1',
  source_timezone: 'UTC',
  first_timestamp_utc: '2024-01-01T00:00:00Z',
  last_timestamp_utc: '2024-01-01T00:00:00Z',
  imported_message_count: 3,
  current_message_count: 3,
  ignored_message_count: 0,
  system_message_count: 0,
  imported_at: '2026-10-11T00:00:00Z',
  deleted_at: null,
  deletable: true,
});
type Handler = (request: Request) => Promise<Response | undefined>;
async function setup(handler?: Handler, clock = () => now) {
  const session = new DevelopmentSession(createVolatileTokenStorage(), () => now);
  sessions.push(session);
  const requests: Request[] = [],
    bodies: unknown[] = [];
  let selected = target,
    deleted = false;
  const wire: typeof fetch = async (input) => {
    const request = new Request(input);
    requests.push(request);
    if (request.method === 'POST') bodies.push(await request.clone().json());
    const override = await handler?.(request);
    if (override) return override;
    const path = new URL(request.url).pathname;
    if (path.endsWith('/prepare')) {
      selected = await request.json();
      return json(challenge(selected));
    }
    if (path.endsWith('/execute')) {
      deleted = true;
      return json(receipt(selected));
    }
    if (path.includes('/receipts/')) return json(receipt(selected));
    if (path.endsWith('/datasets'))
      return json({
        items: [
          {
            ...dataset(),
            ...(deleted
              ? { current_message_count: 0, deleted_at: '2026-10-11T00:01:00Z', deletable: false }
              : {}),
          },
        ],
        next_cursor: null,
      });
    if (path.includes('/conversations/'))
      return deleted ? json({}, 404) : json({ id: jobId, relationship_id: rel });
    return json({ items: [], next_cursor: null });
  };
  const transport = new ApiTransport(
    'http://127.0.0.1:8000',
    session,
    wire,
    300,
    true,
    true,
    wire,
    300,
    true,
    300,
    true,
    true,
  );
  const invalidate = jest.fn(),
    refreshed = jest.fn(async () => undefined),
    uuid = jest.fn(() => person);
  const controller = new ErasureController(transport, session, uuid, invalidate, refreshed, clock);
  await session.connect(token(), async () => undefined);
  controller.select(target);
  return { controller, session, requests, bodies, invalidate, refreshed, transport, uuid };
}
afterEach(async () => {
  for (const session of sessions.splice(0)) await session.logout();
});
it('owner A late Execute cannot publish a receipt or refresh after owner B connects', async () => {
  let resolve!: (value: Response) => void;
  const c = await setup(async (r) =>
    r.url.endsWith('/execute')
      ? new Promise<Response>((done) => {
          resolve = done;
        })
      : undefined,
  );
  await c.controller.prepare();
  const executing = c.controller.confirm();
  await new Promise((r) => setTimeout(r, 0));
  await c.session.logout();
  await c.session.connect(token(other), async () => undefined);
  resolve(json(receipt()));
  await executing;
  expect(c.controller.snapshot()).toMatchObject({
    phase: 'idle',
    target: null,
    receipt: null,
    challenge: null,
  });
  expect(c.refreshed).not.toHaveBeenCalled();
  await c.controller.retry();
  expect(c.requests.filter((r) => r.url.endsWith('/execute'))).toHaveLength(1);
});
it('requires formal Prepare and explicit confirmation, then inspects receipt and refreshes authority', async () => {
  const c = await setup();
  await c.controller.confirm();
  expect(c.requests).toHaveLength(0);
  await c.controller.prepare();
  expect(c.controller.snapshot().phase).toBe('awaiting_confirmation');
  expect(c.requests).toHaveLength(1);
  await c.controller.confirm();
  expect(c.controller.snapshot()).toMatchObject({
    phase: 'completed',
    refresh: 'verified',
    receipt: { receipt_id: person },
  });
  expect(c.requests.map((r) => new URL(r.url).pathname)).toContain(
    `/api/v1/erasures/receipts/${person}`,
  );
  expect(c.controller.snapshot().datasets[0]?.deletable).toBe(false);
  expect(c.invalidate).toHaveBeenCalledWith(target);
  expect(c.refreshed).toHaveBeenCalledWith(target);
});
it('cancel never emits Execute; target/domain changes discard old confirmations', async () => {
  const c = await setup();
  await c.controller.prepare();
  c.controller.cancel();
  await c.controller.confirm();
  expect(c.requests.filter((r) => r.url.endsWith('/execute'))).toHaveLength(0);
  await c.controller.prepare();
  c.controller.select({ domain: 'conversation', target_id: jobId, relationship_id: rel });
  expect(c.controller.snapshot().challenge).toBeNull();
  await c.controller.confirm();
  expect(c.requests.filter((r) => r.url.endsWith('/execute'))).toHaveLength(0);
});
it('local expiry refuses execution and server expiry is a distinct state', async () => {
  let time = now;
  const c = await setup(undefined, () => time);
  await c.controller.prepare();
  time += 301_000;
  await c.controller.confirm();
  expect(c.controller.snapshot().phase).toBe('expired');
  expect(c.requests.filter((r) => r.url.endsWith('/execute'))).toHaveLength(0);
  const d = await setup(async (r) =>
    r.url.endsWith('/execute') ? json({ error: { code: 'confirmation_expired' } }, 409) : undefined,
  );
  await d.controller.prepare();
  await d.controller.confirm();
  expect(d.controller.snapshot().phase).toBe('expired');
});
it.each(['target_busy', 'target_changed', 'confirmation_mismatch', 'confirmation_consumed'])(
  'maps %s without new-key automatic retry',
  async (code) => {
    const c = await setup(async (r) =>
      r.url.endsWith('/execute')
        ? json({ error: { code, message: 'private-sentinel' } }, 409)
        : undefined,
    );
    await c.controller.prepare();
    await c.controller.confirm();
    expect(c.controller.snapshot().phase).toBe(code === 'target_busy' ? 'target_busy' : 'stale');
    expect(c.controller.snapshot().error).not.toContain('private-sentinel');
    await c.controller.retry();
    expect(c.uuid).toHaveBeenCalledTimes(1);
    expect(c.requests.filter((r) => r.url.endsWith('/execute'))).toHaveLength(1);
  },
);
it('committed response loss retains exact immutable body/key; list disappearance never proves success', async () => {
  let drop = true;
  const c = await setup(async (r) => {
    if (r.url.endsWith('/execute') && drop) {
      drop = false;
      throw new ApiError('offline');
    }
  });
  await c.controller.prepare();
  await c.controller.confirm();
  expect(c.controller.snapshot().phase).toBe('unknown_outcome');
  await c.controller.prepare();
  expect(c.uuid).toHaveBeenCalledTimes(1);
  await c.controller.discover(rel);
  expect(c.controller.snapshot().phase).toBe('unknown_outcome');
  await c.controller.retry();
  expect(c.controller.snapshot().phase).toBe('completed');
  const sent = c.bodies.filter((b) => (b as Record<string, unknown>).operation_key);
  expect(sent).toHaveLength(2);
  expect(sent[1]).toEqual(sent[0]);
  expect(c.uuid).toHaveBeenCalledTimes(1);
});
it('known receipt can be inspected after lost inspection, without another Execute', async () => {
  let loss = true;
  const c = await setup(async (r) => {
    if (r.url.includes('/receipts/') && loss) {
      loss = false;
      throw new ApiError('offline');
    }
  });
  await c.controller.prepare();
  await c.controller.confirm();
  expect(c.controller.snapshot().phase).toBe('unknown_outcome');
  expect(c.controller.snapshot().receipt?.receipt_id).toBe(person);
  await c.controller.inspect();
  expect(c.controller.snapshot().phase).toBe('completed');
  expect(c.requests.filter((r) => r.url.endsWith('/execute'))).toHaveLength(1);
});
it('Back retains unresolved original attempt in-session, restart does not recover or execute it', async () => {
  const c = await setup(async (r) => {
    if (r.url.endsWith('/execute')) throw new ApiError('offline');
  });
  c.controller.select({ domain: 'conversation', target_id: jobId, relationship_id: rel });
  await c.controller.prepare();
  await c.controller.confirm();
  c.controller.leave();
  await c.controller.openConversation(jobId, rel);
  expect(c.controller.snapshot().phase).toBe('unknown_outcome');
  const fresh = new ErasureController(
    c.transport,
    c.session,
    () => other,
    () => undefined,
    async () => undefined,
    () => now,
  );
  await fresh.openConversation(jobId, rel);
  expect(fresh.snapshot().phase).toBe('idle');
  expect(c.requests.filter((r) => r.url.endsWith('/execute'))).toHaveLength(1);
});
it('recovery requires the exact domain and Relationship even when UUIDs coincide', async () => {
  const c = await setup(async (r) => {
    if (r.url.endsWith('/execute')) throw new TypeError('lost');
    return undefined;
  });
  await c.controller.prepare();
  await c.controller.confirm();
  expect(c.controller.recoverable(target)).toBe(true);
  expect(c.controller.recoverable({ ...target, domain: 'conversation' })).toBe(false);
  expect(c.controller.recoverable({ ...target, relationship_id: other })).toBe(false);
  c.controller.select({ ...target, domain: 'conversation' });
  expect(c.controller.snapshot()).toMatchObject({ phase: 'idle', challenge: null, receipt: null });
  await c.controller.retry();
  expect(c.requests.filter((r) => r.url.endsWith('/execute'))).toHaveLength(1);
});
it.each(['logout', 'demo', 'connected'] as const)(
  '%s clears all confirmation/key/receipt state and rejects late results',
  async (action) => {
    let release: () => void = () => undefined;
    const c = await setup(async (r) =>
      r.url.endsWith('/prepare')
        ? new Promise((resolve) => {
            release = () => resolve(json(challenge()));
          })
        : undefined,
    );
    const pending = c.controller.prepare();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await c.session[action]();
    release();
    await pending;
    expect(c.controller.snapshot().target).toBeNull();
    expect(c.controller.snapshot().challenge).toBeNull();
    await c.controller.confirm();
    expect(c.requests.filter((r) => r.url.endsWith('/execute'))).toHaveLength(0);
  },
);
it('Demo never sends discovery, Prepare or Execute', async () => {
  const c = await setup();
  await c.session.demo();
  await c.controller.discover(rel);
  c.controller.select(target);
  await c.controller.prepare();
  await c.controller.confirm();
  expect(c.requests).toHaveLength(0);
});
it('rejects malformed/cross-scope confirmations and receipts without declaring deletion', () => {
  expect(() => challengeView({ ...challenge(), target_id: person }, target)).toThrow(ApiError);
  expect(() =>
    receiptView(
      { ...receipt(), memory_affected: true } as unknown as ReturnType<typeof receipt>,
      target,
      other,
    ),
  ).toThrow(ApiError);
  expect(() => datasetView({ ...dataset(), current_message_count: -1 }, rel)).toThrow(ApiError);
  expect(() => datasetView(dataset(), person)).toThrow(ApiError);
});
it('receipt completion remains truthful when authoritative refresh fails', async () => {
  const c = await setup();
  c.refreshed.mockRejectedValueOnce(new Error('Synthetic refresh failure'));
  await c.controller.prepare();
  await c.controller.confirm();
  expect(c.controller.snapshot()).toMatchObject({
    phase: 'completed',
    refresh: 'failed',
    receipt: { receipt_id: person },
  });
});
it('server token expiry clears mutation state without allowing a new-key bypass', async () => {
  const c = await setup(async (r) => (r.url.endsWith('/execute') ? json({}, 401) : undefined));
  await c.controller.prepare();
  await c.controller.confirm();
  expect(c.session.snapshot().status).not.toBe('authenticated');
  expect(c.controller.snapshot().target).toBeNull();
});
