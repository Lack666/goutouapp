import { randomUUID } from 'node:crypto';
import { test, expect } from '../connected/fixture';
import { ApiTransport } from '../src/api/transport';
import { AgentChatController } from '../src/data/agentChatController';
import { DevelopmentSession } from '../src/session/developmentSession';
import { createVolatileTokenStorage } from '../src/session/storage';
import { ResourceController } from '../src/data/resourceController';
import { asUUID } from '../src/api/uuid';
const prompt = '有人正在伤害我'; // Synthetic, never print body or credentials.
test('real SSE answer committed but terminal frame lost: same-key REST recovers one persisted answer', async ({
  backend,
}) => {
  const session = new DevelopmentSession(createVolatileTokenStorage());
  let loss = true;
  const wire: typeof fetch = async (input, init) => {
    const request = new Request(input, init);
    const response = await fetch(request);
    if (loss && request.url.endsWith('/agent-runs/stream') && response.ok) {
      loss = false;
      const body = await response.text();
      const cutoff = body.indexOf('event: completed');
      expect(cutoff).toBeGreaterThan(0);
      return new Response(body.slice(0, cutoff), { headers: response.headers });
    }
    return response;
  };
  const transport = new ApiTransport(backend.baseURL, session, wire, 5000, true, true, wire);
  const resources = new ResourceController(transport, session, randomUUID);
  const chat = new AgentChatController(transport, session, randomUUID);
  try {
    await session.connect(backend.a, resources.probe);
    resources.reserveConversation(null);
    await resources.retryCreate('conversations');
    const id = resources.snapshot().selectedConversationId!;
    await chat.open(id);
    await chat.send(prompt);
    expect(chat.snapshot().phase).toBe('running_unknown');
    expect(chat.snapshot().messages.filter((m) => m.role === 'assistant')).toHaveLength(1);
    const runId = chat.snapshot().runId;
    const before = await backend.agentEvidence();
    await chat.retry('rest');
    await chat.loadHistory();
    expect(chat.snapshot().phase).toBe('completed');
    expect(chat.snapshot().runId).toBe(runId);
    expect(chat.snapshot().messages).toHaveLength(2);
    const after = await backend.agentEvidence();
    expect(after.calls).toBe(before.calls);
    expect(after.memories).toBe(before.memories);
    expect(after.runs.filter((r) => r.conversation === id)).toHaveLength(1);
    expect(after.messages.filter((m) => m.conversation === id)).toHaveLength(2);
  } finally {
    session.logout();
  }
});
test('real signed REST/SSE cross replay, lost response, PostgreSQL IDs, history and owner isolation', async ({
  backend,
}) => {
  const session = new DevelopmentSession(createVolatileTokenStorage());
  let drop = false;
  const bodies: string[] = [];
  const wire: typeof fetch = async (input, init) => {
    const request = new Request(input, init);
    if (request.url.endsWith('/agent-runs') && request.method === 'POST')
      bodies.push(await request.clone().text());
    const response = await fetch(request);
    if (drop && request.url.endsWith('/agent-runs') && response.ok) {
      drop = false;
      await response.text();
      throw new TypeError('Injected postcommit response loss');
    }
    return response;
  };
  const transport = new ApiTransport(backend.baseURL, session, wire, 5000, true, true, wire);
  const resources = new ResourceController(transport, session, randomUUID);
  const chat = new AgentChatController(transport, session, randomUUID, 1);
  try {
    await session.connect(backend.a, resources.probe);
    resources.reserveConversation(null);
    await resources.retryCreate('conversations');
    const id = resources.snapshot().selectedConversationId!;
    await chat.open(id);
    drop = true;
    await chat.send(prompt, 'rest');
    expect(chat.snapshot().phase).toBe('running_unknown');
    const key = chat.snapshot().operationKey;
    const before = await backend.agentEvidence();
    expect(before.runs.filter((r) => r.conversation === id)).toHaveLength(1);
    expect(before.messages.filter((m) => m.conversation === id)).toHaveLength(2);
    await chat.retry('sse');
    const runId = chat.snapshot().runId;
    expect(chat.snapshot().phase).toBe('completed');
    expect(chat.snapshot().operationKey).toBe(key);
    await chat.retry('rest');
    expect(bodies[0] === bodies[1]).toBe(true);
    expect(chat.snapshot().runId).toBe(runId);
    expect((await backend.agentEvidence()).calls).toBe(before.calls);
    expect((await backend.agentEvidence()).memories).toBe(before.memories);
    await chat.loadHistory();
    await chat.loadHistory(true);
    expect(chat.snapshot().messages).toHaveLength(2);
    expect(new Set(chat.snapshot().messages.map((m) => m.id)).size).toBe(2);
    await chat.send(prompt, 'sse');
    const sseRun = chat.snapshot().runId;
    const sseKey = chat.snapshot().operationKey;
    expect(chat.snapshot().phase).toBe('completed');
    await chat.retry('rest');
    expect(chat.snapshot().runId).toBe(sseRun);
    expect(chat.snapshot().operationKey).toBe(sseKey);
    const evidence = await backend.agentEvidence();
    const own = evidence.runs.filter((r) => r.conversation === id);
    expect(own).toHaveLength(2);
    expect(own.every((r) => r.status === 'completed')).toBe(true);
    expect(
      new Set(evidence.messages.filter((m) => m.conversation === id).map((m) => m.id)).size,
    ).toBe(4);
    const operation = randomUUID();
    const body = { message: prompt, operation_key: operation };
    const attempts = await Promise.all(
      Array.from({ length: 4 }, () =>
        transport.client
          .POST('/api/v1/conversations/{conversation_id}/agent-runs', {
            params: { path: { conversation_id: asUUID(id) } },
            body,
          })
          .then(
            () => 200,
            (e: { status: number }) => e.status,
          ),
      ),
    );
    expect(attempts.filter((s) => s === 200).length).toBeGreaterThanOrEqual(1);
    expect(attempts.every((s) => [200, 409].includes(s))).toBe(true);
    const concurrent = (await backend.agentEvidence()).runs.filter((r) => r.key === operation);
    expect(concurrent).toHaveLength(1);
    await expect(
      transport.client.POST('/api/v1/conversations/{conversation_id}/agent-runs', {
        params: { path: { conversation_id: asUUID(id) } },
        body: { ...body, message: 'changed' },
      }),
    ).rejects.toMatchObject({ kind: 'conflict' });
    chat.leave();
    await chat.open(id);
    while (chat.snapshot().cursor) await chat.loadHistory(true);
    expect(chat.snapshot().messages).toHaveLength(6);
    session.logout();
    expect(chat.snapshot().messages).toHaveLength(0);
    await session.connect(backend.b, resources.probe);
    await chat.open(id);
    expect(chat.snapshot().scope).toBe('error');
    expect(chat.snapshot().errorKind).toBe('not_found');
    expect(chat.snapshot().messages).toHaveLength(0);
    expect((await backend.agentEvidence()).runs.filter((r) => r.conversation === id)).toHaveLength(
      3,
    );
  } finally {
    session.logout();
  }
});
