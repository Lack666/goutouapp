import { createNativeSseObserver } from '../src/diagnostics/nativeSseObserver';
import { validateAgentEvent } from '../src/api/agentEvents';

const run = '11111111-1111-4111-8111-111111111111';
const other = '22222222-2222-4222-8222-222222222222';
const event = (id = run) =>
  validateAgentEvent('run_started', {
    schema_version: '1',
    event: 'run_started',
    run_id: id,
    data: {},
  });
it('is inert when disabled, including binding and subscriptions', () => {
  const observer = createNativeSseObserver(false);
  const listener = jest.fn();
  observer.subscribe(listener);
  const ticket = observer.begin();
  observer.event(ticket, event());
  observer.ui('running', 'analyzing');
  observer.reader(ticket, 'reads');
  expect(observer.snapshot()).toBeNull();
  expect(listener).not.toHaveBeenCalled();
});
it('reports relative metadata, detects ID mismatches, and never exports IDs or data', () => {
  let now = 100;
  const observer = createNativeSseObserver(true, () => now);
  const ticket = observer.begin();
  now = 120;
  observer.reader(ticket, 'reads');
  observer.event(ticket, event());
  observer.event(ticket, event(other)); // One read can contain multiple events.
  observer.ui('running', 'checking_safety');
  const snapshot = observer.snapshot();
  expect(snapshot).toMatchObject({
    reader: { reads: 1 },
    consistentRun: false,
    events: [
      { type: 'run_started', ms: 20 },
      { type: 'run_started', ms: 20 },
    ],
  });
  expect(JSON.stringify(snapshot)).not.toContain(run);
  expect(JSON.stringify(snapshot)).not.toContain(other);
  expect(JSON.stringify(snapshot)).not.toContain('data');
});
it('ignores an old response after a new run begins and keeps snapshots immutable', () => {
  const observer = createNativeSseObserver(true);
  const old = observer.begin();
  observer.event(old, event());
  const snapshot = observer.snapshot();
  const current = observer.begin();
  observer.reader(old, 'releases');
  observer.event(old, event(other));
  observer.interrupted(old, false);
  observer.reader(current, 'reads');
  observer.reader(current, 'cancels');
  observer.reader(current, 'releases');
  observer.interrupted(current, true);
  expect(snapshot?.events).toHaveLength(1);
  expect(observer.snapshot()).toMatchObject({
    events: [],
    consistentRun: true,
    reader: { reads: 1, cancels: 1, releases: 1 },
    terminal: 'cancelled',
  });
});
it('bounds event and UI metadata, and a terminal event survives interrupted cleanup', () => {
  const observer = createNativeSseObserver(true);
  const ticket = observer.begin();
  for (let i = 0; i < 100; i++) {
    observer.event(ticket, event());
    observer.ui('running', 'analyzing');
  }
  observer.event(
    ticket,
    validateAgentEvent('failed', {
      schema_version: '1',
      event: 'failed',
      run_id: run,
      data: { code: 'agent_failure', recovery_status: 'failed' },
    }),
  );
  observer.interrupted(ticket, true);
  expect(observer.snapshot()?.events).toHaveLength(64);
  expect(observer.snapshot()?.ui).toHaveLength(64);
  expect(observer.snapshot()?.terminal).toBe('failed');
});
