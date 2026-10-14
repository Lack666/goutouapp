import { runInThisContext } from 'node:vm';
import { AgentChatController } from '../src/data/agentChatController';
import { DevelopmentSession } from '../src/session/developmentSession';
import { createVolatileTokenStorage } from '../src/session/storage';
import { ApiTransport } from '../src/api/transport';
import { asUUID } from '../src/api/uuid';
Object.assign(
  globalThis,
  Object.fromEntries(
    [
      'TextEncoder',
      'TextDecoder',
      'Request',
      'Response',
      'Headers',
      'ReadableStream',
      'AbortController',
    ].map((key) => [key, runInThisContext(key)]),
  ),
);
const conv = asUUID('11111111-1111-4111-8111-111111111111');
const run = asUUID('22222222-2222-4222-8222-222222222222');
const assistant = asUUID('33333333-3333-4333-8333-333333333333');
const user = asUUID('44444444-4444-4444-8444-444444444444');
const other = asUUID('55555555-5555-4555-8555-555555555555');
const key = asUUID('66666666-6666-4666-8666-666666666666');
const token = (sub = user) =>
  `e30.${Buffer.from(JSON.stringify({ sub, exp: Date.now() / 1000 + 900 })).toString('base64url')}.synthetic`;
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const event = (event: string, data: unknown, id = run) =>
  `event: ${event}\ndata: ${JSON.stringify({ schema_version: '1', event, run_id: id, data })}\n\n`;
const final = event('final_response', {
  assistant_message_id: assistant,
  answer: '服务器合成回答',
});
const completed = event('completed', {
  status: 'completed',
  assistant_message_id: assistant,
  memory_status: 'none',
});
const success =
  event('run_started', {}) + event('status', { status: 'checking_safety' }) + final + completed;
const stream = (body: string) =>
  new Response(body, { headers: { 'Content-Type': 'text/event-stream' } });
const response = {
  run_id: run,
  conversation_id: conv,
  status: 'completed',
  assistant_message: { id: assistant, role: 'assistant', content: '服务器合成回答' },
  memory_status: 'none',
  warnings: ['Public warning'],
};
const message = (id: typeof user, role: 'user' | 'assistant', content: string) => ({
  id,
  conversation_id: conv,
  role,
  content,
  created_at: '2026-10-09T00:00:00Z',
});
const sessions: DevelopmentSession[] = [];
it('expiry during an established stream cancels consumption and clears the current session', async () => {
  let cancelled = false;
  const { chat, session } = await setup(
    async () =>
      new Response(
        new ReadableStream({
          start(c) {
            c.enqueue(new TextEncoder().encode(event('run_started', {})));
          },
          cancel() {
            cancelled = true;
          },
        }),
        { headers: { 'Content-Type': 'text/event-stream' } },
      ),
  );
  const short = `e30.${Buffer.from(JSON.stringify({ sub: user, exp: Date.now() / 1000 + 0.25 })).toString('base64url')}.synthetic`;
  await session.connect(short, async () => undefined);
  await chat.open(conv);
  await chat.send('问题');
  expect(session.snapshot().status).toBe('expired');
  expect(cancelled).toBe(true);
  expect(chat.snapshot().messages).toHaveLength(0);
  expect(chat.snapshot().conversationId).toBeNull();
});
it('retains server microsecond ordering before UUID tie-breaking', async () => {
  const { chat } = await setup(undefined, () => ({
    items: [
      { ...message(user, 'user', 'first'), created_at: '2026-10-09T00:00:00.000001Z' },
      { ...message(assistant, 'assistant', 'second'), created_at: '2026-10-09T00:00:00.000002Z' },
    ],
    next_cursor: null,
  }));
  expect(chat.snapshot().messages.map((m) => m.id)).toEqual([user, assistant]);
});
it('invalid foreign/tool History fails closed and refresh recovers', async () => {
  let wrong = true;
  const { chat } = await setup(undefined, () => ({
    items: [
      wrong
        ? { ...message(user, 'user', 'synthetic'), role: 'tool', conversation_id: other }
        : message(user, 'user', 'synthetic'),
    ],
    next_cursor: null,
  }));
  expect(chat.snapshot().history).toBe('error');
  expect(chat.snapshot().messages).toHaveLength(0);
  wrong = false;
  await chat.loadHistory();
  expect(chat.snapshot().messages).toHaveLength(1);
  expect(chat.snapshot().history).toBe('ready');
});
it('HTTP running_unknown takes precedence over failure category and mismatched recovery run fails closed', async () => {
  let count = 0;
  const { chat } = await setup(async () =>
    count++ === 0
      ? stream(event('run_started', {}))
      : json(
          { error: { code: 'agent_failure', run_id: other, recovery_status: 'running_unknown' } },
          502,
        ),
  );
  await chat.send('问题');
  await chat.retry('rest');
  expect(chat.snapshot()).toMatchObject({
    phase: 'running_unknown',
    errorKind: 'protocol',
    runId: run,
  });
  const second = await setup(async () =>
    json(
      { error: { code: 'agent_failure', run_id: run, recovery_status: 'running_unknown' } },
      502,
    ),
  );
  await second.chat.send('问题');
  expect(second.chat.snapshot().phase).toBe('running_unknown');
});
it('malformed committed IDs remain an unknown outcome rather than permission to rerun', async () => {
  const { chat } = await setup(async () => json({ ...response, run_id: 'demo-A' }));
  await chat.send('问题', 'rest');
  expect(chat.snapshot()).toMatchObject({ phase: 'running_unknown', errorKind: 'protocol' });
});
it('expired session before sending clears scope and forbids network work', async () => {
  const { chat, session, requests } = await setup();
  const expired = `e30.${Buffer.from(JSON.stringify({ sub: user, exp: Date.now() / 1000 - 1 })).toString('base64url')}.synthetic`;
  await session.connect(expired, async () => undefined);
  await chat.send('问题');
  expect(session.snapshot().status).toBe('expired');
  expect(requests.filter((r) => r.method === 'POST')).toHaveLength(0);
});
async function setup(
  agent: (request: Request) => Promise<Response> = async () => stream(success),
  history: () => unknown = () => ({ items: [], next_cursor: null }),
  timeout = 1000,
) {
  const session = new DevelopmentSession(createVolatileTokenStorage());
  sessions.push(session);
  const requests: Request[] = [];
  const fetcher = jest.fn(async (input: RequestInfo | URL) => {
    const request = input as Request;
    requests.push(request.clone());
    if (request.url.includes('agent-runs')) return agent(request);
    if (request.url.endsWith('/messages?limit=2') || request.url.includes('/messages?'))
      return json(history());
    return json({ id: conv, relationship_id: null, created_at: '', updated_at: '' });
  }) as jest.MockedFunction<typeof fetch>;
  const transport = new ApiTransport(
    'http://localhost:8000',
    session,
    fetcher,
    1000,
    true,
    true,
    fetcher,
    timeout,
  );
  const uuid = jest.fn(() => key);
  const chat = new AgentChatController(transport, session, uuid, 2);
  await session.connect(token(), async () => undefined);
  await chat.open(conv);
  return { chat, session, requests, fetcher, uuid, transport };
}
afterEach(() => {
  for (const session of sessions.splice(0)) session.logout();
});
it('erasure invalidation clears pending history and ignores a late Agent response', async () => {
  let resolve!: (value: Response) => void;
  const { chat, requests } = await setup(
    () =>
      new Promise<Response>((r) => {
        resolve = r;
      }),
  );
  const sending = chat.send('合成问题', 'rest');
  await new Promise((r) => setTimeout(r, 0));
  chat.invalidateConversation(conv);
  resolve(json(response));
  await sending;
  expect(chat.snapshot().conversationId).toBeNull();
  expect(chat.snapshot().messages).toHaveLength(0);
  const count = requests.length;
  await chat.retry('rest');
  expect(requests).toHaveLength(count);
});
it('erasure of another conversation preserves current history', async () => {
  const { chat } = await setup(undefined, () => ({
    items: [message(user, 'user', '合成')],
    next_cursor: null,
  }));
  chat.invalidateConversation(other);
  expect(chat.snapshot().conversationId).toBe(conv);
  expect(chat.snapshot().messages).toHaveLength(1);
});
it('erasure ignores a late SSE response and a late authoritative History page', async () => {
  let resolve!: (value: Response) => void;
  const x = await setup(
    () =>
      new Promise<Response>((done) => {
        resolve = done;
      }),
  );
  const sending = x.chat.send('合成问题');
  await new Promise((r) => setTimeout(r, 0));
  x.chat.invalidateConversation(conv);
  resolve(stream(success));
  await sending;
  expect(x.chat.snapshot().messages).toHaveLength(0);
  expect(x.chat.snapshot().conversationId).toBeNull();
  await x.chat.open(conv);
  x.fetcher.mockImplementationOnce(
    () =>
      new Promise<Response>((done) => {
        resolve = done;
      }),
  );
  const reading = x.chat.loadHistory();
  await new Promise((r) => setTimeout(r, 0));
  x.chat.invalidateConversation(conv);
  resolve(json({ items: [message(user, 'user', '已删除合成内容')], next_cursor: 'old-cursor' }));
  await reading;
  expect(x.chat.snapshot().messages).toHaveLength(0);
  expect(x.chat.snapshot().conversationId).toBeNull();
});
it('REST uses generated body, owned scope, Bearer, public result and warnings', async () => {
  const { chat, requests } = await setup(async () => json(response));
  await chat.send(' 问题 ', 'rest');
  const request = requests.find((r) => r.method === 'POST')!;
  expect(request.headers.get('Authorization')).toMatch(/^Bearer /);
  expect(await request.json()).toEqual({
    message: '问题',
    operation_key: key,
    expected_relationship_id: null,
  });
  expect(chat.snapshot()).toMatchObject({
    phase: 'completed',
    runId: run,
    operationKey: key,
    memoryStatus: 'none',
    warnings: ['Public warning'],
  });
  expect(chat.snapshot().messages).toHaveLength(1);
  expect(chat.snapshot().messages[0]).toMatchObject({ id: assistant, source: 'server' });
});
it('SSE maps status/final/completed separately with no optimistic duplicate bubbles', async () => {
  const { chat } = await setup();
  const views: string[] = [];
  chat.subscribe(() => views.push(`${chat.snapshot().phase}:${chat.snapshot().progress}`));
  await chat.send('问题');
  expect(views).toContain('running:checking_safety');
  expect(views).toContain('committed:checking_safety');
  expect(chat.snapshot().phase).toBe('completed');
  expect(chat.snapshot().messages.map((m) => m.text)).toEqual(['服务器合成回答']);
});
it.each(['', '  \n', '中'.repeat(2001), '\u0000', '\ud800'])(
  'blocks invalid bounded input %#',
  async (text) => {
    const { chat, requests } = await setup();
    await chat.send(text);
    expect(requests.filter((r) => r.method === 'POST')).toHaveLength(0);
    expect(chat.snapshot().errorKind).toBe('validation');
  },
);
it.each([
  ['pending_confirmation', { status: 'pending_confirmation' }],
  ['memory_status', { status: 'failed' }],
])('maps %s without a Memory mutation', async (name, data) => {
  const { chat, requests } = await setup(async () =>
    stream(
      final +
        event(name, data) +
        event('completed', {
          status: 'completed',
          assistant_message_id: assistant,
          memory_status: name === 'pending_confirmation' ? 'pending_confirmation' : 'failed',
        }),
    ),
  );
  await chat.send('问题');
  expect(chat.snapshot().memoryStatus).toBe(data.status);
  expect(requests.filter((r) => r.method === 'POST')).toHaveLength(1);
});
it.each(['failed', 'running_unknown'])(
  'maps server failed recovery %s without fake reply',
  async (recovery) => {
    const { chat } = await setup(async () =>
      stream(
        event('run_started', {}) +
          event('failed', { code: 'agent_failure', recovery_status: recovery }),
      ),
    );
    await chat.send('问题');
    expect(chat.snapshot().phase).toBe(recovery);
    expect(chat.snapshot().messages).toHaveLength(0);
  },
);
it('reuses original body/key after lost result even if draft changes; cross REST/SSE replay dedupes', async () => {
  let count = 0;
  const { chat, requests, uuid } = await setup(async () => {
    if (count++ === 0) throw new TypeError('private native failure');
    return json(response);
  });
  await chat.send('original');
  expect(chat.snapshot().phase).toBe('running_unknown');
  await chat.send('edited');
  expect(uuid).toHaveBeenCalledTimes(1);
  await chat.retry('rest');
  const posts = requests.filter((r) => r.method === 'POST');
  expect(await posts[0]!.json()).toEqual(await posts[1]!.json());
  expect(chat.snapshot().messages).toHaveLength(1);
  expect(chat.snapshot().phase).toBe('completed');
});
it('timeout completes even when transport ignores abort, retains unknown and same key', async () => {
  const { chat } = await setup(async () => new Promise(() => undefined), undefined, 5);
  await chat.send('问题');
  expect(chat.snapshot()).toMatchObject({
    phase: 'running_unknown',
    errorKind: 'timeout',
    operationKey: key,
  });
});
it.each([
  ['operation_in_progress', 'active_run', 'running_unknown'],
  ['conversation_busy', 'active_run', 'running_unknown'],
  ['operation_unresolved', 'operation_unresolved', 'running_unknown'],
  ['idempotency_conflict', 'conflict', 'failed'],
  ['operation_failed', 'operation_failed', 'failed'],
  ['invalid_scope', 'invalid_scope', 'failed'],
])('handles safe public error %s', async (code, kind, phase) => {
  const { chat } = await setup(async () =>
    json({ error: { code, message: 'SQL private', run_id: run } }, 409),
  );
  await chat.send('问题');
  expect(chat.snapshot()).toMatchObject({ phase, errorKind: kind, runId: run });
  expect(chat.snapshot().error).not.toContain('SQL');
});
it.each([401, 404, 422, 503])('handles HTTP %i and no fabricated answer', async (status) => {
  const { chat, session } = await setup(async () =>
    json({ error: { code: status === 503 ? 'constructor' : 'generic' } }, status),
  );
  await chat.send('问题');
  expect(chat.snapshot().messages).toHaveLength(0);
  if (status === 401) expect(session.snapshot().status).toBe('invalid');
  if (status === 503) expect(chat.snapshot().errorKind).toBe('unavailable');
});
it.each([
  event('run_started', {}) + event('status', { status: 'analyzing' }, other),
  event('status', { status: 'analyzing' }),
  completed,
  final +
    event('completed', { status: 'completed', assistant_message_id: other, memory_status: 'none' }),
])('fails closed on run/order/assistant mismatch %#', async (wire) => {
  const { chat } = await setup(async () => stream(wire));
  await chat.send('问题');
  expect(chat.snapshot().phase).toBe('running_unknown');
  expect(chat.snapshot().errorKind).toBe('protocol');
});
it('final commit without completed keeps confirmed answer and outcome unknown; history dedupes by id', async () => {
  const { chat } = await setup(
    async () => stream(final),
    () => ({
      items: [message(user, 'user', '问题'), message(assistant, 'assistant', '服务器合成回答')],
      next_cursor: null,
    }),
  );
  await chat.send('问题');
  expect(chat.snapshot().phase).toBe('running_unknown');
  await chat.loadHistory();
  expect(chat.snapshot().messages).toHaveLength(2);
});
it('pages equal timestamps by ID, cursor continuation, identical text stays separate, refresh recovers', async () => {
  let page = 0;
  const { chat, requests } = await setup(undefined, () =>
    page++ === 0
      ? {
          items: [message(assistant, 'assistant', 'same'), message(user, 'user', 'same')],
          next_cursor: 'opaque',
        }
      : {
          items: [message(assistant, 'assistant', 'same'), message(other, 'assistant', 'same')],
          next_cursor: null,
        },
  );
  await chat.loadHistory(true);
  expect(chat.snapshot().messages.map((m) => m.id)).toEqual([assistant, user, other]);
  expect(requests.some((r) => r.url.includes('cursor=opaque'))).toBe(true);
  await chat.loadHistory();
  expect(chat.snapshot().messages).toHaveLength(2);
});
it('scope mismatch and Demo id prevent sending', async () => {
  const { chat, requests } = await setup();
  await chat.open(conv, other);
  expect(chat.snapshot().errorKind).toBe('invalid_scope');
  await chat.send('问题');
  await chat.open('demo-A');
  expect(chat.snapshot().scope).toBe('error');
  expect(requests.filter((r) => r.method === 'POST')).toHaveLength(0);
});
it('Demo session never sends authenticated Agent requests', async () => {
  const { chat, session, requests } = await setup();
  session.demo();
  await chat.open(conv);
  await chat.send('问题');
  expect(requests.filter((r) => r.method === 'POST')).toHaveLength(0);
});
it.each(['leave', 'pause', 'logout', 'switch'])(
  'isolates stale stream on %s and cancels reader',
  async (action) => {
    let push: ReadableStreamDefaultController<Uint8Array> | undefined;
    let cancelled = false;
    const { chat, session } = await setup(
      async () =>
        new Response(
          new ReadableStream({
            start(c) {
              push = c;
              c.enqueue(new TextEncoder().encode(event('run_started', {})));
            },
            cancel() {
              cancelled = true;
            },
          }),
          { headers: { 'Content-Type': 'text/event-stream' } },
        ),
    );
    const pending = chat.send('问题');
    for (let n = 0; n < 20 && chat.snapshot().phase !== 'running'; n++)
      await new Promise((r) => setTimeout(r, 1));
    if (action === 'logout') session.logout();
    else if (action === 'switch') await session.connect(token(other), async () => undefined);
    else if (action === 'leave') chat.leave();
    else chat.pause();
    await pending;
    expect(cancelled).toBe(true);
    expect(chat.snapshot().messages).toHaveLength(0);
    expect(() => push?.enqueue(new TextEncoder().encode(final))).toThrow();
    if (action === 'leave') {
      await chat.open(conv);
      expect(chat.snapshot().operationKey).toBe(key);
      expect(chat.snapshot().phase).toBe('running_unknown');
    }
  },
);
it('guards rapid duplicate sends/retries while active', async () => {
  const { chat, requests } = await setup(async () => new Promise(() => undefined), undefined, 10);
  const pending = chat.send('问题');
  await chat.send('second');
  await chat.retry('rest');
  await pending;
  expect(requests.filter((r) => r.method === 'POST')).toHaveLength(1);
});
