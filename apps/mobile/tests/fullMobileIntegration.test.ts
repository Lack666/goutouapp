import { ApiTransport } from '../src/api/transport';
import { AgentChatController } from '../src/data/agentChatController';
import { HistoryController } from '../src/data/historyController';
import { ImportController } from '../src/data/importController';
import { MemoryController } from '../src/data/memoryController';
import { ResourceController } from '../src/data/resourceController';
import { DevelopmentSession } from '../src/session/developmentSession';
import { createVolatileTokenStorage } from '../src/session/storage';
import {
  control,
  record,
  preview,
  person,
  rel,
  jobId,
  other,
  json,
  token,
  time,
} from './memorySupport';

const sessions: DevelopmentSession[] = [];
async function connection() {
  const requests: string[] = [];
  let delayed = false;
  let finish: () => void = () => undefined;
  const wire: typeof fetch = async (input) => {
    const request = new Request(input);
    const path = new URL(request.url).pathname;
    requests.push(`${request.method} ${path}`);
    if (delayed)
      return new Promise((resolve) => {
        finish = () => resolve(json({ items: [], next_cursor: null }));
      });
    if (path === '/api/v1/memory/control') return json(control());
    if (path === '/api/v1/memories')
      return json({
        items: [record()],
        next_cursor: null,
        retention_policy_summary: record().retention_policy_summary,
        historical_notice: record().historical_notice,
      });
    if (path === '/api/v1/memory/undo/preview') return json(preview());
    if (path === `/api/v1/conversations/${jobId}`)
      return json({ id: jobId, relationship_id: rel, created_at: time, updated_at: time });
    if (path.endsWith('/messages')) return json({ items: [], next_cursor: null });
    return json({ items: [], next_cursor: null });
  };
  const session = new DevelopmentSession(createVolatileTokenStorage());
  sessions.push(session);
  const transport = new ApiTransport(
    'http://127.0.0.1:8000',
    session,
    wire,
    500,
    true,
    true,
    wire,
    500,
    true,
    500,
    true,
  );
  const value = {
    session,
    requests,
    resources: new ResourceController(transport, session, () => person),
    chat: new AgentChatController(transport, session, () => person),
    imports: new ImportController(transport, session),
    history: new HistoryController(transport, session),
    memory: new MemoryController(
      transport,
      session,
      () => person,
      () => Date.parse(time),
    ),
    delay: () => {
      delayed = true;
    },
    finish: () => {
      delayed = false;
      finish();
    },
  };
  await session.connect(token(), value.resources.probe);
  return value;
}
afterEach(async () => {
  await Promise.all(sessions.splice(0).map((session) => session.logout()));
});

it('one session clears resources, Chat scope, Import, History cursor and Memory confirmation together on owner switch', async () => {
  const c = await connection();
  await c.chat.open(jobId, rel);
  await c.history.open('agent', jobId, rel);
  await c.memory.open(person, rel);
  await c.memory.armUndo();
  expect(c.memory.snapshot().phase).toBe('awaiting_user_confirmation');
  expect(c.chat.snapshot().scope).toBe('ready');
  await c.session.connect(token(other), c.resources.probe);
  expect(c.chat.snapshot()).toMatchObject({
    conversationId: null,
    operationKey: null,
    messages: [],
  });
  expect(c.history.snapshot()).toMatchObject({ parentId: null, cursor: null, items: [] });
  expect(c.imports.snapshot().job).toBeNull();
  expect(c.memory.snapshot()).toMatchObject({
    control: null,
    undo: null,
    challenge: null,
    receipt: null,
    canRetry: false,
    items: [],
  });
  expect(c.resources.snapshot().selectedConversationId).toBeNull();
});

it('Demo switching invalidates every Connected controller without submitting business mutations', async () => {
  const c = await connection();
  await c.chat.open(jobId, rel);
  await c.memory.open();
  await c.session.demo();
  const before = c.requests.length;
  await c.chat.send('anonymous synthetic', 'rest');
  await c.memory.changeControl('grant');
  await c.memory.retry();
  expect(c.session.snapshot().mode).toBe('demo');
  expect(c.requests).toHaveLength(before);
  expect(c.memory.snapshot().items).toEqual([]);
  expect(c.chat.snapshot().messages).toEqual([]);
});

it('late resource response after logout cannot restore scope or inherited keys', async () => {
  const c = await connection();
  c.delay();
  const read = c.resources.load('persons');
  await Promise.resolve();
  await c.session.logout();
  c.finish();
  await read;
  expect(c.resources.snapshot().pages.persons.items).toEqual([]);
  expect(c.resources.snapshot().selectedRelationshipId).toBeNull();
  expect(c.memory.snapshot().canRetry).toBe(false);
});

it('process reconstruction restores only authoritative reads and cannot replay a lost Memory key', async () => {
  const c = await connection();
  await c.memory.open();
  await c.memory.armUndo();
  c.memory.pause();
  const count = c.requests.length;
  await c.memory.retry();
  expect(c.requests).toHaveLength(count);
  const restarted = await connection();
  await restarted.memory.open();
  await restarted.memory.retry();
  expect(restarted.requests.every((request) => request.startsWith('GET '))).toBe(true);
  expect(restarted.memory.snapshot()).toMatchObject({
    phase: 'idle',
    canRetry: false,
    receipt: null,
  });
});

it('background clears prepared confirmation and foreground performs only reads across all history and memory surfaces', async () => {
  const c = await connection();
  await c.chat.open(jobId, rel);
  await c.history.open('agent', jobId, rel);
  await c.memory.open();
  await c.memory.armUndo();
  c.chat.pause();
  c.history.pause();
  c.memory.pause();
  expect(c.history.snapshot().items).toEqual([]);
  expect(c.memory.snapshot()).toMatchObject({ undo: null, challenge: null, phase: 'idle' });
  await c.history.resume();
  await c.memory.resume();
  expect(c.requests.every((request) => request.startsWith('GET '))).toBe(true);
});
