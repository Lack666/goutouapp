import type { components, UUID } from '../api/generated/client';
import { ApiTransport } from '../api/transport';
import { ApiError, safeError } from '../api/errors';
import { ErasureHTTPError } from '../api/erasureErrors';
import { asUUID, asUUIDv4 } from '../api/uuid';
import {
  check,
  targetView,
  sameTarget,
  challengeView,
  receiptView,
  datasetView,
  type ErasureTarget,
  type ErasureChallenge,
  type ErasureReceipt,
  type Dataset,
} from '../api/erasureAdapter';
import type { DevelopmentSession } from '../session/developmentSession';

export const ERASURE_RESTART_NOTICE =
  '删除操作标识仅保留在本次会话。重启、退出或切换身份后不会自动执行旧删除；请重新读取服务器状态。记录消失不能证明原操作成功，丢失原 key 的结果可能无法完全确认。';
export const ERASURE_SCOPE_NOTICE =
  '仅删除指定主库历史。Dataset 删除移除正式 RelationshipMessage 和对应说话人记录，保留必要 Tombstone / 去重 / 回执元数据；同关系相同 Dataset 再次 Finalize 可能返回 dataset_deleted。Conversation 删除仅移除该 AI 对话消息并保留运行与操作标识。其他 Dataset、Relationship、Conversation 不受影响；Memory 不会自动删除，请使用独立 Memory Controls。旧备份可能仍含历史内容，恢复前须受控核对。';
export type ErasurePhase =
  | 'idle'
  | 'preparing'
  | 'awaiting_confirmation'
  | 'executing'
  | 'completed'
  | 'expired'
  | 'stale'
  | 'target_busy'
  | 'failed'
  | 'unknown_outcome';
type Body = Readonly<components['schemas']['ErasureExecute']>;
type Attempt = {
  readonly owner: UUID;
  readonly epoch: number;
  readonly body: Body;
  dispatched: boolean;
  receipt: ErasureReceipt | null;
  phase: ErasurePhase;
};
export interface ErasureView {
  phase: ErasurePhase;
  target: ErasureTarget | null;
  challenge: ErasureChallenge | null;
  receipt: ErasureReceipt | null;
  error: string | null;
  refresh: 'idle' | 'verified' | 'failed';
  datasets: readonly Dataset[];
  cursor: string | null;
  relationship: UUID | null;
  discovery: 'idle' | 'loading' | 'ready' | 'error';
}
const empty = (): ErasureView => ({
  phase: 'idle',
  target: null,
  challenge: null,
  receipt: null,
  error: null,
  refresh: 'idle',
  datasets: [],
  cursor: null,
  relationship: null,
  discovery: 'idle',
});
const identity = (t: ErasureTarget) => `${t.domain}:${t.target_id}:${t.relationship_id ?? ''}`;

export class ErasureController {
  private view = empty();
  private listeners = new Set<() => void>();
  private generation = 0;
  private epoch: number;
  private request: AbortController | null = null;
  private attempts = new Map<string, Attempt>();
  constructor(
    readonly transport: ApiTransport,
    private readonly session: DevelopmentSession,
    private readonly uuid: () => string,
    private readonly invalidate: (target: ErasureTarget) => void,
    private readonly refreshed: (target: ErasureTarget) => Promise<void>,
    private readonly now = Date.now,
  ) {
    this.epoch = session.epoch();
    session.subscribe(() => {
      if (this.epoch !== session.epoch()) {
        this.epoch = session.epoch();
        this.leave();
        this.attempts.clear();
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
  private patch(value: Partial<ErasureView>) {
    this.view = { ...this.view, ...value };
    for (const fn of this.listeners) fn();
  }
  private owner(): UUID | null {
    if (
      this.session.snapshot().mode !== 'connected' ||
      this.session.snapshot().status !== 'authenticated'
    )
      return null;
    const token = this.session.credential();
    if (!token) return null;
    try {
      return asUUID(
        JSON.parse(atob(token.split('.')[1]!.replace(/-/g, '+').replace(/_/g, '/'))).sub,
      );
    } catch {
      return null;
    }
  }
  private attempt() {
    return this.view.target ? this.attempts.get(identity(this.view.target)) : undefined;
  }
  private abort() {
    this.generation++;
    this.request?.abort();
    this.request = null;
  }
  leave = () => {
    const attempt = this.attempt();
    if (attempt && this.view.phase === 'executing') attempt.phase = 'unknown_outcome';
    if (attempt && !attempt.dispatched && this.view.target)
      this.attempts.delete(identity(this.view.target));
    this.abort();
    this.view = empty();
    this.patch({});
  };
  pause = () => {
    if (this.view.phase === 'executing') {
      const attempt = this.attempt();
      if (attempt) attempt.phase = 'unknown_outcome';
      this.abort();
      this.patch({
        phase: 'unknown_outcome',
        challenge: null,
        error: '已停止等待；删除结果未知。请查询回执或安全重放原操作。',
      });
    } else if (this.view.phase === 'awaiting_confirmation' || this.view.phase === 'preparing')
      this.cancel();
  };
  select = (target: ErasureTarget) => {
    if (!this.owner()) return;
    const normalized = targetView(target);
    if (this.view.target && sameTarget(this.view.target, normalized)) return;
    const datasets = this.view.datasets,
      cursor = this.view.cursor,
      relationship =
        this.view.relationship ??
        (normalized.domain === 'dataset' ? (normalized.relationship_id ?? null) : null);
    this.leave();
    const attempt = this.attempts.get(identity(normalized));
    this.patch({
      target: normalized,
      datasets,
      cursor,
      relationship,
      discovery: relationship ? 'ready' : 'idle',
      phase: attempt?.phase ?? 'idle',
      receipt: attempt?.receipt ?? null,
    });
  };
  openConversation = async (value: string, expectedRelationship: string | null) => {
    this.leave();
    const retained = [...this.attempts.values()].find(
      (attempt) =>
        attempt.dispatched &&
        attempt.body.domain === 'conversation' &&
        attempt.body.target_id === value &&
        attempt.owner === this.owner() &&
        attempt.epoch === this.session.epoch() &&
        (expectedRelationship === null || attempt.body.relationship_id === expectedRelationship),
    );
    if (retained) {
      this.select(retained.body);
      return;
    }
    await this.task(async (signal, valid) => {
      const id = asUUID(value);
      const { data } = await this.transport.client.GET('/api/v1/conversations/{conversation_id}', {
        params: { path: { conversation_id: id } },
        signal,
      });
      check(data && data.id === id);
      if (expectedRelationship !== null)
        check(data.relationship_id === asUUID(expectedRelationship));
      if (valid())
        this.select({
          domain: 'conversation',
          target_id: id,
          relationship_id: data.relationship_id,
        });
    });
  };
  recoverable = (target: ErasureTarget) =>
    [...this.attempts.values()].some(
      (attempt) =>
        attempt.dispatched &&
        sameTarget(attempt.body, target) &&
        attempt.owner === this.owner() &&
        attempt.epoch === this.session.epoch(),
    );
  cancel = () => {
    if (this.view.phase === 'executing' || this.view.phase === 'unknown_outcome') return;
    if (this.view.target) this.attempts.delete(identity(this.view.target));
    this.abort();
    this.patch({ phase: 'idle', challenge: null, error: null });
  };
  private async task(
    work: (signal: AbortSignal, valid: () => boolean) => Promise<void>,
    executing = false,
  ) {
    if (!this.owner() || this.request) return;
    const request = new AbortController(),
      generation = ++this.generation,
      epoch = this.session.epoch();
    this.request = request;
    const valid = () => generation === this.generation && epoch === this.session.epoch();
    try {
      await work(request.signal, valid);
    } catch (raw) {
      if (valid()) {
        const error = safeError(raw);
        let phase: ErasurePhase = executing ? 'unknown_outcome' : 'failed';
        if (error instanceof ErasureHTTPError) {
          phase =
            error.code === 'target_busy'
              ? 'target_busy'
              : error.code === 'confirmation_expired'
                ? 'expired'
                : 'stale';
        } else if (error.status && error.status < 500) phase = 'failed';
        const attempt = this.attempt();
        if (attempt) attempt.phase = phase;
        this.patch({
          phase,
          challenge: null,
          error:
            phase === 'unknown_outcome'
              ? '删除结果未知；请保留原操作，查询已知回执或使用同 key 重放。'
              : error.message,
          ...(this.view.discovery === 'loading' ? { discovery: 'error' as const } : {}),
        });
      }
    } finally {
      if (valid()) this.request = null;
    }
  }
  discover = async (value: string, more = false) => {
    if (!this.owner() || this.request) return;
    const relationship = asUUID(value);
    if (this.view.phase === 'awaiting_confirmation') this.cancel();
    if (!more && this.view.relationship !== relationship) this.leave();
    if (more && (!this.view.cursor || this.view.datasets.length >= 200)) return;
    this.patch({
      relationship,
      discovery: 'loading',
      error: null,
      ...(more ? {} : { datasets: [], cursor: null }),
    });
    await this.task(async (signal, valid) => {
      const { data } = await this.transport.client.GET(
        '/api/v1/relationships/{relationship_id}/datasets',
        {
          params: {
            path: { relationship_id: relationship },
            query: { limit: 30, ...(more ? { cursor: this.view.cursor! } : {}) },
          },
          signal,
        },
      );
      check(data && Array.isArray(data.items) && data.items.length <= 30);
      check(
        data.next_cursor === null ||
          (typeof data.next_cursor === 'string' &&
            data.next_cursor.length > 0 &&
            data.next_cursor.length <= 512),
      );
      const items = data.items.map((dto) => datasetView(dto, relationship));
      if (valid())
        this.patch({
          datasets: [
            ...new Map(
              [...(more ? this.view.datasets : []), ...items].map((row) => [
                row.dataset_job_id,
                row,
              ]),
            ).values(),
          ].slice(0, 200),
          cursor: data.next_cursor,
          discovery: 'ready',
        });
    });
  };
  prepare = async () => {
    const target = this.view.target;
    if (
      !target ||
      this.request ||
      ['executing', 'unknown_outcome', 'completed', 'target_busy'].includes(this.view.phase)
    )
      return;
    this.cancel();
    this.patch({ phase: 'preparing', receipt: null, refresh: 'idle' });
    await this.task(async (signal, valid) => {
      const { data } = await this.transport.client.POST('/api/v1/erasures/prepare', {
        body: target,
        signal,
      });
      check(data);
      const challenge = challengeView(data, target);
      check(Date.parse(challenge.expires_at) > this.now());
      if (!valid()) return;
      if (this.attempts.size >= 20) {
        const oldest = [...this.attempts].find(([, a]) => a.phase === 'completed');
        if (oldest) this.attempts.delete(oldest[0]);
        else throw new ApiError('unavailable');
      }
      const body: Body = Object.freeze({
        ...target,
        confirmation_id: challenge.confirmation_id,
        operation_key: asUUIDv4(this.uuid()),
      });
      this.attempts.set(identity(target), {
        owner: this.owner()!,
        epoch: this.session.epoch(),
        body,
        dispatched: false,
        receipt: null,
        phase: 'awaiting_confirmation',
      });
      this.patch({ phase: 'awaiting_confirmation', challenge });
    });
  };
  confirm = async () => {
    const challenge = this.view.challenge;
    if (this.view.phase !== 'awaiting_confirmation' || !challenge || this.request) return;
    if (Date.parse(challenge.expires_at) <= this.now()) {
      this.cancel();
      this.patch({ phase: 'expired', error: '删除确认已过期，请重新准备。' });
      return;
    }
    await this.execute(false);
  };
  retry = async () => {
    if (!['unknown_outcome', 'completed'].includes(this.view.phase)) return;
    await this.execute(true);
  };
  inspect = async () => {
    if (!this.attempt()?.receipt || this.request) return;
    await this.execute(true, true);
  };
  refreshBusy = () => {
    if (this.view.phase === 'target_busy')
      this.patch({ phase: 'idle', error: '请主动重新准备，由服务器重新核对运行状态。' });
  };
  private async execute(replay: boolean, inspectOnly = false) {
    const attempt = this.attempt(),
      target = this.view.target;
    if (
      !attempt ||
      !target ||
      this.request ||
      attempt.epoch !== this.session.epoch() ||
      attempt.owner !== this.owner()
    )
      return;
    if (replay && !attempt.dispatched) return;
    attempt.dispatched = true;
    attempt.phase = 'executing';
    this.patch({ phase: 'executing', error: null, challenge: null, refresh: 'idle' });
    this.invalidate(target);
    await this.task(async (signal, valid) => {
      let result = attempt.receipt;
      if (!inspectOnly) {
        const { data } = await this.transport.client.POST('/api/v1/erasures/execute', {
          body: attempt.body,
          signal,
        });
        check(data);
        result = receiptView(data, target, attempt.body.confirmation_id);
        if (!valid()) return;
        attempt.receipt = result;
        this.patch({ receipt: result });
      }
      check(result);
      const { data } = await this.transport.client.GET('/api/v1/erasures/receipts/{receipt_id}', {
        params: { path: { receipt_id: result.receipt_id } },
        signal,
      });
      check(data);
      const receipt = receiptView(data, target, attempt.body.confirmation_id);
      check(JSON.stringify(receipt) === JSON.stringify(result));
      if (!valid()) return;
      attempt.receipt = receipt;
      // Receipt establishes deletion; refresh failure stays distinct from unknown execution.
      attempt.phase = 'completed';
      this.patch({ phase: 'completed', receipt });
      try {
        if (target.domain === 'conversation') {
          try {
            await this.transport.client.GET('/api/v1/conversations/{conversation_id}', {
              params: { path: { conversation_id: target.target_id } },
              signal,
            });
            throw new ApiError('protocol');
          } catch (error) {
            if (!(error instanceof ApiError && error.status === 404)) throw error;
          }
        }
        if (valid()) await this.refreshed(target);
        if (valid() && target.domain === 'dataset' && target.relationship_id) {
          const { data: page } = await this.transport.client.GET(
            '/api/v1/relationships/{relationship_id}/datasets',
            {
              params: { path: { relationship_id: target.relationship_id }, query: { limit: 30 } },
              signal,
            },
          );
          check(page && Array.isArray(page.items) && page.items.length <= 30);
          const datasets = page.items.map((row) => datasetView(row, target.relationship_id!));
          const erased = datasets.find((row) => row.dataset_job_id === target.target_id);
          check(!erased || (!erased.deletable && erased.current_message_count === 0));
          if (valid()) this.patch({ datasets, cursor: page.next_cursor, discovery: 'ready' });
        }
        if (valid()) this.patch({ refresh: 'verified' });
      } catch {
        if (valid())
          this.patch({
            refresh: 'failed',
            error: '正式回执已确认删除；历史刷新失败，请主动重新读取。',
          });
      }
    }, true);
  }
}
