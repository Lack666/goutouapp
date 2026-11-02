import { ApiError } from '../src/api/errors';
import { importJobView, importReceiptView } from '../src/api/importAdapter';
import { LOCAL_IMPORT_BYTE_LIMIT, validateSourceTimezone } from '../src/data/importController';
import {
  file,
  job,
  jobId,
  rel,
  person,
  other,
  json,
  receipt,
  sessions,
  setup,
  prepare,
  token,
} from './importSupport';
afterEach(async () => {
  for (const session of sessions.splice(0)) await session.logout();
});
it('select/cancel/reselect are local and never automatically upload', async () => {
  const { controller, requests } = await setup();
  const first = file();
  await controller.select(async () => first);
  expect(controller.snapshot().upload).toBe('selected');
  expect(controller.snapshot().file).toEqual({
    name: first.name,
    size: first.size,
    mimeType: first.mimeType,
  });
  await controller.select(async () => null);
  expect(first.release).not.toHaveBeenCalled();
  await controller.select(async () => file('new.markdown'));
  expect(first.release).toHaveBeenCalledTimes(1);
  expect(requests).toHaveLength(0);
  expect(controller.snapshot()).not.toHaveProperty('uri');
});
it('explicit selection cancellation rejects a late picker and releases its cache', async () => {
  const { controller } = await setup();
  const selected = file();
  let finish!: (value: typeof selected) => void;
  const pending = controller.select(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  controller.cancelSelection();
  finish(selected);
  await pending;
  expect(controller.snapshot().file).toBeNull();
  expect(selected.release).toHaveBeenCalled();
});
it.each([
  ['private.pdf', 5, '仅开放'],
  ['large.md', LOCAL_IMPORT_BYTE_LIMIT + 1, '100 MiB'],
  ['empty.md', 0, '无法读取'],
])('rejects %s without any HTTP upload', async (name, size, message) => {
  const { controller, requests } = await setup();
  await controller.select(async () => file(name as string, size as number));
  await controller.upload();
  expect(controller.snapshot().upload).toBe('failed');
  expect(controller.snapshot().error).toContain(message);
  expect(requests).toHaveLength(0);
});
it.each(['not/a_timezone', '+08:00', ' Asia/Shanghai', ''])(
  'rejects invalid source timezone %s',
  (value) => {
    expect(() => validateSourceTimezone(value)).toThrow(ApiError);
  },
);
it.each(['Asia/Shanghai', 'America/New_York', 'UTC'])(
  'accepts explicit IANA source timezone %s',
  (value) => {
    expect(() => validateSourceTimezone(value)).not.toThrow();
  },
);
it('multipart carries real UTF8 bytes, explicit format/timezone, current JWT and automatic boundary', async () => {
  const { controller, requests, session } = await setup();
  const selected = file();
  await controller.select(async () => selected);
  controller.timezone('Asia/Shanghai');
  await controller.upload();
  const request = requests.find((r) => r.method === 'POST')!;
  const form = (await request.formData()) as unknown as {
    get(key: string): FormDataEntryValue | null;
  };
  expect(await (form.get('file') as File).text()).toBe('# synthetic 微信\n');
  expect(form.get('source_timezone')).toBe('Asia/Shanghai');
  expect(form.get('source_format')).toBe('wechat_markdown_v1');
  expect(request.headers.get('Content-Type')).toMatch(/^multipart\/form-data; boundary=/);
  expect(request.headers.get('Authorization')).toBe(`Bearer ${session.credential()}`);
  expect(controller.snapshot().job?.id).toBe(jobId);
  expect(requests.at(-1)?.method).toBe('GET');
  expect(selected.release).toHaveBeenCalled();
});
it('file cache reading failure occurs before HTTP and does not create unknown upload', async () => {
  const { controller, requests } = await setup();
  const selected = {
    ...file(),
    binary: async () => {
      throw new ApiError('file_unreadable');
    },
  };
  await controller.select(async () => selected);
  await controller.upload();
  expect(controller.snapshot().upload).toBe('failed');
  expect(requests).toHaveLength(0);
});

it('explicit JSONL selection is carried through multipart without automatic analysis', async () => {
  const { controller, requests } = await setup();
  controller.format('chatlab_jsonl_v0_0_2');
  await controller.select(async () => file('anonymous.jsonl'));
  expect(requests).toHaveLength(0);
  await controller.upload();
  const request = requests.find((r) => r.method === 'POST')!;
  const form = (await request.formData()) as unknown as {
    get(key: string): FormDataEntryValue | null;
  };
  expect(form.get('source_format')).toBe('chatlab_jsonl_v0_0_2');
  expect(requests.every((r) => !r.url.includes('imported-analysis'))).toBe(true);
});
it('upload response loss retains selection and never retries or creates a second job automatically', async () => {
  const { controller, requests } = await setup(async (r) => {
    if (r.url.endsWith('/chat-imports')) throw new TypeError('private source must not surface');
  });
  await controller.select(async () => file());
  await controller.upload();
  expect(controller.snapshot().upload).toBe('unknown_outcome');
  expect(controller.snapshot().error).toContain('unknown_upload_outcome');
  expect(controller.snapshot().error).not.toContain('private source');
  await controller.upload();
  await controller.select(async () => file());
  expect(requests).toHaveLength(1);
  expect(controller.snapshot().file?.name).toBe('synthetic.md');
});
it('timeout after upload dispatch is unknown and active duplicate Upload is guarded', async () => {
  const { controller, requests } = await setup(
    async (r) => (r.url.endsWith('/chat-imports') ? new Promise(() => undefined) : undefined),
    15,
  );
  await controller.select(async () => file());
  await Promise.all([controller.upload(), controller.upload()]);
  expect(requests).toHaveLength(1);
  expect(controller.snapshot().upload).toBe('unknown_outcome');
});
it('parser summary preserves historical bounds/raw labels and labels warnings as sampled', () => {
  const view = importJobView(job());
  expect(view.speakers.map((s) => s.rawLabel)).toEqual(['我', '匿名🥰']);
  expect(view.speakers.every((s) => s.binding === 'unbound')).toBe(true);
  expect(view.summary.firstTimestamp).toContain('2024-');
  expect(view.warningCount).toBe(2);
  expect(view.truncatedIssues).toBe(1);
  expect(view.issueSamples).toEqual(['synthetic_warning']);
});
it('readiness/finalize are gated before explicit identity and relationship confirmation', async () => {
  const { controller, requests } = await setup();
  await controller.select(async () => file());
  await controller.upload();
  await controller.ready();
  await controller.finalize();
  expect(requests.some((r) => r.url.endsWith('/ready') || r.url.endsWith('/finalize'))).toBe(false);
});
it('explicit speaker/relationship binding sends exact labels, owned UUID and current revisions', async () => {
  const { controller, requests } = await setup();
  await prepare(controller);
  const mutations = requests.filter((r) => r.method === 'PUT');
  expect(await mutations[0]!.json()).toEqual({
    raw_speaker_label: '我',
    binding_kind: 'self',
    person_id: null,
    expected_revision: 0,
  });
  expect(await mutations[1]!.json()).toEqual({
    raw_speaker_label: '匿名🥰',
    binding_kind: 'person',
    person_id: person,
    expected_revision: 1,
  });
  expect(await mutations[2]!.json()).toEqual({ relationship_id: rel, expected_revision: 2 });
  expect(await requests.find((r) => r.url.endsWith('/ready'))!.text()).toBe('');
  expect(controller.snapshot().job?.status).toBe('ready');
});
it('stale revision re-inspects, clears every confirmation, and requires another user submission', async () => {
  let conflict = true;
  const { controller, setState, requests } = await setup(async (r) => {
    if (r.url.endsWith('/speakers') && conflict) {
      conflict = false;
      return json({ error: { code: 'stale_revision', message: 'private' } }, 409);
    }
  });
  await controller.select(async () => file());
  await controller.upload();
  setState({ ...job(), binding_revision: 7 });
  await controller.bindSpeaker('我', 'self');
  expect(controller.snapshot().job?.revision).toBe(7);
  expect(controller.snapshot().confirmations).toEqual([]);
  expect(controller.snapshot().relationshipConfirmed).toBe(false);
  expect(requests.at(-1)?.method).toBe('GET');
  await controller.bindSpeaker('我', 'self');
  expect(
    (
      await requests
        .filter((r) => r.method === 'PUT')
        .at(-1)!
        .json()
    ).expected_revision,
  ).toBe(7);
});
it('relationship switch invalidates speaker confirmations and compatibility fails closed', async () => {
  const { controller, setState } = await setup();
  await prepare(controller);
  await controller.chooseRelationship(other);
  expect(controller.snapshot().scope).toBe('error');
  expect(controller.snapshot().confirmations).toEqual([]);
  expect(controller.snapshot().relationshipConfirmed).toBe(false);
  await controller.chooseRelationship(rel);
  setState({
    ...job(),
    speakers: [
      { raw_speaker_label: '我', binding_kind: 'self', person_id: null, message_count: 1 },
      { raw_speaker_label: '匿名🥰', binding_kind: 'person', person_id: other, message_count: 2 },
    ],
  });
  await controller.inspect();
  await controller.confirmRelationship();
  expect(controller.snapshot().error).toContain('不兼容');
});
it.each([
  ['stale_revision', 409],
  ['binding_invalid', 400],
  ['job_not_ready', 409],
  ['artifact_unavailable', 409],
  ['parse_failed', 422],
  ['upload_too_large', 413],
  ['unsupported_format', 415],
  ['import_failed', 503],
])('maps actual %s safely', async (code, status) => {
  const { controller } = await setup(async (r) =>
    r.url.endsWith('/chat-imports')
      ? json({ error: { code, message: 'private JWT transcript SQL' } }, status as number)
      : undefined,
  );
  await controller.select(async () => file());
  await controller.upload();
  expect(controller.snapshot().error).not.toContain('private JWT');
  expect(controller.snapshot().error).not.toBeNull();
});
it('group rejection displays current server readiness issues, preserving explicit system/ignore roles', async () => {
  const { controller, setState } = await setup(async (r) =>
    r.url.endsWith('/ready') ? json({ error: { code: 'job_not_ready' } }, 409) : undefined,
  );
  await prepare(controller);
  setState({
    ...job(),
    status: 'awaiting_binding',
    binding_revision: 3,
    readiness_issues: ['unsupported_group_binding'],
  });
  await controller.inspect();
  expect(controller.snapshot().job?.readinessIssues).toContain('unsupported_group_binding');
  await controller.finalize();
  expect(controller.snapshot().receipt).toBeNull();
});
it('finalize/replay expose formal receipts and use server revisions without second upload', async () => {
  const { controller, requests } = await setup();
  await prepare(controller);
  await controller.finalize();
  expect(controller.snapshot().receipt?.newCount).toBe(3);
  await controller.finalize();
  expect(controller.snapshot().receipt?.newCount).toBe(0);
  expect(controller.snapshot().receipt?.status).toBe('already_imported');
  expect(requests.filter((r) => r.url.endsWith('/chat-imports'))).toHaveLength(1);
  expect(
    (
      await requests
        .filter((r) => r.url.endsWith('/finalize'))
        .at(-1)!
        .json()
    ).expected_revision,
  ).toBe(3);
});
it('full exact-dataset duplicate receipt may point to a different dataset, never guessed from text', () => {
  const view = importReceiptView({ ...receipt(0), dataset_job_id: other });
  expect(view.datasetId).toBe(other);
  expect(view.jobId).toBe(jobId);
  expect(view.newCount).toBe(0);
});
it('finalize response loss recovers imported inspect summary with no additional finalize', async () => {
  const { controller, setState, requests } = await setup(async (r) => {
    if (r.url.endsWith('/finalize')) {
      const full = receipt();
      setState({
        ...job(),
        status: 'imported',
        binding_revision: 3,
        bound_relationship_id: rel,
        artifact_state: 'deleted',
        receipt: {
          dataset_job_id: jobId,
          relationship_id: rel,
          imported_message_count: 3,
          ignored_message_count: 0,
          system_message_count: 0,
          imported_at: full.imported_at,
          transcript_fingerprint: full.transcript_fingerprint,
        },
      });
      throw new TypeError();
    }
  });
  await prepare(controller);
  await controller.finalize();
  expect(controller.snapshot().receipt?.status).toBe('imported_summary');
  expect(controller.snapshot().receipt?.newCount).toBeNull();
  expect(requests.filter((r) => r.url.endsWith('/finalize'))).toHaveLength(1);
  expect(controller.snapshot().outcome).toBe('known');
});
it('cancel is acknowledged by server; AbortSignal alone never reports server cancelled', async () => {
  const { controller } = await setup();
  await controller.select(async () => file());
  await controller.upload();
  await controller.cancel();
  expect(controller.snapshot().job?.status).toBe('cancelled');
  expect(controller.snapshot().error).toContain('服务器已确认');
});
it('unknown cancel response with unresolved inspect remains unknown', async () => {
  const { controller } = await setup(async (r) => {
    if (r.url.endsWith('/cancel')) throw new TypeError();
  });
  await controller.select(async () => file());
  await controller.upload();
  await controller.cancel();
  expect(controller.snapshot().job?.status).toBe('awaiting_binding');
  expect(controller.snapshot().outcome).toBe('unknown_cancel_outcome');
});
it('owner change clears file summaries/jobs/revisions and rejects late selections', async () => {
  const { controller, session } = await setup();
  await prepare(controller);
  await session.connect(token(other), async () => undefined);
  expect(controller.snapshot().file).toBeNull();
  expect(controller.snapshot().job).toBeNull();
  expect(controller.snapshot().confirmations).toEqual([]);
});
it('route switch releases selection and clears previous task, while unmount preserves only known Job metadata', async () => {
  const { controller } = await setup();
  const selected = file();
  await controller.select(async () => selected);
  controller.leave();
  expect(selected.release).toHaveBeenCalled();
  await controller.select(async () => file());
  await controller.upload();
  controller.leave();
  expect(controller.snapshot().job?.id).toBe(jobId);
  await controller.open(rel);
  expect(controller.snapshot().job).toBeNull();
});
it('known Job UUID recovery only inspects, never uploads or infers confirmations', async () => {
  const { controller, requests } = await setup();
  await controller.recoverJob(jobId);
  expect(controller.snapshot().job?.id).toBe(jobId);
  expect(controller.snapshot().confirmations).toEqual([]);
  expect(requests.every((r) => r.method === 'GET')).toBe(true);
});
it('server401 invalidates the shared session and clears source/Job before publishing an error', async () => {
  const { controller, session } = await setup(async (r) =>
    r.url.endsWith('/chat-imports')
      ? json({ error: { code: 'invalid_credential' } }, 401)
      : undefined,
  );
  await controller.select(async () => file());
  await controller.upload();
  expect(session.snapshot().status).toBe('invalid');
  expect(controller.snapshot().file).toBeNull();
  expect(controller.snapshot().job).toBeNull();
  expect(controller.snapshot().upload).toBe('idle');
});
it('stopping an active upload aborts waiting and cannot accept the delayed Job or claim server cancel', async () => {
  let finish!: (response: Response) => void;
  const { controller, requests } = await setup(async (r) =>
    r.url.endsWith('/chat-imports')
      ? new Promise((resolve) => {
          finish = resolve;
        })
      : undefined,
  );
  await controller.select(async () => file());
  const pending = controller.upload();
  while (!finish) await new Promise((resolve) => setTimeout(resolve, 0));
  controller.pause();
  finish(json(job(), 201));
  await pending;
  expect(controller.snapshot().upload).toBe('unknown_outcome');
  expect(controller.snapshot().job).toBeNull();
  expect(requests.some((r) => r.url.endsWith('/cancel'))).toBe(false);
});
it('unresolved finalize response remains unknown and never auto-retries; explicit same-Job retry is available', async () => {
  let calls = 0;
  const { controller } = await setup(async (r) => {
    if (r.url.endsWith('/finalize')) {
      calls++;
      throw new TypeError();
    }
  });
  await prepare(controller);
  await controller.finalize();
  expect(controller.snapshot().outcome).toBe('unknown_finalize_outcome');
  expect(calls).toBe(1);
  await controller.finalize();
  expect(calls).toBe(2);
  expect(controller.snapshot().receipt).toBeNull();
});
it('system and ignore identities are explicit revisioned submissions, with no arbitrary Person ID', async () => {
  const { controller, requests } = await setup();
  await controller.select(async () => file());
  await controller.upload();
  await controller.bindSpeaker('我', 'system');
  await controller.bindSpeaker('匿名🥰', 'ignore');
  const bodies = await Promise.all(requests.filter((r) => r.method === 'PUT').map((r) => r.json()));
  expect(bodies.map((b) => [b.binding_kind, b.person_id])).toEqual([
    ['system', null],
    ['ignore', null],
  ]);
});
it('invalid synthetic Person ID is not sent to the binding API', async () => {
  const { controller, requests } = await setup();
  await controller.select(async () => file());
  await controller.upload();
  await controller.bindSpeaker('匿名🥰', 'person', 'Demo A');
  expect(requests.some((r) => r.method === 'PUT')).toBe(false);
  expect(controller.snapshot().confirmations).toEqual([]);
});
it('logout during conflict recovery rejects the delayed inspect and its old error', async () => {
  let armed = false;
  let finish!: (response: Response) => void;
  const { controller, session } = await setup(async (r) => {
    if (!armed) return;
    if (r.method === 'PUT') return json({ error: { code: 'stale_revision' } }, 409);
    if (r.url.endsWith(`/chat-imports/${jobId}`))
      return new Promise((resolve) => {
        finish = resolve;
      });
  });
  await prepare(controller);
  armed = true;
  const pending = controller.bindSpeaker('我', 'self');
  while (!finish) await new Promise((resolve) => setTimeout(resolve, 0));
  await session.logout();
  finish(json(job()));
  await pending;
  expect(controller.snapshot().job).toBeNull();
  expect(controller.snapshot().error).toBeNull();
  expect(controller.snapshot().confirmations).toEqual([]);
});
