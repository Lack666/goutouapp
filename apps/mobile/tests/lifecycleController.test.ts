import { LifecycleController } from '../src/data/lifecycleController';
import { ApiTransport } from '../src/api/transport';
import { DevelopmentSession } from '../src/session/developmentSession';
import { createVolatileTokenStorage } from '../src/session/storage';
import { person, rel, other, token, json } from './memorySupport';

const sessions: DevelopmentSession[] = [];
const now = Date.parse('2026-10-11T00:00:00Z');
const target = { domain: 'person' as const, target_id: person };
const counts = {
  persons: 1,
  relationships: 1,
  conversations: 1,
  agent_runs: 1,
  messages: 2,
  chat_import_jobs: 1,
  relationship_messages: 4,
  chat_import_speakers: 2,
  chat_import_artifacts: 1,
  memory_records: 1,
};
const challenge = (t = target) => ({
  ...t,
  counts,
  confirmation_id: other,
  expires_at: '2026-10-11T00:05:00Z',
  memory_policy: 'delete_exact_structured_scope',
  scope_notice: 'Primary data only; immutable operation fences remain.',
});
const receipt = (t = target) => ({
  ...t,
  counts,
  confirmation_id: other,
  receipt_id: rel,
  performed_at: '2026-10-11T00:01:00Z',
  status: 'deleted',
  primary_store_only: true,
});
async function setup(override?: (r: Request) => Promise<Response | undefined>) {
  const session = new DevelopmentSession(createVolatileTokenStorage(), () => now);
  sessions.push(session);
  const requests: Request[] = [],
    bodies: unknown[] = [];
  const wire: typeof fetch = async (input) => {
    const r = new Request(input);
    requests.push(r);
    if (r.method === 'POST') bodies.push(await r.clone().json());
    const overridden = await override?.(r);
    if (overridden) return overridden;
    if (r.url.endsWith('/prepare')) return json(challenge());
    if (r.url.endsWith('/execute') || r.url.includes('/receipts/')) return json(receipt());
    return json({}, 404);
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
    refresh = jest.fn(async () => undefined);
  const uuid = jest.fn(() => rel);
  const controller = new LifecycleController(
    transport,
    session,
    uuid,
    invalidate,
    refresh,
    () => now,
  );
  await session.connect(token(), async () => undefined);
  controller.select('person', person);
  return { controller, session, requests, bodies, invalidate, refresh, uuid };
}
afterEach(async () => {
  for (const s of sessions.splice(0)) await s.logout();
});

it('formal prepare + explicit confirmation + receipt GET + authoritative 404 refresh', async () => {
  const c = await setup();
  await c.controller.confirm();
  expect(c.requests).toHaveLength(0);
  await c.controller.prepare();
  expect(c.controller.snapshot().phase).toBe('awaiting_confirmation');
  expect(c.invalidate).not.toHaveBeenCalled();
  await c.controller.confirm();
  expect(c.controller.snapshot()).toMatchObject({ phase: 'completed', refresh: 'verified' });
  expect(c.invalidate).toHaveBeenCalledTimes(1);
  expect(c.refresh).toHaveBeenCalledTimes(1);
  await c.controller.retry();
  expect(c.bodies[2]).toEqual(c.bodies[1]);
  expect(c.uuid).toHaveBeenCalledTimes(1);
});
it('cancel, expired challenge, background and restart never dispatch an execute', async () => {
  const c = await setup();
  await c.controller.prepare();
  c.controller.cancel();
  await c.controller.confirm();
  await c.controller.prepare();
  c.controller.leave();
  await c.controller.confirm();
  await c.controller.retry();
  expect(c.requests.filter((r) => r.url.endsWith('/execute'))).toHaveLength(0);
  expect(c.controller.snapshot().target).toBeNull();
});
it('unknown outcome retains original target and exact immutable key/body', async () => {
  let drop = true;
  const c = await setup(async (r) => {
    if (r.url.endsWith('/execute') && drop) {
      drop = false;
      throw new Error('private transport');
    }
    return undefined;
  });
  await c.controller.prepare();
  await c.controller.confirm();
  expect(c.controller.snapshot().phase).toBe('unknown_outcome');
  expect(c.controller.snapshot().error).not.toContain('private transport');
  c.controller.select('relationship', other);
  expect(c.controller.snapshot().target).toEqual(target);
  c.controller.leave();
  await c.controller.retry();
  expect(c.controller.snapshot().phase).toBe('completed');
  expect(c.bodies[2]).toEqual(c.bodies[1]);
});
it('unverified receipt GET remains unknown after leaving the screen', async () => {
  const c = await setup(async (r) =>
    r.url.includes('/receipts/') ? json({ ...receipt(), target_id: other }) : undefined,
  );
  await c.controller.prepare();
  await c.controller.confirm();
  c.controller.leave();
  expect(c.controller.snapshot().phase).toBe('unknown_outcome');
  expect(c.refresh).not.toHaveBeenCalled();
});
it('PostgreSQL JSONB key ordering does not change receipt identity', async () => {
  const c = await setup(async (r) =>
    r.url.includes('/receipts/')
      ? json({ ...receipt(), counts: Object.fromEntries(Object.entries(counts).reverse()) })
      : undefined,
  );
  await c.controller.prepare();
  await c.controller.confirm();
  expect(c.controller.snapshot()).toMatchObject({ phase: 'completed', refresh: 'verified' });
});
it.each(['confirmation_expired', 'target_changed', 'target_busy'])(
  'definitive %s allows explicit fresh preparation',
  async (code) => {
    let first = true;
    const c = await setup(async (r) => {
      if (r.url.endsWith('/execute') && first) {
        first = false;
        return json({ error: { code, message: 'private' } }, 409);
      }
      return undefined;
    });
    await c.controller.prepare();
    await c.controller.confirm();
    c.controller.refreshBusy();
    await c.controller.prepare();
    expect(c.controller.snapshot().phase).toBe('awaiting_confirmation');
    await c.controller.confirm();
    expect(c.controller.snapshot().phase).toBe('completed');
    expect(c.uuid).toHaveBeenCalledTimes(2);
  },
);
it.each([
  { ...challenge(), target_id: other },
  { ...challenge(), counts: { ...counts, persons: -1 } },
  { ...challenge(), counts: { ...counts, owner: 1 } },
  { ...challenge(), expires_at: '2026-10-10T00:00:00Z' },
  { ...challenge(), memory_policy: 'preserve' },
])('rejects malformed or stale official challenge before creating a key', async (payload) => {
  const c = await setup(async (r) => (r.url.endsWith('/prepare') ? json(payload) : undefined));
  await c.controller.prepare();
  await c.controller.confirm();
  expect(c.controller.snapshot().phase).toBe('failed');
  expect(c.uuid).not.toHaveBeenCalled();
  expect(c.invalidate).not.toHaveBeenCalled();
});
it('A late execute cannot publish a receipt or refresh after B connects', async () => {
  let resolve!: (r: Response) => void;
  const c = await setup(async (r) =>
    r.url.endsWith('/execute')
      ? new Promise<Response>((done) => {
          resolve = done;
        })
      : undefined,
  );
  await c.controller.prepare();
  const executing = c.controller.confirm();
  await new Promise((done) => setTimeout(done, 0));
  expect(c.invalidate).toHaveBeenCalledTimes(1);
  await c.session.logout();
  await c.session.connect(token(other), async () => undefined);
  resolve(json(receipt()));
  await executing;
  expect(c.controller.snapshot()).toMatchObject({ target: null, receipt: null, phase: 'idle' });
  expect(c.refresh).not.toHaveBeenCalled();
  await c.controller.retry();
  expect(c.requests.filter((r) => r.url.endsWith('/execute'))).toHaveLength(1);
});
