import { test, expect } from '../connected/fixture';
import { connected, selectedFixture, bind } from './support';
import { asUUID } from '../src/api/uuid';
import { ImportController } from '../src/data/importController';
import { ImportHTTPError } from '../src/api/importErrors';

test('signed generated multipart / PostgreSQL / 1001 history occurrences / exact-dataset replay / owned isolation', async ({
  backend,
}) => {
  const { session, transport, imports, history, person, relationship, conversation } =
    await connected(backend.baseURL, backend.a);
  try {
    const before = await backend.importEvidence();
    await imports.select(async () => selectedFixture(1001));
    await imports.upload();
    expect(imports.snapshot().upload).toBe('job_created');
    expect(imports.snapshot().job?.speakers.every((s) => s.binding === 'unbound')).toBe(true);
    await bind(imports, person);
    expect(imports.snapshot().job?.status).toBe('ready');
    const job = imports.snapshot().job!;
    let stale = false;
    try {
      await transport.client.PUT('/api/v1/chat-imports/{job_id}/speakers', {
        params: { path: { job_id: asUUID(job.id) } },
        body: { raw_speaker_label: '我', binding_kind: 'self', expected_revision: 0 },
      });
    } catch (error) {
      stale = error instanceof ImportHTTPError && error.code === 'stale_revision';
    }
    expect(stale).toBe(true);
    await imports.finalize();
    const original = imports.snapshot().receipt!;
    expect(original.count).toBe(1001);
    expect(original.newCount).toBe(1001);
    expect(imports.snapshot().job?.artifactState).toBe('deleted');
    await imports.finalize();
    expect(imports.snapshot().receipt?.newCount).toBe(0);
    await history.open('relationship', relationship);
    while (history.snapshot().cursor) await history.load(true);
    expect(history.snapshot().items).toHaveLength(1001);
    expect(new Set(history.snapshot().items.map((m) => m.id)).size).toBe(1001);
    expect(new Set(history.snapshot().items.map((m) => m.timestamp)).size).toBe(1);
    expect(new Set(history.snapshot().items.map((m) => m.content)).size).toBe(1);
    const agent = await transport.client.GET('/api/v1/conversations/{conversation_id}/messages', {
      params: { path: { conversation_id: asUUID(conversation) } },
    });
    expect(agent.data?.items).toHaveLength(0);
    const duplicate = new ImportController(transport, session);
    await duplicate.open(relationship);
    await duplicate.select(async () => selectedFixture(1001));
    await duplicate.upload();
    await bind(duplicate, person);
    await duplicate.finalize();
    expect(duplicate.snapshot().receipt?.status).toBe('already_imported');
    expect(duplicate.snapshot().receipt?.datasetId).toBe(original.datasetId);
    expect(duplicate.snapshot().receipt?.jobId).not.toBe(original.jobId);
    expect(duplicate.snapshot().receipt?.newCount).toBe(0);
    expect(duplicate.snapshot().job?.status).toBe('ready');
    await duplicate.cancel();
    expect(duplicate.snapshot().job?.status).toBe('cancelled');
    expect(duplicate.snapshot().job?.artifactState).toBe('deleted');
    const after = await backend.importEvidence();
    expect(after.messages - before.messages).toBe(1001);
    expect(after.agent_messages).toBe(before.agent_messages);
    expect(after.memories).toBe(before.memories);
    await session.connect(backend.b, async () => undefined);
    expect(history.snapshot().items).toHaveLength(0);
    expect(imports.snapshot().job).toBeNull();
    await imports.recoverJob(original.jobId);
    expect(imports.snapshot().job).toBeNull();
    expect(imports.snapshot().error).toContain('不属于');
    await history.open('relationship', relationship);
    expect(history.snapshot().items).toHaveLength(0);
    expect(history.snapshot().status).toBe('error');
  } finally {
    await session.logout();
  }
});
test('actual upload Job committed but response lost: unknown outcome never automatically repeats multipart', async ({
  backend,
}) => {
  let drop = true;
  let uploads = 0;
  const wire: typeof fetch = async (input, init) => {
    const request = new Request(input, init);
    const response = await fetch(request);
    if (request.url.endsWith('/chat-imports') && request.method === 'POST') {
      uploads++;
      if (drop && response.ok) {
        drop = false;
        await response.text();
        throw new TypeError('injected response loss');
      }
    }
    return response;
  };
  const { session, imports } = await connected(backend.baseURL, backend.a, wire);
  try {
    const before = await backend.importEvidence();
    await imports.select(async () => selectedFixture(3, 'lost upload'));
    await imports.upload();
    expect(imports.snapshot().upload).toBe('unknown_outcome');
    expect(imports.snapshot().file?.name).toBe('anonymous-wechat-v1.md');
    expect(imports.snapshot().job).toBeNull();
    await imports.upload();
    expect(uploads).toBe(1);
    const after = await backend.importEvidence();
    expect(after.jobs.length - before.jobs.length).toBe(1);
    // The operator evidence is not a Mobile recovery API. Cleanup uses the known fixture ID.
    const lost = after.jobs.find((j) => !before.jobs.some((old) => old.id === j.id))!;
    await imports.recoverJob(lost.id);
    await imports.cancel();
    expect(imports.snapshot().job?.status).toBe('cancelled');
  } finally {
    await session.logout();
  }
});
test('actual finalized commit loses response: original Job inspect recovers summary, replay writes zero rows', async ({
  backend,
}) => {
  let drop = true;
  let finalizes = 0;
  const wire: typeof fetch = async (input, init) => {
    const request = new Request(input, init);
    const response = await fetch(request);
    if (request.url.endsWith('/finalize')) {
      finalizes++;
      if (drop && response.ok) {
        drop = false;
        await response.text();
        throw new TypeError('injected response loss');
      }
    }
    return response;
  };
  const { session, imports, person } = await connected(backend.baseURL, backend.a, wire);
  try {
    const before = await backend.importEvidence();
    await imports.select(async () => selectedFixture(7, 'lost finalize'));
    await imports.upload();
    await bind(imports, person);
    await imports.finalize();
    expect(imports.snapshot().receipt?.status).toBe('imported_summary');
    expect(imports.snapshot().outcome).toBe('known');
    expect(finalizes).toBe(1);
    await imports.finalize();
    expect(imports.snapshot().receipt?.status).toBe('already_imported');
    expect(imports.snapshot().receipt?.newCount).toBe(0);
    const after = await backend.importEvidence();
    expect(after.messages - before.messages).toBe(7);
    expect(after.memories).toBe(before.memories);
    expect(after.agent_messages).toBe(before.agent_messages);
  } finally {
    await session.logout();
  }
});
