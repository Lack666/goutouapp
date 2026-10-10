import { runInThisContext } from 'node:vm';
import { ApiTransport, validateBaseURL } from '../src/api/transport';
import { ApiError } from '../src/api/errors';
import { DevelopmentSession } from '../src/session/developmentSession';
import { createVolatileTokenStorage } from '../src/session/storage';
import { ResourceController } from '../src/data/resourceController';
import { personView, relationshipView, conversationView } from '../src/api/resourceAdapter';
import { asUUID, asUUIDv4 } from '../src/api/uuid';
import { operationInventory } from '../src/api/generated/client';
import { createPlatformTokenStorage } from '../src/session/tokenStorage.native';
import * as SecureStore from 'expo-secure-store';

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
  WHEN_UNLOCKED_THIS_DEVICE_ONLY: 'device-only',
}));
// Use Node's actual fetch primitives for injectable transport tests, without RN's Jest stubs.
Object.assign(globalThis, {
  Request: runInThisContext('Request'),
  Response: runInThisContext('Response'),
  Headers: runInThisContext('Headers'),
  AbortController: runInThisContext('AbortController'),
});
const a = asUUID('11111111-1111-4111-8111-111111111111');
const b = asUUID('22222222-2222-4222-8222-222222222222');
const now = Date.now();
const token = (sub = a, exp = now + 900_000) =>
  `${Buffer.from('{"alg":"HS256"}').toString('base64url')}.${Buffer.from(JSON.stringify({ sub, exp: exp / 1000 })).toString('base64url')}.synthetic`;
const person = (id = a) => ({
  id,
  display_name: 'Synthetic',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
});
const relationship = {
  id: a,
  person_id: b,
  relationship_type: 'unknown',
  status: 'unknown',
  created_at: '',
  updated_at: '',
};
const conversation = { id: a, relationship_id: null, created_at: '', updated_at: '' };
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
const sessions: DevelopmentSession[] = [];
function setup(
  fetcher: typeof fetch = jest.fn(async () => json({ items: [], next_cursor: null })),
  timeout = 1000,
) {
  const storage = createVolatileTokenStorage();
  const session = new DevelopmentSession(storage);
  sessions.push(session);
  const transport = new ApiTransport('http://localhost:8000', session, fetcher, timeout, true);
  const uuid = jest.fn(() => a);
  const resources = new ResourceController(transport, session, uuid, 2);
  return { session, storage, transport, resources, uuid, fetcher };
}
afterEach(() => {
  for (const session of sessions.splice(0)) session.logout();
  jest.useRealTimers();
  jest.clearAllMocks();
});

describe('generated client and safe transport', () => {
  it('defines exactly the authoritative 36 operations with Bearer protected resources', () => {
    expect(operationInventory).toHaveLength(36);
    expect(
      operationInventory.filter((op) => op.path === '/api/v1/persons').every((op) => op.bearer),
    ).toBe(true);
  });
  it('maps nullable and absent profile data without inventing facts', () => {
    expect(conversationView(conversation).relationshipId).toBeNull();
    expect(personView(person()).source).toBe('server');
    expect(relationshipView(relationship).known).toEqual([]);
    expect(relationshipView(relationship).person.nickname).toBeNull();
  });
  it.each(['demo-a', 'demo-b', 'nickname', ''])(
    'blocks synthetic resource ID %s before HTTP',
    async (id) => {
      const x = setup();
      await x.session.connect(token(), x.resources.probe);
      const count = (x.fetcher as jest.Mock).mock.calls.length;
      await x.resources.select('persons', id);
      expect((x.fetcher as jest.Mock).mock.calls.length).toBe(count);
      expect(x.resources.snapshot().details.persons.value).toBeNull();
    },
  );
  it('requires UUID v4 for creation', () => {
    expect(() => asUUIDv4('11111111-1111-1111-8111-111111111111')).toThrow();
    expect(() => validateBaseURL('http://example.com', true)).toThrow(ApiError);
    expect(validateBaseURL('http://10.0.2.2:8000', true)).toBe('http://10.0.2.2:8000');
  });
  it('injects Bearer only from current session, never unauthenticated', async () => {
    const seen: boolean[] = [];
    const x = setup(async (input) => {
      seen.push(new Request(input).headers.has('Authorization'));
      return json({ items: [], next_cursor: null });
    });
    await x.transport.client.GET('/api/v1/persons');
    await x.session.connect(token(), x.resources.probe);
    expect(seen).toEqual([false, true]);
  });
  it.each([401, 404, 409, 422, 503])(
    'normalizes HTTP %i without raw body or credential',
    async (status) => {
      const x = setup(async () => json({ error: { message: 'private SQL traceback' } }, status));
      const logging = jest.spyOn(console, 'log').mockImplementation(() => undefined);
      await expect(x.transport.client.GET('/api/v1/persons')).rejects.toMatchObject({ status });
      expect(logging).not.toHaveBeenCalled();
      logging.mockRestore();
    },
  );
  it('cancels an in-flight request', async () => {
    const x = setup(
      (input) =>
        new Promise((_, reject) => {
          new Request(input).signal.addEventListener('abort', () => reject(new Error('private')));
        }),
    );
    const pending = x.transport.client.GET('/api/v1/persons');
    x.transport.cancelAll();
    await expect(pending).rejects.toMatchObject({ kind: 'cancelled' });
  });
  it('times out an in-flight request', async () => {
    const x = setup(() => new Promise(() => undefined), 5);
    await expect(x.transport.client.GET('/api/v1/persons')).rejects.toMatchObject({
      kind: 'timeout',
    });
  });
  it('normalizes offline failure', async () => {
    const x = setup(async () => {
      throw new Error('private token and network details');
    });
    await expect(x.transport.client.GET('/api/v1/persons')).rejects.toMatchObject({
      kind: 'offline',
    });
  });
  it.each([
    'http://localhost:8000',
    'https://user:pass@localhost:8000',
    'https://localhost:8000?token=private',
  ])('rejects insecure deployment configuration %s', (value) => {
    expect(() => validateBaseURL(value, false)).toThrow(ApiError);
  });
  it('blocks Agent/SSE/import/memory operations at transport', async () => {
    const x = setup();
    await expect(x.transport.client.POST('/api/v1/memory/pause')).rejects.toMatchObject({
      kind: 'validation',
    });
    expect(x.fetcher).not.toHaveBeenCalled();
  });
});

describe('development sessions and credential lifecycle', () => {
  it('starts Demo/no token without business requests', () => {
    const x = setup();
    expect(x.session.snapshot()).toMatchObject({ mode: 'demo', status: 'no_token' });
    expect(x.session.credential()).toBeNull();
    expect(x.fetcher).not.toHaveBeenCalled();
  });
  it('accepts user input only after the server probe and hides it from snapshots', async () => {
    const x = setup();
    await x.session.connect(token(), x.resources.probe);
    expect(x.session.snapshot().status).toBe('authenticated');
    expect(JSON.stringify(x.session.snapshot()).includes('synthetic')).toBe(false);
  });
  it('handles empty input', async () => {
    const x = setup();
    await x.session.connect('', x.resources.probe);
    expect(x.session.snapshot().status).toBe('no_token');
    expect(x.fetcher).not.toHaveBeenCalled();
  });
  it('rejects expired input without pretending to authenticate', async () => {
    const x = setup();
    await x.session.connect(token(a, now - 1), x.resources.probe);
    expect(x.session.snapshot().status).toBe('expired');
    expect(x.fetcher).not.toHaveBeenCalled();
  });
  it('rejects malformed input', async () => {
    const x = setup();
    await x.session.connect('malformed', x.resources.probe);
    expect(x.session.snapshot().status).toBe('invalid');
  });
  it('defers signature validity to server and clears on 401', async () => {
    const x = setup(async () => json({}, 401));
    await x.session.connect(token(), x.resources.probe);
    expect(x.session.snapshot().status).toBe('invalid');
    expect(x.session.credential()).toBeNull();
    expect(await x.storage.read()).toBeNull();
  });
  it('distinguishes network unavailable from invalid credential', async () => {
    const x = setup(async () => {
      throw new Error();
    });
    await x.session.connect(token(), x.resources.probe);
    expect(x.session.snapshot().status).toBe('network_unavailable');
  });
  it('writes and clears volatile storage; a new Web session has no credential', async () => {
    const x = setup();
    await x.session.connect(token(), x.resources.probe);
    expect((await x.storage.read()) !== null).toBe(true);
    expect(await createVolatileTokenStorage().read()).toBeNull();
    x.session.logout();
    await Promise.resolve();
    await Promise.resolve();
    expect(await x.storage.read()).toBeNull();
  });
  it('native storage delegates read/write/delete with device-only keychain', async () => {
    const store = createPlatformTokenStorage();
    await store.read();
    await store.write(token());
    await store.clear();
    expect(SecureStore.getItemAsync).toHaveBeenCalledWith('goutou.development.session.v1');
    expect((SecureStore.setItemAsync as jest.Mock).mock.calls[0]?.[2]).toEqual({
      keychainAccessible: 'device-only',
    });
    expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('goutou.development.session.v1');
  });
  it('restores native credential with a fresh server probe', async () => {
    const x = setup();
    await x.storage.write(token());
    await x.session.restore(x.resources.probe);
    expect(x.session.snapshot().status).toBe('authenticated');
    expect(x.fetcher).toHaveBeenCalledTimes(1);
  });
  it('expires while idle and clears every resource on foreground expiry', async () => {
    let instant = now;
    const storage = createVolatileTokenStorage();
    const session = new DevelopmentSession(storage, () => instant);
    sessions.push(session);
    await session.connect(token(a, now + 100), async () => undefined);
    instant += 101;
    session.resume();
    expect(session.snapshot().status).toBe('expired');
    expect(session.credential()).toBeNull();
  });
  it('clears all domain lists, cursors, selections and pending attempts on logout', async () => {
    const x = setup(async (input) => {
      const path = new URL(new Request(input).url).pathname;
      return path.includes('relationships')
        ? json({ items: [relationship], next_cursor: 'opaque-r' })
        : path.includes('conversations')
          ? json({ items: [conversation], next_cursor: 'opaque-c' })
          : json({ items: [person()], next_cursor: 'opaque-p' });
    });
    await x.session.connect(token(), x.resources.probe);
    for (const kind of ['persons', 'relationships', 'conversations'] as const)
      await x.resources.load(kind);
    x.resources.reservePerson('pending');
    x.session.logout();
    const view = x.resources.snapshot();
    expect(Object.values(view.pages).every((p) => !p.items.length && !p.cursor)).toBe(true);
    expect(view.selectedConversationId).toBeNull();
    expect(view.selectedRelationshipId).toBeNull();
    await x.resources.retryCreate('persons');
    expect(view.creates.persons.status).toBe('idle');
  });
  it('mode switch cancels scope and preserves Demo isolation', async () => {
    const x = setup();
    await x.session.connect(token(), x.resources.probe);
    const clearing = x.session.demo();
    expect(x.session.snapshot()).toMatchObject({ mode: 'demo', status: 'clearing' });
    expect(x.session.credential()).toBeNull();
    await clearing;
    expect(x.session.snapshot()).toMatchObject({ mode: 'demo', status: 'no_token' });
  });
  it('ignores delayed A response after B identity switch', async () => {
    let finish: (response: Response) => void = () => undefined;
    const x = setup();
    await x.session.connect(token(), x.resources.probe);
    const original = x.transport.client.GET;
    const delayed = jest.spyOn(x.transport.client, 'GET').mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = (response) =>
            resolve({ data: { items: [person()], next_cursor: 'a-cursor' }, response });
        }),
    );
    const load = x.resources.load('persons');
    x.session.logout();
    delayed.mockRestore();
    await x.session.connect(token(b), x.resources.probe);
    await x.resources.load('persons');
    finish(json({}));
    await load;
    expect(x.resources.snapshot().pages.persons.items).toEqual([]);
    expect(x.resources.snapshot().pages.persons.cursor).toBeNull();
    expect(x.session.snapshot().status).toBe('authenticated');
    expect(x.transport.client.GET).toBe(original);
  });
});

describe('owned resources, opaque pages and stable create attempts', () => {
  it.each(['persons', 'relationships', 'conversations'] as const)(
    'retry response loss uses identical UUID/payload for %s',
    async (kind) => {
      let first = true;
      const bodies: string[] = [];
      const x = setup(async (input) => {
        const request = new Request(input);
        if (request.method === 'POST') {
          bodies.push(await request.text());
          if (first) {
            first = false;
            throw new Error('lost response');
          }
          return json(
            kind === 'persons' ? person() : kind === 'relationships' ? relationship : conversation,
            201,
          );
        }
        const detail = new URL(request.url).pathname.split('/').length > 4;
        return detail
          ? json(
              kind === 'persons'
                ? person()
                : kind === 'relationships'
                  ? relationship
                  : conversation,
            )
          : json({ items: [], next_cursor: null });
      });
      await x.session.connect(token(), x.resources.probe);
      if (kind === 'persons') x.resources.reservePerson('first');
      else if (kind === 'relationships') x.resources.reserveRelationship(b, 'unknown', 'unknown');
      else x.resources.reserveConversation(null);
      await x.resources.retryCreate(kind);
      expect(x.resources.snapshot().creates[kind].status).toBe('failed');
      await x.resources.retryCreate(kind);
      expect(bodies[0] === bodies[1]).toBe(true);
      expect(x.uuid).toHaveBeenCalledTimes(1);
      expect(x.resources.snapshot().creates[kind].status).toBe('saved');
    },
  );
  it('never inserts synthetic success after unavailable create', async () => {
    const x = setup(async (input) =>
      new Request(input).method === 'POST' ? json({}, 503) : json({ items: [], next_cursor: null }),
    );
    await x.session.connect(token(), x.resources.probe);
    x.resources.reservePerson('Synthetic');
    await x.resources.retryCreate('persons');
    expect(x.resources.snapshot().creates.persons.status).toBe('failed');
    expect(x.resources.snapshot().pages.persons.items).toEqual([]);
  });
  it('changed input explicitly reserves a new creation UUID', async () => {
    const x = setup();
    await x.session.connect(token(), x.resources.probe);
    x.uuid.mockReturnValueOnce(a).mockReturnValueOnce(b);
    x.resources.reservePerson('first');
    x.resources.reservePerson('changed');
    expect(x.uuid).toHaveBeenCalledTimes(2);
  });
  it('guards duplicate More and deduplicates IDs without parsing cursor or timestamps', async () => {
    const queries: (string | null)[] = [];
    let list = 0;
    const x = setup(async (input) => {
      const url = new URL(new Request(input).url);
      queries.push(url.searchParams.get('cursor'));
      if (url.searchParams.get('limit') === '1') return json({ items: [], next_cursor: null });
      list++;
      return json({
        items: list === 1 ? [person(a)] : [person(a), person(b)],
        next_cursor: list === 1 ? 'opaque:do-not-parse' : null,
      });
    });
    await x.session.connect(token(), x.resources.probe);
    await x.resources.load('persons');
    await Promise.all([x.resources.load('persons', true), x.resources.load('persons', true)]);
    expect(x.resources.snapshot().pages.persons.items.map((p) => p.id)).toEqual([a, b]);
    expect(queries).toEqual([null, null, 'opaque:do-not-parse']);
  });
  it('foreign/missing detail has empty state and safe recovery', async () => {
    const x = setup(async (input) =>
      new URL(new Request(input).url).pathname.endsWith(a)
        ? json({}, 404)
        : json({ items: [], next_cursor: null }),
    );
    await x.session.connect(token(), x.resources.probe);
    await x.resources.select('relationships', a);
    expect(x.resources.snapshot().details.relationships.status).toBe('error');
    expect(x.resources.snapshot().selectedRelationshipId).toBeNull();
  });
  it('rapid detail switching cannot apply the previous scope', async () => {
    let finish: () => void = () => undefined;
    const x = setup(async (input) => {
      const path = new URL(new Request(input).url).pathname;
      if (path.endsWith(a))
        return new Promise((resolve) => {
          finish = () => resolve(json(person(a)));
        });
      if (path.endsWith(b)) return json(person(b));
      return json({ items: [], next_cursor: null });
    });
    await x.session.connect(token(), x.resources.probe);
    const old = x.resources.select('persons', a);
    await x.resources.select('persons', b);
    finish();
    await old;
    expect(x.resources.snapshot().details.persons.value?.id).toBe(b);
  });
  it('logout while create in-flight prevents delayed persisted result from entering UI', async () => {
    let finish: () => void = () => undefined;
    const x = setup(async (input) =>
      new Request(input).method === 'POST'
        ? new Promise((resolve) => {
            finish = () => resolve(json(person(), 201));
          })
        : json({ items: [], next_cursor: null }),
    );
    await x.session.connect(token(), x.resources.probe);
    x.resources.reservePerson('Synthetic');
    const old = x.resources.retryCreate('persons');
    x.session.logout();
    finish();
    await old;
    expect(x.resources.snapshot().creates.persons.status).toBe('idle');
    expect(x.resources.snapshot().pages.persons.items).toEqual([]);
  });
});
