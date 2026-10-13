import { runInThisContext } from 'node:vm';
import { ApiTransport } from '../src/api/transport';
import { asUUID } from '../src/api/uuid';

Object.assign(
  globalThis,
  Object.fromEntries(
    [
      'Request',
      'Response',
      'Headers',
      'ReadableStream',
      'TextEncoder',
      'TextDecoder',
      'AbortController',
    ].map((key) => [key, runInThisContext(key)]),
  ),
);

it('suppresses every late SSE event after the credential epoch changes, even without a controller subscriber', async () => {
  let epoch = 1;
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const onEvent = jest.fn();
  let pending!: Promise<void>;
  const ready = new Promise<void>((resolve) => {
    const transport = new ApiTransport(
      'http://localhost:8000',
      {
        credential: () => 'synthetic-credential',
        epoch: () => epoch,
        invalidate: () => undefined,
      },
      async () => {
        resolve();
        return new Response(
          new ReadableStream<Uint8Array>({
            start(value) {
              controller = value;
            },
          }),
          { headers: { 'Content-Type': 'text/event-stream' } },
        );
      },
      1000,
      true,
      true,
    );
    pending = transport.streamAgent(
      asUUID('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),
      { message: 'Synthetic', operation_key: 'synthetic-operation' },
      onEvent,
      new AbortController().signal,
    );
  });
  await ready;
  for (let step = 0; step < 8; step++) await Promise.resolve();
  epoch++;
  controller.enqueue(
    new TextEncoder().encode(
      'event: completed\ndata: {"schema_version":"1","event":"completed","run_id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","data":{"status":"completed","assistant_message_id":"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb","memory_status":"none"}}\n\n',
    ),
  );
  await expect(pending).rejects.toMatchObject({ kind: 'cancelled' });
  expect(onEvent).not.toHaveBeenCalled();
});
