import { randomUUID } from 'node:crypto';
import { test, expect } from '../connected/fixture';
import { connected, scope, save } from './support';
import { asUUID } from '../src/api/uuid';
import { MemoryController } from '../src/data/memoryController';
import { bind, selectedFixture } from '../import-connected/support';
async function reset(value: Awaited<ReturnType<typeof connected>>) {
  await value.memory.open();
  value.memory.chooseAllConsent(false);
  await value.memory.prepare('delete_all');
  await value.memory.execute();
  expect(value.memory.snapshot().phase).toBe('completed');
  await value.memory.changeControl('grant');
  await value.memory.changeControl('resume');
}
test('real JWT / PostgreSQL / LangGraph: consent, pause, expiry, guarded undo and data-domain separation', async ({
  backend,
}) => {
  const value = await connected(backend.baseURL, backend.a);
  try {
    const target = await scope(value);
    await value.memory.open();
    expect(value.memory.snapshot().control?.consentEnabled).toBe(false);
    expect(await save(value, target)).toBe('none');
    expect((await backend.memoryEvidence()).memories).toBe(0);
    await value.memory.changeControl('grant');
    expect(await save(value, target)).toBe('saved');
    await value.memory.open(target.person, target.relationship);
    expect(value.memory.snapshot().items).toHaveLength(1);
    expect(value.memory.snapshot().retention).toContain('37 days');
    const first = value.memory.snapshot().items[0]!.id;
    await value.memory.changeControl('pause');
    expect(await save(value, target, '二', 'sse')).toBe('skipped_paused');
    expect((await backend.memoryEvidence()).memories).toBe(1);
    expect((await backend.memoryEvidence()).recall_counts.at(-1)).toBe(0);
    await value.memory.changeControl('revoke');
    await value.memory.changeControl('resume');
    expect(value.memory.snapshot().control).toMatchObject({ consentEnabled: false, paused: true });
    await value.memory.changeControl('grant');
    expect(value.memory.snapshot().control?.paused).toBe(true);
    await value.memory.changeControl('resume');
    expect(await save(value, target, '二', 'sse')).toBe('saved');
    expect((await backend.memoryEvidence()).recall_counts.at(-1)).toBe(1);
    await backend.expire('memory', first);
    await value.memory.refresh();
    expect(value.memory.snapshot().items).toHaveLength(1);
    await value.memory.inspect(first);
    expect(value.memory.snapshot().detail?.state).toBe('expired');
    await value.chat.open(target.conversation, target.relationship);
    await value.chat.send('请根据之前的关系背景分析现状。', 'rest');
    expect((await backend.memoryEvidence()).recall_counts.at(-1)).toBe(1);
    await value.memory.armUndo();
    const second = value.memory.snapshot().undo!.memoryId;
    expect(second).not.toBe(first);
    await value.memory.execute();
    expect(value.memory.snapshot().receipt).toMatchObject({
      action: 'undo',
      undoneMemoryId: second,
      affectedCount: 1,
    });
    expect(value.memory.snapshot().items).toHaveLength(0);
    await value.imports.open(target.relationship);
    await value.imports.select(async () => selectedFixture(2, '8E domain'));
    value.imports.timezone('Asia/Shanghai');
    await value.imports.upload();
    await bind(value.imports, target.person);
    await value.imports.finalize();
    expect(value.imports.snapshot().job?.status).toBe('imported');
    expect(await save(value, target, '三')).toBe('saved');
    await value.memory.open(null, null);
    const before = await backend.memoryEvidence();
    value.memory.chooseAllConsent(false);
    await value.memory.prepare('delete_all');
    expect(value.memory.snapshot().challenge?.expectedCount).toBe(2);
    await value.memory.execute();
    expect(value.memory.snapshot().phase).toBe('completed');
    expect(value.memory.snapshot().control?.consentEnabled).toBe(true);
    const after = await backend.memoryEvidence();
    expect(after.memories).toBe(0);
    expect(after.agent_messages).toBe(before.agent_messages);
    expect(after.relationship_messages).toBe(before.relationship_messages);
    expect(after.relationship_messages).toBe(2);
  } finally {
    await value.session.logout();
  }
});
test('real committed response loss: controls re-inspect; undo/delete replay exact original payload, durable owner-only receipts', async ({
  backend,
}) => {
  let lose = '';
  const attempts: { path: string; body: string }[] = [];
  let knownReceipt = '';
  let originalKey = '';
  const wire: typeof fetch = async (input, init) => {
    const request = new Request(input, init);
    const path = new URL(request.url).pathname;
    const destructive = path.endsWith('/undo') || path.endsWith('/execute');
    if (destructive) attempts.push({ path, body: await request.clone().text() });
    const response = await fetch(request);
    if (response.ok && lose && path.endsWith(lose)) {
      lose = '';
      const body = await response.text();
      if (destructive) {
        const receipt = JSON.parse(body);
        knownReceipt = receipt.mutation_id;
        originalKey = receipt.operation_key;
      }
      throw new TypeError('Synthetic response lost after real commit');
    }
    return response;
  };
  const value = await connected(backend.baseURL, backend.a, wire);
  const foreign = await connected(backend.baseURL, backend.b);
  try {
    await reset(value);
    const target = await scope(value);
    lose = '/pause';
    await value.memory.changeControl('pause');
    expect(value.memory.snapshot().control?.paused).toBe(true);
    expect(value.memory.snapshot().feedback).toContain('权威');
    await value.memory.changeControl('resume');
    expect(await save(value, target)).toBe('saved');
    expect(await save(value, target, '二')).toBe('saved');
    await value.memory.open(target.person, target.relationship);
    await value.memory.armUndo();
    const removed = value.memory.snapshot().undo!.memoryId;
    const expected = value.memory.snapshot().undo!.operationId;
    lose = '/undo';
    await value.memory.execute();
    expect(value.memory.snapshot().phase).toBe('unknown_outcome');
    await value.memory.refresh();
    expect(value.memory.snapshot().items).toHaveLength(1);
    const older = value.memory.snapshot().undo!;
    expect(older.operationId).not.toBe(expected);
    await value.memory.retry();
    expect(value.memory.snapshot().receipt).toMatchObject({
      replayed: true,
      undoneMemoryId: removed,
    });
    expect(value.memory.snapshot().items[0]?.id).toBe(older.memoryId);
    const undoRequests = attempts.filter((value) => value.path.endsWith('/undo'));
    expect(undoRequests[0]).toEqual(undoRequests[1]);
    await expect(
      value.transport.client.POST('/api/v1/memory/undo', {
        body: { expected_operation_id: older.operationId, operation_key: originalKey },
      }),
    ).rejects.toMatchObject({ code: 'mutation_conflict' });
    const restarted = new MemoryController(value.transport, value.session, randomUUID);
    await restarted.inspectReceipt(knownReceipt);
    expect(restarted.snapshot().receipt?.id).toBe(knownReceipt);
    expect(restarted.snapshot().canRetry).toBe(false);
    await foreign.memory.inspectReceipt(knownReceipt);
    expect(foreign.memory.snapshot().receipt).toBeNull();
    expect(foreign.memory.snapshot().error).toBeTruthy();
    await foreign.memory.inspect(older.memoryId);
    expect(foreign.memory.snapshot().detail).toBeNull();
    await value.memory.prepare('delete_one', older.memoryId);
    lose = '/execute';
    await value.memory.execute();
    expect(value.memory.snapshot().phase).toBe('unknown_outcome');
    expect(value.memory.snapshot().receipt).toBeNull();
    expect(await save(value, target, '三')).toBe('saved');
    await value.memory.refresh();
    const newMemory = value.memory.snapshot().items[0]!.id;
    await value.memory.retry();
    expect(value.memory.snapshot().receipt).toMatchObject({
      replayed: true,
      affectedCount: 1,
      targetId: older.memoryId,
    });
    expect(value.memory.snapshot().items.map((item) => item.id)).toEqual([newMemory]);
    const deletes = attempts.filter((value) => value.path.endsWith('/execute')).slice(-2);
    expect(deletes[0]).toEqual(deletes[1]);
    await value.memory.inspectReceipt(knownReceipt);
    expect(value.memory.snapshot().receipt?.replayed).toBe(false);
    await value.session.logout();
    await value.session.connect(backend.b, value.resources.probe);
    await value.memory.retry();
    expect(value.memory.snapshot().receipt).toBeNull();
    expect(value.memory.snapshot().canRetry).toBe(false);
  } finally {
    await value.session.logout();
    await foreign.session.logout();
  }
});
test('real structured Person deletion, stale/expired challenge, explicit all consent choice, safe replay preserving new records', async ({
  backend,
}) => {
  const value = await connected(backend.baseURL, backend.a);
  try {
    await reset(value);
    const domainBaseline = await backend.memoryEvidence();
    const first = await scope(value, '8E Person P');
    const other = await scope(value, '8E Person Q');
    expect(await save(value, first)).toBe('saved');
    expect(await save(value, other, '二')).toBe('saved');
    await value.memory.open(other.person);
    const otherMemory = value.memory.snapshot().items[0]!.id;
    await value.memory.open(first.person);
    await value.memory.prepare('delete_person');
    expect(value.memory.snapshot().challenge?.expectedCount).toBe(1);
    expect(await save(value, first, '三')).toBe('saved');
    await value.memory.execute();
    expect(value.memory.snapshot().phase).toBe('stale_or_conflict');
    expect(value.memory.snapshot().error).toBe('操作目标已发生变化，请重新检查。');
    await value.memory.prepare('delete_person');
    await backend.expire('confirmation', value.memory.snapshot().challenge!.id);
    await value.memory.execute();
    expect(value.memory.snapshot().phase).toBe('expired');
    await value.memory.prepare('delete_person');
    expect(value.memory.snapshot().challenge?.expectedCount).toBe(2);
    await value.memory.execute();
    expect(value.memory.snapshot().receipt).toMatchObject({
      action: 'delete_person',
      affectedCount: 2,
      targetId: first.person,
    });
    await value.memory.open(null, null);
    expect(value.memory.snapshot().items.map((item) => item.id)).toEqual([otherMemory]);
    expect(
      (
        await value.transport.client.GET('/api/v1/persons/{person_id}', {
          params: { path: { person_id: asUUID(first.person) } },
        })
      ).data?.id,
    ).toBe(first.person);
    expect(
      (
        await value.transport.client.GET('/api/v1/relationships/{relationship_id}', {
          params: { path: { relationship_id: asUUID(first.relationship) } },
        })
      ).data?.id,
    ).toBe(first.relationship);
    value.memory.chooseAllConsent(false);
    await value.memory.prepare('delete_all');
    value.memory.chooseAllConsent(true);
    expect(value.memory.snapshot().challenge).toBeNull();
    await value.memory.execute();
    expect(value.memory.snapshot().items).toHaveLength(1);
    value.memory.chooseAllConsent(false);
    await value.memory.prepare('delete_all');
    await value.memory.execute();
    expect(value.memory.snapshot().control?.consentEnabled).toBe(true);
    expect(await save(value, other, '四')).toBe('saved');
    await value.memory.retry();
    expect(value.memory.snapshot().receipt?.replayed).toBe(true);
    expect(value.memory.snapshot().items).toHaveLength(1);
    value.memory.chooseAllConsent(true);
    await value.memory.prepare('delete_all');
    await value.memory.execute();
    expect(value.memory.snapshot().control).toMatchObject({ consentEnabled: false, paused: true });
    expect(value.memory.snapshot().items).toHaveLength(0);
    expect(await save(value, other, '五', 'sse')).toBe('none');
    const evidence = await backend.memoryEvidence();
    expect(evidence.memories).toBe(0);
    expect(evidence.recall_counts.at(-1)).toBe(0);
    expect(evidence.relationship_messages).toBe(domainBaseline.relationship_messages);
  } finally {
    await value.session.logout();
  }
});
