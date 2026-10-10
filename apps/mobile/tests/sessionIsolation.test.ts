import { runInThisContext } from 'node:vm';
import { DevelopmentSession } from '../src/session/developmentSession';
import { createVolatileTokenStorage, type TokenStorage } from '../src/session/storage';
import { ApiTransport } from '../src/api/transport';
import { ResourceController } from '../src/data/resourceController';
Object.assign(globalThis, {
  Request: runInThisContext('Request'),
  Response: runInThisContext('Response'),
  Headers: runInThisContext('Headers'),
  AbortController: runInThisContext('AbortController'),
});
const id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const credential = () =>
  `${Buffer.from('{"alg":"HS256"}').toString('base64url')}.${Buffer.from(JSON.stringify({ sub: id, exp: Date.now() / 1000 + 900 })).toString('base64url')}.synthetic`;
const ok = () =>
  new Response('{"items":[],"next_cursor":null}', {
    headers: { 'Content-Type': 'application/json' },
  });

it('logout cancels credentials immediately and acknowledges durable removal only after storage clears', async () => {
  let value: string | null = null;
  let delayed = false;
  let finish: () => void = () => undefined;
  const storage: TokenStorage = {
    read: async () => value,
    write: async (token) => {
      value = token;
    },
    clear: async () => {
      if (delayed) await new Promise<void>((resolve) => (finish = resolve));
      value = null;
    },
  };
  const session = new DevelopmentSession(storage);
  await session.connect(credential(), async () => undefined);
  const epoch = session.epoch();
  delayed = true;
  const logout = session.logout();
  expect(session.snapshot()).toMatchObject({ status: 'clearing', epoch: epoch + 1 });
  expect(session.credential()).toBeNull();
  for (let step = 0; step < 8; step++) await Promise.resolve();
  expect(value).not.toBeNull();
  expect(session.snapshot().status).toBe('clearing');
  finish();
  await logout;
  expect(value).toBeNull();
  expect(session.snapshot().status).toBe('no_token');
  const restored = new DevelopmentSession(storage);
  const probe = jest.fn(async () => undefined);
  await restored.restore(probe);
  expect(probe).not.toHaveBeenCalled();
  expect(restored.credential()).toBeNull();
});

it('failed credential removal never reports logout storage as cleared', async () => {
  let rejectClear = false;
  const session = new DevelopmentSession({
    read: async () => null,
    write: async () => undefined,
    clear: async () => {
      if (rejectClear) throw new Error('private native failure');
    },
  });
  await session.connect(credential(), async () => undefined);
  rejectClear = true;
  await session.logout();
  expect(session.snapshot().status).toBe('storage_error');
  expect(session.credential()).toBeNull();
});

it('delayed old 401 cannot invalidate the new verified session', async () => {
  const session = new DevelopmentSession(createVolatileTokenStorage());
  let finish: () => void = () => undefined;
  let delay = false;
  const fetcher: typeof fetch = async () =>
    delay
      ? new Promise((resolve) => {
          finish = () => resolve(new Response('', { status: 401 }));
        })
      : ok();
  const transport = new ApiTransport('http://localhost:8000', session, fetcher, 1000, true);
  const resources = new ResourceController(transport, session, () => id);
  try {
    await session.connect(credential(), resources.probe);
    delay = true;
    const old = transport.client.GET('/api/v1/persons').catch(() => undefined);
    session.logout();
    delay = false;
    await session.connect(credential(), resources.probe);
    finish();
    await old;
    expect(session.snapshot().status).toBe('authenticated');
  } finally {
    session.logout();
  }
});
it('logout wins over a delayed storage write and startup read', async () => {
  let value: string | null = null;
  let finish: () => void = () => undefined;
  const store: TokenStorage = {
    read: async () => value,
    write: async (token) => {
      await new Promise<void>((resolve) => {
        finish = resolve;
      });
      value = token;
    },
    clear: async () => {
      value = null;
    },
  };
  const session = new DevelopmentSession(store);
  const connect = session.connect(credential(), async () => undefined);
  for (let step = 0; step < 8; step++) await Promise.resolve();
  session.logout();
  finish();
  await connect;
  for (let step = 0; step < 8; step++) await Promise.resolve();
  expect(value === null).toBe(true);
  expect(session.snapshot().status).toBe('no_token');
});
it('storage write failure is explicit and never authenticates', async () => {
  const session = new DevelopmentSession({
    read: async () => null,
    clear: async () => undefined,
    write: async () => {
      throw new Error('private native storage details');
    },
  });
  await session.connect(credential(), async () => undefined);
  expect(session.snapshot().status).toBe('storage_error');
  expect(session.credential()).toBeNull();
});
it('native restore read failure is explicit and safely cleared', async () => {
  const clear = jest.fn(async () => undefined);
  const session = new DevelopmentSession({
    read: async () => {
      throw new Error('private');
    },
    write: async () => undefined,
    clear,
  });
  await session.restore(async () => undefined);
  await Promise.resolve();
  expect(session.snapshot().status).toBe('storage_error');
  expect(clear).toHaveBeenCalled();
});
it('duplicate create/retry clicks issue only one active POST', async () => {
  const session = new DevelopmentSession(createVolatileTokenStorage());
  let finish: () => void = () => undefined;
  let posts = 0;
  const transport = new ApiTransport(
    'http://localhost:8000',
    session,
    async (input) =>
      new Request(input).method === 'POST'
        ? new Promise((resolve) => {
            posts++;
            finish = () =>
              resolve(
                new Response(
                  JSON.stringify({ id, display_name: 'Synthetic', created_at: '', updated_at: '' }),
                  { status: 201 },
                ),
              );
          })
        : ok(),
    1000,
    true,
  );
  const resources = new ResourceController(transport, session, () => id);
  try {
    await session.connect(credential(), resources.probe);
    resources.reservePerson('Synthetic');
    const first = resources.retryCreate('persons');
    await resources.retryCreate('persons');
    expect(resources.reservePerson('Changed')).toBe(false);
    expect(posts).toBe(1);
    finish();
    await first;
    expect(resources.snapshot().creates.persons.status).toBe('saved');
  } finally {
    session.logout();
  }
});
