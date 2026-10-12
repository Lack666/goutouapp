import type { AgentEvent, ProgressStatus } from '../api/agentEvents';

type Phase =
  | 'idle'
  | 'submitting'
  | 'running'
  | 'committed'
  | 'completed'
  | 'failed'
  | 'running_unknown';
type Terminal = 'completed' | 'failed' | 'cancelled' | 'disconnected' | null;
type Observation = {
  reader: { reads: number; cancels: number; releases: number };
  events: { type: AgentEvent['event']; ms: number }[];
  ui: { phase: Phase; progress: ProgressStatus | null; ms: number }[];
  consistentRun: boolean;
  terminal: Terminal;
};

// Only public protocol metadata enters this bounded observer. Bodies and IDs are
// deliberately excluded from snapshots; the first ID is private to a comparison.
export function createNativeSseObserver(enabled: boolean, clock = () => Date.now()) {
  const listeners = new Set<() => void>();
  const responses = new WeakMap<Response, number>();
  let generation = 0;
  let started = 0;
  let firstRun: string | undefined;
  let value: Observation | null = null;
  const update = (ticket: number, change: (old: Observation) => Observation) => {
    if (!enabled || ticket !== generation || !value) return;
    value = change(value);
    listeners.forEach((listener) => listener());
  };
  const ms = () => Math.max(0, clock() - started);
  return {
    enabled,
    subscribe(listener: () => void) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    snapshot: () => value,
    begin() {
      if (!enabled) return 0;
      generation++;
      started = clock();
      firstRun = undefined;
      value = {
        reader: { reads: 0, cancels: 0, releases: 0 },
        events: [],
        ui: [],
        consistentRun: true,
        terminal: null,
      };
      listeners.forEach((listener) => listener());
      return generation;
    },
    bind(response: Response, ticket: number) {
      if (enabled) responses.set(response, ticket);
    },
    ticket(response: Response) {
      return responses.get(response) ?? 0;
    },
    reader(ticket: number, operation: 'reads' | 'cancels' | 'releases') {
      update(ticket, (old) => ({
        ...old,
        reader: { ...old.reader, [operation]: old.reader[operation] + 1 },
      }));
    },
    event(ticket: number, event: AgentEvent) {
      update(ticket, (old) => {
        firstRun ??= event.run_id;
        return {
          ...old,
          consistentRun: old.consistentRun && firstRun === event.run_id,
          events: [...old.events, { type: event.event, ms: ms() }].slice(-64),
          terminal:
            event.event === 'completed' || event.event === 'failed' ? event.event : old.terminal,
        };
      });
    },
    ui(phase: Phase, progress: ProgressStatus | null) {
      update(generation, (old) => ({
        ...old,
        ui: [...old.ui, { phase, progress, ms: ms() }].slice(-64),
      }));
    },
    interrupted(ticket: number, aborted: boolean) {
      update(ticket, (old) => ({
        ...old,
        terminal: old.terminal ?? (aborted ? 'cancelled' : 'disconnected'),
      }));
    },
  };
}
