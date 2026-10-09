import { runInThisContext } from 'node:vm';
import { SSEParser, consumeSSE } from '../src/api/sseParser';
import { validateAgentEvent } from '../src/api/agentEvents';
Object.assign(
  globalThis,
  Object.fromEntries(
    ['TextEncoder', 'TextDecoder', 'Response', 'ReadableStream', 'AbortController'].map((key) => [
      key,
      runInThisContext(key),
    ]),
  ),
);
const run = '11111111-1111-4111-8111-111111111111';
const message = '22222222-2222-4222-8222-222222222222';
const frame = (event: string, data: unknown, extra = {}) =>
  `event: ${event}\ndata: ${JSON.stringify({ schema_version: '1', event, run_id: run, data, ...extra })}\n\n`;
const answer = frame('final_response', {
  assistant_message_id: message,
  answer: '中文🌱\n完整回答',
});
const end = frame('completed', {
  status: 'completed',
  assistant_message_id: message,
  memory_status: 'none',
});
const bytes = (text: string) => new TextEncoder().encode(text);
it('accepts every two-part byte boundary including Chinese/emoji and partial JSON', () => {
  const input = bytes(answer + end);
  for (let split = 0; split <= input.length; split++) {
    const events: unknown[] = [];
    const parser = new SSEParser((e) => events.push(e));
    parser.push(input.slice(0, split));
    parser.push(input.slice(split));
    parser.finish();
    expect(events).toHaveLength(2);
    expect(events[0]).toMatchObject({ data: { answer: '中文🌱\n完整回答' } });
  }
});
it('accepts single-byte chunks, CRLF splits, comments and multiple frames per chunk', () => {
  const events: unknown[] = [];
  const parser = new SSEParser((e) => events.push(e));
  for (const byte of bytes(': harmless comment\r\n\r\n' + (answer + end).replace(/\n/g, '\r\n')))
    parser.push(Uint8Array.of(byte));
  parser.finish();
  expect(events).toHaveLength(2);
});
it('joins multi-line data before JSON validation', () => {
  const events: unknown[] = [];
  const parser = new SSEParser((e) => events.push(e));
  parser.push(
    bytes(
      `event: run_started\ndata: {"schema_version":"1",\ndata: "event":"run_started","run_id":"${run}","data":{}}\n\n`,
    ),
  );
  parser.finish();
  expect(events).toHaveLength(1);
});
it.each([
  ['malformed JSON', 'event: status\ndata: nope\n\n'],
  [
    'no event',
    `data: ${JSON.stringify({ schema_version: '1', event: 'run_started', run_id: run, data: {} })}\n\n`,
  ],
  ['unknown event', frame('token_delta', {})],
  ['unknown version', frame('run_started', {}, { schema_version: '2' })],
  ['extra internal fields', frame('run_started', {}, { internal: 'private' })],
  ['bad run id', frame('run_started', {}, { run_id: 'demo-A' })],
  ['event mismatch', frame('status', { status: 'preparing' }, { event: 'run_started' })],
  ['bad status', frame('status', { status: 'internal_node' })],
  ['bad final', frame('final_response', { answer: 'answer', assistant_message_id: 'demo' })],
  ['bad memory', frame('memory_status', { status: 'secret' })],
  ['bad confirmation', frame('pending_confirmation', { status: 'saved' })],
  [
    'bad completed',
    frame('completed', { status: 'running', assistant_message_id: message, memory_status: 'none' }),
  ],
  ['bad failure', frame('failed', { code: 'SQL traceback', recovery_status: 'failed' })],
  ['extension field', 'id: 1\n\n'],
])('rejects %s', (_label, text) => {
  const parser = new SSEParser(() => undefined);
  expect(() => parser.push(bytes(text))).toThrow();
});
it.each([
  ['run_started', {}],
  ['status', { status: 'checking_safety' }],
  ['final_response', { assistant_message_id: message, answer: 'safe' }],
  ['memory_status', { status: 'failed' }],
  ['pending_confirmation', { status: 'pending_confirmation' }],
  ['completed', { status: 'completed', assistant_message_id: message, memory_status: 'none' }],
  ['failed', { code: 'agent_failure', recovery_status: 'running_unknown' }],
])('validates public event %s', (event, data) => {
  expect(validateAgentEvent(event, { schema_version: '1', event, run_id: run, data }).event).toBe(
    event,
  );
});
it('enforces line/frame and cumulative byte bounds independently', () => {
  expect(() => new SSEParser(() => undefined, 8).push(bytes('data: 超过限制'))).toThrow();
  expect(() => new SSEParser(() => undefined, 1000, 5).push(bytes(': comment\n\n'))).toThrow();
  const parser = new SSEParser(() => undefined, 18);
  expect(() => parser.push(bytes('data: one\ndata: two\ndata: three\n'))).toThrow();
});
it('rejects truncated UTF-8 and an unterminated last frame', () => {
  const parser = new SSEParser(() => undefined);
  parser.push(Uint8Array.of(0xe4, 0xb8));
  expect(() => parser.finish()).toThrow();
  const partial = new SSEParser(() => undefined);
  partial.push(bytes(answer.trimEnd()));
  expect(() => partial.finish()).toThrow();
});
it('cleans up reader after normal terminal and rejects nonterminal EOF', async () => {
  let cancelled = 0;
  const response = new Response(
    new ReadableStream({
      start(c) {
        c.enqueue(bytes(end));
      },
      cancel() {
        cancelled++;
      },
    }),
    { headers: { 'Content-Type': 'text/event-stream; charset=utf-8' } },
  );
  await consumeSSE(
    response,
    new AbortController().signal,
    () => undefined,
    (p) => p,
  );
  expect(cancelled).toBe(1);
  expect(response.body?.locked).toBe(false);
  await expect(
    consumeSSE(
      new Response(answer, { headers: { 'Content-Type': 'text/event-stream' } }),
      new AbortController().signal,
      () => undefined,
      (p) => p,
    ),
  ).rejects.toMatchObject({ kind: 'incomplete_stream' });
});
it('rejects incorrect content type', async () => {
  let cancelled = false;
  const response = new Response(
    new ReadableStream({
      cancel() {
        cancelled = true;
      },
    }),
  );
  await expect(
    consumeSSE(
      response,
      new AbortController().signal,
      () => undefined,
      (p) => p,
    ),
  ).rejects.toMatchObject({ kind: 'protocol' });
  expect(cancelled).toBe(true);
});
