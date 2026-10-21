import type { components } from '../api/generated/client';
import { ApiTransport } from '../api/transport';
import { ApiError, safeError } from '../api/errors';
import { ErasureHTTPError } from '../api/erasureErrors';
import { asUUID, asUUIDv4 } from '../api/uuid';
import type { DevelopmentSession } from '../session/developmentSession';

type Target = components['schemas']['MobileLifecycleTarget'];
type Challenge = components['schemas']['LifecycleChallenge'];
type Receipt = components['schemas']['LifecycleResult'];
type Body = Readonly<components['schemas']['MobileLifecycleExecute']>;
type Phase =
  | 'idle'
  | 'preparing'
  | 'awaiting_confirmation'
  | 'executing'
  | 'completed'
  | 'unknown_outcome'
  | 'failed'
  | 'expired'
  | 'stale'
  | 'target_busy';
const empty = () => ({
  phase: 'idle' as Phase,
  target: null as Target | null,
  challenge: null as Challenge | null,
  receipt: null as Receipt | null,
  refresh: 'idle' as 'idle' | 'verified' | 'failed',
  error: null as string | null,
});
const matches = (a: Target, b: Target) => a.domain === b.domain && a.target_id === b.target_id;
function check(value: unknown): asserts value {
  if (!value) throw new ApiError('protocol');
}
const countKeys = new Set([
  'persons',
  'relationships',
  'conversations',
  'agent_runs',
  'messages',
  'chat_import_jobs',
  'relationship_messages',
  'chat_import_speakers',
  'chat_import_artifacts',
  'memory_records',
]);
function counts(value: Record<string, number>) {
  check(value && typeof value === 'object' && !Array.isArray(value));
  check(Object.keys(value).length === countKeys.size);
  for (const [key, count] of Object.entries(value))
    check(countKeys.has(key) && Number.isSafeInteger(count) && count >= 0);
}

export class LifecycleController {
  private view = empty();
  private listeners = new Set<() => void>();
  private generation = 0;
  private epoch: number;
  private request: AbortController | null = null;
  private attempt: { body: Body; epoch: number; dispatched: boolean } | null = null;
  constructor(
    readonly transport: ApiTransport,
    private readonly session: DevelopmentSession,
    private readonly uuid: () => string,
    private readonly invalidate: () => void,
    private readonly refresh: () => Promise<void>,
    private readonly now = Date.now,
  ) {
    this.epoch = session.epoch();
    session.subscribe(() => {
      if (this.epoch !== session.epoch()) {
        this.epoch = session.epoch();
        this.clear();
      }
    });
  }
  snapshot = () => this.view;
  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  };
  private patch(value: Partial<ReturnType<typeof empty>>) {
    this.view = { ...this.view, ...value };
    for (const fn of this.listeners) fn();
  }
  private authenticated() {
    return (
      this.session.snapshot().mode === 'connected' &&
      this.session.snapshot().status === 'authenticated' &&
      this.session.credential() !== null
    );
  }
  clear = () => {
    this.generation++;
    this.request?.abort();
    this.request = null;
    this.attempt = null;
    this.view = empty();
    this.patch({});
  };
  leave = () => {
    this.generation++;
    this.request?.abort();
    this.request = null;
    if (this.attempt?.dispatched)
      this.patch({
        phase: this.view.phase === 'completed' ? 'completed' : 'unknown_outcome',
        challenge: null,
      });
    else this.clear();
  };
  select = (domain: Target['domain'], id: string) => {
    if (!this.authenticated()) return;
    const target = { domain, target_id: asUUID(id) };
    if (this.view.target && matches(this.view.target, target)) return;
    // A dispatched unknown operation must remain available under its exact target.
    // Switching requires leaving/re-entering after reading authoritative state.
    if (this.attempt?.dispatched && this.view.phase !== 'completed') return;
    this.clear();
    this.patch({ target });
  };
  cancel = () => {
    if (this.attempt?.dispatched) return;
    const target = this.view.target;
    this.clear();
    this.patch({ target });
  };
  private async task(
    work: (signal: AbortSignal, valid: () => boolean) => Promise<void>,
    execute = false,
  ) {
    if (!this.authenticated() || this.request) return;
    const controller = new AbortController(),
      generation = ++this.generation,
      epoch = this.session.epoch();
    this.request = controller;
    const valid = () => generation === this.generation && epoch === this.session.epoch();
    try {
      await work(controller.signal, valid);
    } catch (raw) {
      if (valid()) {
        const error = safeError(raw);
        const phase: Phase =
          error instanceof ErasureHTTPError
            ? error.code === 'target_busy'
              ? 'target_busy'
              : error.code === 'confirmation_expired'
                ? 'expired'
                : 'stale'
            : execute && (!error.status || error.status >= 500)
              ? 'unknown_outcome'
              : 'failed';
        if (execute && error.status && error.status < 500 && error.kind !== 'protocol')
          this.attempt = null;
        this.patch({
          phase,
          challenge: null,
          error:
            phase === 'unknown_outcome'
              ? '删除结果未知，请保留原 key 并安全重放；不会自动发送新的删除。'
              : error.message,
        });
      }
    } finally {
      if (valid()) this.request = null;
    }
  }
  prepare = async () => {
    const target = this.view.target;
    if (!target || this.request || this.attempt?.dispatched) return;
    this.patch({ phase: 'preparing', challenge: null, error: null });
    await this.task(async (signal, valid) => {
      const { data } = await this.transport.client.POST('/api/v1/lifecycle-erasures/prepare', {
        body: target,
        signal,
      });
      check(data && matches(data as Target, target));
      counts(data.counts);
      check(
        data.memory_policy === 'delete_exact_structured_scope' &&
          typeof data.scope_notice === 'string' &&
          data.scope_notice.length <= 512,
      );
      check(
        Number.isFinite(Date.parse(data.expires_at)) && Date.parse(data.expires_at) > this.now(),
      );
      asUUID(data.confirmation_id);
      if (!valid()) return;
      this.attempt = {
        body: Object.freeze({
          ...target,
          confirmation_id: data.confirmation_id,
          operation_key: asUUIDv4(this.uuid()),
        }),
        epoch: this.session.epoch(),
        dispatched: false,
      };
      this.patch({ phase: 'awaiting_confirmation', challenge: data });
    });
  };
  confirm = async () => {
    if (this.view.phase !== 'awaiting_confirmation' || !this.view.challenge) return;
    if (Date.parse(this.view.challenge.expires_at) <= this.now()) {
      this.cancel();
      this.patch({ phase: 'expired' });
      return;
    }
    await this.execute();
  };
  retry = async () => {
    if (this.view.phase === 'unknown_outcome' || this.view.phase === 'completed')
      await this.execute();
  };
  refreshBusy = () => {
    if (this.view.phase === 'target_busy') {
      this.attempt = null;
      this.patch({ phase: 'idle', error: null });
    }
  };
  private async execute() {
    const attempt = this.attempt,
      target = this.view.target;
    if (!attempt || !target || this.request || attempt.epoch !== this.session.epoch()) return;
    attempt.dispatched = true;
    this.invalidate();
    this.patch({ phase: 'executing', challenge: null, error: null, refresh: 'idle' });
    await this.task(async (signal, valid) => {
      const { data } = await this.transport.client.POST('/api/v1/lifecycle-erasures/execute', {
        body: attempt.body,
        signal,
      });
      check(
        data &&
          matches(data as Target, target) &&
          data.confirmation_id === attempt.body.confirmation_id &&
          data.status === 'deleted' &&
          data.primary_store_only === true,
      );
      counts(data.counts);
      asUUID(data.receipt_id);
      check(Number.isFinite(Date.parse(data.performed_at)));
      if (!valid()) return;
      this.patch({ receipt: data });
      const { data: receipt } = await this.transport.client.GET(
        '/api/v1/lifecycle-erasures/receipts/{receipt_id}',
        { params: { path: { receipt_id: asUUID(data.receipt_id) } }, signal },
      );
      check(
        receipt &&
          matches(receipt as Target, data as Target) &&
          receipt.confirmation_id === data.confirmation_id &&
          receipt.receipt_id === data.receipt_id &&
          receipt.status === data.status &&
          receipt.primary_store_only === data.primary_store_only &&
          receipt.performed_at === data.performed_at,
      );
      counts(receipt.counts);
      check([...countKeys].every((key) => receipt.counts[key] === data.counts[key]));
      if (!valid()) return;
      this.patch({ phase: 'completed', receipt });
      try {
        if (target.domain === 'person')
          await this.transport.client.GET('/api/v1/persons/{person_id}', {
            params: { path: { person_id: asUUID(target.target_id) } },
            signal,
          });
        else
          await this.transport.client.GET('/api/v1/relationships/{relationship_id}', {
            params: { path: { relationship_id: asUUID(target.target_id) } },
            signal,
          });
        throw new ApiError('protocol');
      } catch (error) {
        if (!(error instanceof ApiError && error.status === 404)) {
          if (valid()) this.patch({ refresh: 'failed' });
          return;
        }
      }
      try {
        await this.refresh();
        if (valid()) this.patch({ refresh: 'verified' });
      } catch {
        if (valid())
          this.patch({ refresh: 'failed', error: '正式回执已确认删除；请重新读取服务器资料。' });
      }
    }, true);
  }
}
