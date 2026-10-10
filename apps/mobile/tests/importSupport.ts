import { runInThisContext } from 'node:vm';
import { ApiTransport } from '../src/api/transport';
import { ImportController } from '../src/data/importController';
import { DevelopmentSession } from '../src/session/developmentSession';
import { createVolatileTokenStorage } from '../src/session/storage';
import { asUUID } from '../src/api/uuid';
import type { components } from '../src/api/generated/client';
import type { SelectedImportFile } from '../src/contracts/connectedImport';
Object.assign(
  globalThis,
  Object.fromEntries(
    [
      'Request',
      'Response',
      'Headers',
      'FormData',
      'Blob',
      'File',
      'AbortController',
      'TextEncoder',
      'TextDecoder',
    ].map((key) => [key, runInThisContext(key)]),
  ),
);
export const rel = asUUID('11111111-1111-4111-8111-111111111111');
export const person = asUUID('22222222-2222-4222-8222-222222222222');
export const jobId = asUUID('33333333-3333-4333-8333-333333333333');
export const other = asUUID('44444444-4444-4444-8444-444444444444');
export const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
export const token = (sub = person) =>
  `e30.${Buffer.from(JSON.stringify({ sub, exp: Date.now() / 1000 + 900 })).toString('base64url')}.synthetic`;
export function job(): components['schemas']['ImportJobResponse'] {
  return {
    id: jobId,
    artifact_id: other,
    artifact_state: 'active',
    status: 'awaiting_binding',
    source_format: 'wechat_markdown_v1',
    parser_version: '1',
    schema_version: '1',
    source_timezone: 'Asia/Shanghai',
    source_fingerprint: 'a'.repeat(64),
    transcript_fingerprint: 'b'.repeat(64),
    message_count: 3,
    speaker_count: 2,
    first_timestamp_utc: '2024-01-01T00:00:00Z',
    last_timestamp_utc: '2024-01-01T01:00:00Z',
    warning_count: 2,
    error_count: 0,
    issues_truncated: 1,
    issue_code_samples: ['synthetic_warning'],
    bound_relationship_id: null,
    binding_revision: 0,
    imported_message_count: null,
    ignored_message_count: null,
    system_message_count: null,
    imported_at: null,
    possible_duplicate_job_id: null,
    created_at: '2026-10-10T00:00:00Z',
    updated_at: '2026-10-10T00:00:00Z',
    speakers: [
      { raw_speaker_label: '我', message_count: 1, binding_kind: 'unbound', person_id: null },
      { raw_speaker_label: '匿名🥰', message_count: 2, binding_kind: 'unbound', person_id: null },
    ],
    readiness_issues: ['unbound_speakers'],
    receipt: null,
  };
}
export function file(name = 'synthetic.md', size?: number): SelectedImportFile {
  const binary = new Blob(['# synthetic 微信\n']);
  return {
    name,
    size: size ?? binary.size,
    mimeType: 'text/markdown',
    binary: jest.fn(async () => binary),
    release: jest.fn(),
  };
}
export const receipt = (newCount = 3): components['schemas']['ImportReceiptResponse'] => ({
  import_job_id: jobId,
  dataset_job_id: jobId,
  relationship_id: rel,
  imported_message_count: 3,
  ignored_message_count: 0,
  system_message_count: 0,
  new_message_count: newCount,
  first_timestamp_utc: '2024-01-01T00:00:00Z',
  last_timestamp_utc: '2024-01-01T01:00:00Z',
  transcript_fingerprint: 'b'.repeat(64),
  status: newCount ? 'imported' : 'already_imported',
  imported_at: '2026-10-10T00:00:00Z',
});
export const sessions: DevelopmentSession[] = [];
export async function setup(
  wire?: (
    request: Request,
    state: components['schemas']['ImportJobResponse'],
  ) => Promise<Response | undefined>,
  timeout = 2000,
) {
  const session = new DevelopmentSession(createVolatileTokenStorage());
  sessions.push(session);
  let state = job();
  const requests: Request[] = [];
  const fetcher: typeof fetch = async (input) => {
    const request = input as Request;
    requests.push(request.clone());
    const custom = await wire?.(request, state);
    if (custom) return custom;
    const path = new URL(request.url).pathname;
    if (path === '/api/v1/persons') return json({ items: [], next_cursor: null });
    if (path.startsWith('/api/v1/relationships/')) return json({ id: rel, person_id: person });
    if (path === '/api/v1/chat-imports') return json(state, 201);
    if (request.method === 'GET') return json(state);
    if (path.endsWith('/speakers')) {
      const body = (await request.json()) as components['schemas']['SpeakerBindingRequest'];
      state = {
        ...state,
        binding_revision: state.binding_revision + 1,
        speakers: state.speakers.map((s) =>
          s.raw_speaker_label === body.raw_speaker_label
            ? { ...s, binding_kind: body.binding_kind, person_id: body.person_id ?? null }
            : s,
        ),
      };
    } else if (path.endsWith('/relationship'))
      state = {
        ...state,
        binding_revision: state.binding_revision + 1,
        bound_relationship_id: rel,
      };
    else if (path.endsWith('/ready')) state = { ...state, status: 'ready', readiness_issues: [] };
    else if (path.endsWith('/cancel'))
      state = { ...state, status: 'cancelled', artifact_state: 'deleted' };
    else if (path.endsWith('/finalize')) {
      const full = receipt(state.status === 'imported' ? 0 : 3);
      state = {
        ...state,
        status: 'imported',
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
      };
      return json(full);
    }
    return json(state);
  };
  const transport = new ApiTransport(
    'http://127.0.0.1:8000',
    session,
    fetcher,
    timeout,
    true,
    true,
    fetcher,
    timeout,
    true,
    timeout,
  );
  const controller = new ImportController(transport, session);
  await session.connect(token(), async () => undefined);
  await controller.open(null);
  return {
    controller,
    session,
    transport,
    requests,
    setState: (s: components['schemas']['ImportJobResponse']) => {
      state = s;
    },
  };
}
export async function prepare(controller: ImportController) {
  await controller.select(async () => file());
  await controller.upload();
  await controller.chooseRelationship(rel);
  await controller.bindSpeaker('我', 'self');
  await controller.bindSpeaker('匿名🥰', 'person', person);
  await controller.confirmRelationship();
  await controller.ready();
}
