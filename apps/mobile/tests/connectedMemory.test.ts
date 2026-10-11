import {
  memoryControlView,
  memoryRecordView,
  memoryChallengeView,
  memoryReceiptView,
  memoryUndoView,
} from '../src/api/memoryAdapter';
import { memoryHTTPError } from '../src/api/memoryErrors';
import { ApiTransport } from '../src/api/transport';
import { ApiError } from '../src/api/errors';
import { MemoryController, MEMORY_RESTART_NOTICE } from '../src/data/memoryController';
import {
  setup,
  sessions,
  json,
  person,
  rel,
  other,
  jobId,
  control,
  record,
  preview,
  challenge,
  time,
  token,
} from './memorySupport';
afterEach(async () => {
  for (const session of sessions.splice(0)) await session.logout();
});
it('reads server controls, public records, retention and global latest preview through generated JWT client', async () => {
  const { controller, requests, session } = await setup();
  await controller.open(person, rel);
  expect(controller.snapshot().items[0]?.summary).toBe(record().content);
  expect(controller.snapshot().retention).toContain('37 days');
  expect(controller.snapshot().undo?.operationId).toBe(other);
  expect(
    requests.every(
      (request) => request.headers.get('Authorization') === `Bearer ${session.credential()}`,
    ),
  ).toBe(true);
  expect(new URL(requests[1]!.url).searchParams.get('person_id')).toBe(person);
  expect(new URL(requests[1]!.url).searchParams.has('include_expired')).toBe(false);
});
it('maps only documented public fields, excluding raw evidence, fingerprints and operation keys', () => {
  const value = memoryRecordView({
    ...record(),
    evidence: 'private',
    snapshot_hash: 'private',
  } as ReturnType<typeof record>);
  expect(value).not.toHaveProperty('evidence');
  expect(value).not.toHaveProperty('snapshot_hash');
  expect(value).not.toHaveProperty('operation_key');
  expect(value.provenance).toBe(record().provenance_summary);
});
it.each(['state', 'created_at', 'id'])('rejects malformed public record %s', (key) => {
  expect(() => memoryRecordView({ ...record(), [key]: 'invalid' })).toThrow(ApiError);
});
it('keeps unavailable Undo empty and does not invent expiry', () => {
  expect(memoryUndoView({ available: false })).toBeNull();
  expect(memoryUndoView(preview())).not.toHaveProperty('expiresAt');
  expect(() => memoryUndoView({ available: true })).toThrow(ApiError);
});
it('rejects malformed control booleans and confirmation counts', () => {
  expect(() =>
    memoryControlView({ ...control(), paused: 'true' } as unknown as ReturnType<typeof control>),
  ).toThrow(ApiError);
  expect(() => memoryChallengeView({ ...challenge(), expected_count: -1 })).toThrow(ApiError);
});
it('sanitizes allowlisted conflicts and never exposes raw messages', () => {
  expect(
    memoryHTTPError(409, JSON.stringify({ error: { code: 'undo_unavailable' } })).message,
  ).toBe('操作目标已发生变化，请重新检查。');
  expect(
    memoryHTTPError(
      409,
      JSON.stringify({ error: { code: 'stale_undo', message: 'private token' } }),
    ).message,
  ).toBe('操作目标已发生变化，请重新检查。');
  expect(memoryHTTPError(503, '{private token').message).not.toContain('private');
});
it('transport refuses memory by default and rejects non-contract methods', async () => {
  const { session } = await setup();
  const wire = jest.fn();
  const transport = new ApiTransport('http://127.0.0.1:8000', session, wire, 500, true);
  await expect(transport.client.GET('/api/v1/memory/control')).rejects.toThrow(ApiError);
  expect(wire).not.toHaveBeenCalled();
});
it('known-ID detail displays expired server state without adding it to active list', async () => {
  const { controller } = await setup(async (request) =>
    new URL(request.url).pathname === `/api/v1/memories/${jobId}`
      ? json({ ...record(), state: 'expired', expires_at: time })
      : undefined,
  );
  await controller.open();
  await controller.inspect(jobId);
  expect(controller.snapshot().detail?.state).toBe('expired');
  expect(controller.snapshot().items).toHaveLength(1);
});
it('foreign scope response cannot enter detail or list', async () => {
  const { controller } = await setup();
  await controller.open(other, null);
  expect(controller.snapshot().status).toBe('error');
  expect(controller.snapshot().items).toEqual([]);
  await controller.inspect(jobId);
  expect(controller.snapshot().detail).toBeNull();
});
it('scope switch clears detail, pending challenge and cursor without a destructive request', async () => {
  const { controller, requests } = await setup();
  await controller.open();
  await controller.inspect(jobId);
  await controller.prepare('delete_one', jobId);
  expect(controller.snapshot().phase).toBe('awaiting_user_confirmation');
  await controller.open(person, null);
  expect(controller.snapshot().detail).toBeNull();
  expect(controller.snapshot().challenge).toBeNull();
  expect(requests.some((request) => request.url.endsWith('/execute'))).toBe(false);
});
it('revoke retains data and pauses; grant preserves pause; resume without consent never grants', async () => {
  const { controller } = await setup();
  await controller.open();
  await controller.changeControl('revoke');
  expect(controller.snapshot().control).toMatchObject({ consentEnabled: false, paused: true });
  await controller.changeControl('resume');
  expect(controller.snapshot().control?.consentEnabled).toBe(false);
  await controller.changeControl('grant');
  expect(controller.snapshot().control).toMatchObject({ consentEnabled: true, paused: true });
  await controller.changeControl('resume');
  expect(controller.snapshot().control?.writeEnabled).toBe(true);
});
it('lost control response is recovered by authoritative GET rather than optimistic rollback', async () => {
  let committed = false;
  const { controller } = await setup(async (request) => {
    if (request.url.endsWith('/pause')) {
      committed = true;
      throw new TypeError('lost response');
    }
    if (committed && request.url.endsWith('/control')) return json(control(true, true));
  });
  await controller.open();
  await controller.changeControl('pause');
  expect(controller.snapshot().control?.paused).toBe(true);
  expect(controller.snapshot().feedback).toContain('权威');
});
it('failed control and failed reinspection leave no stale confirmed toggle', async () => {
  let lost = false;
  const { controller } = await setup(async (request) => {
    if (request.url.endsWith('/pause')) lost = true;
    if (lost) throw new TypeError('offline');
  });
  await controller.open();
  await controller.changeControl('pause');
  expect(controller.snapshot().control).toBeNull();
  expect(controller.snapshot().status).toBe('error');
});
it('Undo preview is non-destructive and execute binds exact latest ID', async () => {
  const { controller, requests } = await setup();
  await controller.open();
  await controller.armUndo();
  expect(requests.filter((request) => request.method === 'POST')).toHaveLength(0);
  await controller.execute();
  expect(controller.snapshot().phase).toBe('completed');
  const request = requests.find((request) => request.url.endsWith('/undo'))!;
  expect(await request.json()).toEqual({
    expected_operation_id: other,
    operation_key: `memory-${person}`,
  });
  expect(controller.snapshot().receipt?.undoneMemoryId).toBe(jobId);
  expect(controller.snapshot().receipt).not.toHaveProperty('operation_key');
});
it('scoped Undo refuses latest from another Person without substituting older memory', async () => {
  const { controller, requests } = await setup(async (request) =>
    request.url.endsWith('/memories?limit=50&person_id=' + other)
      ? json({
          items: [],
          next_cursor: null,
          retention_policy_summary: '37',
          historical_notice: 'past',
        })
      : undefined,
  );
  await controller.open(other, null);
  await controller.armUndo();
  await controller.execute();
  expect(controller.snapshot().phase).toBe('stale_or_conflict');
  expect(requests.some((request) => request.url.endsWith('/undo'))).toBe(false);
});
it('stale Undo never automatically retries or falls back after server latest changes', async () => {
  const { controller, requests } = await setup(async (request) =>
    request.url.endsWith('/undo') ? json({ error: { code: 'stale_undo' } }, 409) : undefined,
  );
  await controller.open();
  await controller.armUndo();
  await controller.execute();
  await controller.retry();
  expect(controller.snapshot().phase).toBe('stale_or_conflict');
  expect(controller.snapshot().error).toBe('操作目标已发生变化，请重新检查。');
  expect(requests.filter((request) => request.url.endsWith('/undo'))).toHaveLength(1);
});
it.each(['undo', 'delete_one'] as const)(
  'unknown %s outcome retains immutable payload across authority refresh',
  async (action) => {
    let loss = true;
    const { controller, requests } = await setup(async (request) => {
      if (loss && (request.url.endsWith('/undo') || request.url.endsWith('/execute'))) {
        loss = false;
        throw new TypeError('lost after commit');
      }
    });
    await controller.open();
    if (action === 'undo') await controller.armUndo();
    else await controller.prepare('delete_one', jobId);
    await controller.execute();
    expect(controller.snapshot().phase).toBe('unknown_outcome');
    expect(controller.snapshot().receipt).toBeNull();
    await controller.refresh();
    expect(controller.snapshot().phase).toBe('unknown_outcome');
    await controller.retry();
    const mutations = requests.filter(
      (request) => request.url.endsWith('/undo') || request.url.endsWith('/execute'),
    );
    expect(mutations).toHaveLength(2);
    expect(await mutations[0]!.json()).toEqual(await mutations[1]!.json());
    expect(mutations[0]!.url).toBe(mutations[1]!.url);
    expect(controller.snapshot().phase).toBe('completed');
  },
);
it('delete-all requires explicit choice; changing it invalidates confirmation', async () => {
  const { controller, requests } = await setup();
  await controller.open();
  await controller.prepare('delete_all');
  expect(controller.snapshot().phase).toBe('failed');
  expect(requests.some((request) => request.url.endsWith('/all/prepare'))).toBe(false);
  controller.chooseAllConsent(false);
  await controller.prepare('delete_all');
  expect(controller.snapshot().challenge?.revokeConsent).toBe(false);
  controller.chooseAllConsent(true);
  expect(controller.snapshot().challenge).toBeNull();
  await controller.execute();
  expect(requests.some((request) => request.url.endsWith('/execute'))).toBe(false);
});
it.each(['delete_one', 'delete_person', 'delete_all'] as const)(
  '%s displays server count and executes only matching challenge after confirmation',
  async (action) => {
    const { controller, requests } = await setup();
    await controller.open(action === 'delete_person' ? person : null, null);
    controller.chooseAllConsent(true);
    await controller.prepare(action, action === 'delete_one' ? jobId : undefined);
    expect(controller.snapshot().challenge?.expectedCount).toBe(3);
    expect(controller.snapshot().phase).toBe('awaiting_user_confirmation');
    expect(requests.some((request) => request.url.endsWith('/execute'))).toBe(false);
    await controller.execute();
    expect(controller.snapshot().receipt?.action).toBe(action);
    expect(controller.snapshot().receipt?.affectedCount).toBe(3);
  },
);
it('expired challenge disables execute locally and requires explicit re-prepare', async () => {
  let now = Date.parse(time);
  const { controller, requests } = await setup(undefined, () => now);
  await controller.open();
  await controller.prepare('delete_one', jobId);
  now += 300_000;
  controller.tick();
  await controller.execute();
  expect(controller.snapshot().phase).toBe('expired');
  expect(requests.some((request) => request.url.endsWith('/execute'))).toBe(false);
});
it.each([
  'confirmation_expired',
  'confirmation_stale',
  'confirmation_required',
  'mutation_conflict',
])('server %s is definitive and never reported as success', async (code) => {
  const { controller } = await setup(async (request) =>
    request.url.endsWith('/execute')
      ? json({ error: { code, message: 'private' } }, 409)
      : undefined,
  );
  await controller.open();
  await controller.prepare('delete_one', jobId);
  await controller.execute();
  expect(controller.snapshot().phase).toBe(
    code === 'confirmation_expired' ? 'expired' : 'stale_or_conflict',
  );
  expect(controller.snapshot().receipt).toBeNull();
  expect(controller.snapshot().canRetry).toBe(false);
});
it('pause while executing rejects late success and retains only safe retry target', async () => {
  let release!: () => void;
  const { controller } = await setup(async (request) => {
    if (request.url.endsWith('/execute'))
      await new Promise<void>((resolve) => {
        release = resolve;
      });
  });
  await controller.open();
  await controller.prepare('delete_one', jobId);
  const pending = controller.execute();
  while (!release) await Promise.resolve();
  controller.pause();
  release();
  await pending;
  expect(controller.snapshot().phase).toBe('unknown_outcome');
  expect(controller.snapshot().detail).toBeNull();
  expect(controller.snapshot().items).toEqual([]);
  expect(controller.snapshot().receipt).toBeNull();
});
it('logout and owner A to B clear authority, records, challenge, receipt, and retry payload', async () => {
  const { controller, session, requests } = await setup();
  await controller.open();
  await controller.armUndo();
  await controller.execute();
  await session.logout();
  expect(controller.snapshot().items).toEqual([]);
  expect(controller.snapshot().receipt).toBeNull();
  expect(controller.snapshot().canRetry).toBe(false);
  await session.connect(token(other), async () => undefined);
  await controller.retry();
  expect(requests.filter((request) => request.url.endsWith('/undo'))).toHaveLength(1);
});
it('fresh controller cannot auto-replay after restart and discloses lost key limitation', async () => {
  const { controller, transport, session, requests } = await setup();
  await controller.open();
  await controller.prepare('delete_one', jobId);
  const restarted = new MemoryController(transport, session, () => person);
  await restarted.retry();
  expect(restarted.snapshot().canRetry).toBe(false);
  expect(requests.some((request) => request.url.endsWith('/execute'))).toBe(false);
  expect(MEMORY_RESTART_NOTICE).toContain('不能自动安全重试');
});
it('unconfirmed or mismatched receipt cannot become formal success', () => {
  expect(() => memoryReceiptView({ action: 'undo', status: 'deleted' } as never)).toThrow(ApiError);
});
it('paging bounds memory window, uses server cursor, and merges by ID rather than content', async () => {
  let page = 0;
  const { controller, requests } = await setup(async (request) => {
    if (new URL(request.url).pathname !== '/api/v1/memories') return;
    const offset = page++ * 50;
    return json({
      items: Array.from({ length: 50 }, (_, index) => ({
        ...record(),
        id: `00000000-0000-4000-8000-${String(offset + index).padStart(12, '0')}`,
      })),
      next_cursor: `opaque-${page}`,
      retention_policy_summary: '37',
      historical_notice: 'past',
    });
  });
  await controller.open();
  for (let index = 0; index < 5; index++) await controller.refresh(true);
  expect(controller.snapshot().items).toHaveLength(200);
  expect(page).toBe(4);
  expect(
    requests.some((request) => new URL(request.url).searchParams.get('cursor') === 'opaque-1'),
  ).toBe(true);
});

it('confirmed receipt survives a failed optional same-key replay', async () => {
  let loss = false;
  const { controller } = await setup(async (request) => {
    if (loss && request.url.endsWith('/undo')) throw new TypeError('lost replay');
  });
  await controller.open();
  await controller.armUndo();
  await controller.execute();
  const receipt = controller.snapshot().receipt;
  loss = true;
  await controller.retry();
  expect(controller.snapshot().phase).toBe('completed');
  expect(controller.snapshot().receipt).toEqual(receipt);
  expect(controller.snapshot().feedback).toContain('此前正式服务器回执');
});
it('failed durable lookup preserves previously verified receipt without proving the lookup succeeded', async () => {
  const { controller } = await setup();
  await controller.open();
  await controller.armUndo();
  await controller.execute();
  const receipt = controller.snapshot().receipt;
  await controller.inspectReceipt(other);
  expect(controller.snapshot().receipt).toEqual(receipt);
  expect(controller.snapshot().status).toBe('error');
});
it('late non-cooperative response after epoch change cannot restore owner A data for B', async () => {
  let finish!: (response: Response) => void;
  const { controller, session } = await setup(async (request) =>
    request.url.endsWith('/control')
      ? await new Promise<Response>((resolve) => {
          finish = resolve;
        })
      : undefined,
  );
  const pending = controller.open();
  while (!finish) await Promise.resolve();
  await session.logout();
  await session.connect(token(other), async () => undefined);
  finish(json(control()));
  await pending;
  expect(controller.snapshot().control).toBeNull();
  expect(controller.snapshot().items).toEqual([]);
});
it('a malformed successful mutation response remains unknown rather than claiming a receipt', async () => {
  const { controller } = await setup(async (request) =>
    request.url.endsWith('/execute')
      ? json({
          mutation_id: rel,
          action: 'delete_one',
          status: 'deleted',
          primary_store_only: true,
          affected_count: 1,
          operation_key: 'wrong key',
        })
      : undefined,
  );
  await controller.open();
  await controller.prepare('delete_one', jobId);
  await controller.execute();
  expect(controller.snapshot().phase).toBe('unknown_outcome');
  expect(controller.snapshot().receipt).toBeNull();
  expect(controller.snapshot().canRetry).toBe(true);
});
