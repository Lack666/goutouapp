import type { components, UUID } from '../api/generated/client';
import { ApiTransport } from '../api/transport';
import { ApiError, safeError } from '../api/errors';
import { MemoryHTTPError } from '../api/memoryErrors';
import { asUUID, asUUIDv4 } from '../api/uuid';
import {
  memoryCheck,
  memoryControlView,
  memoryRecordView,
  memoryListView,
  memoryUndoView,
  memoryChallengeView,
  memoryReceiptView,
} from '../api/memoryAdapter';
import type { DevelopmentSession } from '../session/developmentSession';
import type {
  ConnectedMemoryView,
  MemoryScope,
  MemoryAction,
  ConnectedMemoryReceipt,
} from '../contracts/connectedMemory';

export const MEMORY_WINDOW_LIMIT = 200;
export const MEMORY_RESTART_NOTICE =
  '操作恢复信息仅保留在本次会话内。重启后丢失原操作标识，不能自动安全重试未确认的操作；请读取服务器权威状态或查询已知回执。记录消失本身不能证明操作成功。';
const ownerScope: MemoryScope = Object.freeze({ personId: null, relationshipId: null });
const empty = (): ConnectedMemoryView => ({
  scope: ownerScope,
  control: null,
  items: [],
  cursor: null,
  detail: null,
  undo: null,
  challenge: null,
  receipt: null,
  allConsentChoice: null,
  retention: '',
  historicalNotice: '',
  phase: 'idle',
  status: 'idle',
  error: null,
  feedback: null,
  canRetry: false,
});
type Attempt = Readonly<{
  action: MemoryAction;
  key: string;
  targetId: UUID | null;
  scope: MemoryScope;
  operationId: UUID | null;
  confirmationId: UUID | null;
}>;
type Apply = (value: Partial<ConnectedMemoryView>) => void;
export class MemoryController {
  private view = empty();
  private readonly listeners = new Set<() => void>();
  private generation = 0;
  private epoch: number;
  private request: AbortController | null = null;
  private attempt: Attempt | null = null;
  constructor(
    readonly transport: ApiTransport,
    private readonly session: DevelopmentSession,
    private readonly uuid: () => string,
    private readonly clock: () => number = Date.now,
  ) {
    this.epoch = session.epoch();
    session.subscribe(() => {
      if (this.epoch !== session.epoch()) {
        this.epoch = session.epoch();
        this.cancel();
        this.attempt = null;
        this.view = empty();
        this.patch({});
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
  private patch(value: Partial<ConnectedMemoryView>) {
    this.view = { ...this.view, ...value };
    for (const fn of this.listeners) fn();
  }
  private cancel() {
    this.generation++;
    this.request?.abort();
    this.request = null;
  }
  private authenticated() {
    return this.session.snapshot().status === 'authenticated' && this.session.credential() !== null;
  }
  private locked() {
    return this.view.phase === 'executing' || this.view.phase === 'unknown_outcome';
  }
  private matches(scope: MemoryScope) {
    return (
      (!this.view.scope.personId || scope.personId === this.view.scope.personId) &&
      (!this.view.scope.relationshipId || scope.relationshipId === this.view.scope.relationshipId)
    );
  }
  private async data<T>(promise: Promise<{ data?: T }>) {
    const response = await promise;
    memoryCheck(response.data !== undefined);
    return response.data;
  }
  private async task(
    work: (signal: AbortSignal, apply: Apply) => Promise<void>,
    failure?: (error: ApiError, apply: Apply) => void,
  ) {
    if (!this.authenticated() || this.request) return;
    const request = new AbortController();
    this.request = request;
    const generation = ++this.generation;
    const epoch = this.session.epoch();
    const valid = () => generation === this.generation && epoch === this.session.epoch();
    const apply: Apply = (value) => {
      if (valid()) this.patch(value);
    };
    apply({ status: 'loading', error: null });
    try {
      await work(request.signal, apply);
    } catch (error) {
      if (valid()) {
        const safe = safeError(error);
        apply({ status: 'error', error: safe.message });
        failure?.(safe, apply);
      }
    } finally {
      if (valid()) {
        this.request = null;
        if (this.view.status === 'loading') this.patch({ status: 'ready' });
      }
    }
  }
  private async read(signal: AbortSignal, apply: Apply, more = false) {
    const client = this.transport.client;
    const control = memoryControlView(
      await this.data(client.GET('/api/v1/memory/control', { signal })),
    );
    const page = memoryListView(
      await this.data(
        client.GET('/api/v1/memories', {
          signal,
          params: {
            query: {
              limit: 50,
              person_id: this.view.scope.personId ?? undefined,
              relationship_id: this.view.scope.relationshipId ?? undefined,
              cursor: more ? (this.view.cursor ?? undefined) : undefined,
            },
          },
        }),
      ),
    );
    memoryCheck(page.items.every((item) => this.matches(item)));
    const undo = memoryUndoView(
      await this.data(client.GET('/api/v1/memory/undo/preview', { signal })),
    );
    const items = [
      ...new Map(
        [...(more ? this.view.items : []), ...page.items].map((item) => [item.id, item]),
      ).values(),
    ].slice(0, MEMORY_WINDOW_LIMIT);
    apply({ control, ...page, items, undo, status: 'ready' });
  }
  open = async (
    person: string | null = this.view.scope.personId,
    relationship: string | null = this.view.scope.relationshipId,
  ) => {
    if (this.locked()) return;
    this.cancel();
    this.attempt = null;
    const prior = this.view;
    this.view = empty();
    try {
      if (relationship && !person) throw new ApiError('invalid_scope');
      const scope = Object.freeze({
        personId: person === null ? null : asUUID(person),
        relationshipId: relationship === null ? null : asUUID(relationship),
      });
      this.patch({ scope, allConsentChoice: prior.allConsentChoice });
    } catch (error) {
      this.patch({ status: 'error', error: safeError(error).message });
      return;
    }
    await this.refresh();
  };
  refresh = async (more = false) => {
    if (
      this.request ||
      !this.authenticated() ||
      (more && (!this.view.cursor || this.view.items.length >= MEMORY_WINDOW_LIMIT))
    )
      return;
    if (this.view.phase === 'awaiting_user_confirmation' || this.view.phase === 'expired') {
      this.attempt = null;
      this.patch({ phase: 'idle', challenge: null, canRetry: false });
    }
    this.patch({
      detail: null,
      control: null,
      ...(more ? {} : { items: [], cursor: null, undo: null }),
    });
    await this.task((signal, apply) => this.read(signal, apply, more));
  };
  inspect = async (id: string) => {
    if (this.request) return;
    this.patch({ detail: null });
    await this.task(async (signal, apply) => {
      const record = memoryRecordView(
        await this.data(
          this.transport.client.GET('/api/v1/memories/{memory_id}', {
            params: { path: { memory_id: asUUID(id) } },
            signal,
          }),
        ),
      );
      memoryCheck(this.matches(record));
      apply({ detail: record });
    });
  };
  changeControl = async (action: 'grant' | 'revoke' | 'pause' | 'resume') => {
    if (this.request || this.locked()) return;
    this.patch({ control: null, challenge: null, phase: 'idle', feedback: null, canRetry: false });
    this.attempt = null;
    await this.task(async (signal, apply) => {
      let uncertain = false;
      try {
        const client = this.transport.client;
        const dto =
          action === 'grant' || action === 'revoke'
            ? await this.data(
                client.POST('/api/v1/memory/consent', {
                  body: { enabled: action === 'grant' },
                  signal,
                }),
              )
            : action === 'pause'
              ? await this.data(client.POST('/api/v1/memory/pause', { signal }))
              : await this.data(client.POST('/api/v1/memory/resume', { signal }));
        memoryControlView(dto);
      } catch (error) {
        if (!this.authenticated()) throw error;
        uncertain = true;
      }
      const control = memoryControlView(
        await this.data(this.transport.client.GET('/api/v1/memory/control', { signal })),
      );
      apply({
        control,
        feedback: uncertain
          ? '控制请求结果未确认；已重新读取服务器当前权威状态。'
          : '已读取服务器当前权威状态。',
      });
    });
  };
  chooseAllConsent = (choice: boolean) => {
    if (this.request || this.locked() || choice === this.view.allConsentChoice) return;
    this.attempt = null;
    this.patch({
      allConsentChoice: choice,
      challenge: null,
      phase: 'idle',
      receipt: null,
      canRetry: false,
    });
  };
  armUndo = async () => {
    if (this.request || this.locked()) return;
    this.attempt = null;
    this.patch({
      undo: null,
      challenge: null,
      receipt: null,
      phase: 'preparing',
      feedback: null,
      canRetry: false,
    });
    await this.task(
      async (signal, apply) => {
        const undo = memoryUndoView(
          await this.data(this.transport.client.GET('/api/v1/memory/undo/preview', { signal })),
        );
        if (!undo) {
          apply({ phase: 'idle', feedback: '当前没有可撤销的操作。' });
          return;
        }
        if (!this.matches(undo)) {
          apply({
            undo,
            phase: 'stale_or_conflict',
            feedback: '最新操作属于其它范围。请显式选择其范围；不会撤销更早的操作。',
          });
          return;
        }
        apply({ undo, phase: 'awaiting_user_confirmation' });
      },
      (_error, apply) => apply({ phase: 'failed' }),
    );
  };
  prepare = async (action: Exclude<MemoryAction, 'undo'>, recordId?: string) => {
    if (this.request || this.locked()) return;
    this.attempt = null;
    this.patch({
      challenge: null,
      receipt: null,
      phase: 'preparing',
      feedback: null,
      canRetry: false,
    });
    await this.task(
      async (signal, apply) => {
        const client = this.transport.client;
        let dto: components['schemas']['MemoryConfirmationChallenge'];
        let target: UUID | null = null;
        let scope: MemoryScope = ownerScope;
        let revoke = false;
        if (action === 'delete_one') {
          const record =
            this.view.detail?.id === recordId
              ? this.view.detail
              : this.view.items.find((item) => item.id === recordId);
          if (!record || !this.matches(record)) throw new ApiError('invalid_scope');
          target = record.id;
          scope = { personId: record.personId, relationshipId: record.relationshipId };
          dto = await this.data(
            client.POST('/api/v1/memory/deletions/one/prepare', {
              signal,
              body: {
                memory_id: target,
                person_id: scope.personId,
                relationship_id: scope.relationshipId,
              },
            }),
          );
        } else if (action === 'delete_person') {
          if (!this.view.scope.personId) throw new ApiError('invalid_scope');
          target = this.view.scope.personId;
          scope = { personId: target, relationshipId: null };
          dto = await this.data(
            client.POST('/api/v1/memory/deletions/person/prepare', {
              signal,
              body: { person_id: target },
            }),
          );
        } else {
          if (this.view.allConsentChoice === null || this.view.scope.personId)
            throw new ApiError('validation');
          revoke = this.view.allConsentChoice;
          dto = await this.data(
            client.POST('/api/v1/memory/deletions/all/prepare', {
              signal,
              body: { revoke_consent_after_delete: revoke },
            }),
          );
        }
        const challenge = memoryChallengeView(dto);
        memoryCheck(
          challenge.action === action &&
            challenge.targetId === target &&
            challenge.personId === scope.personId &&
            challenge.relationshipId === scope.relationshipId &&
            challenge.revokeConsent === revoke,
        );
        apply({
          challenge,
          phase:
            Date.parse(challenge.expiresAt) <= this.clock()
              ? 'expired'
              : 'awaiting_user_confirmation',
        });
      },
      (_error, apply) => apply({ phase: 'failed' }),
    );
  };
  tick = () => {
    if (
      this.view.phase === 'awaiting_user_confirmation' &&
      this.view.challenge &&
      Date.parse(this.view.challenge.expiresAt) <= this.clock()
    )
      this.patch({ phase: 'expired', feedback: '服务器确认已过期，请重新准备并确认。' });
  };
  execute = async () => {
    this.tick();
    if (this.request || this.view.phase !== 'awaiting_user_confirmation') return;
    try {
      const challenge = this.view.challenge;
      const undo = this.view.undo;
      if (!challenge && (!undo || !this.matches(undo))) throw new ApiError('invalid_scope');
      this.attempt = Object.freeze({
        action: challenge?.action ?? 'undo',
        key: `memory-${asUUIDv4(this.uuid())}`,
        targetId: challenge ? challenge.targetId : undo!.memoryId,
        scope: Object.freeze({
          personId: challenge ? challenge.personId : undo!.personId,
          relationshipId: challenge ? challenge.relationshipId : undo!.relationshipId,
        }),
        confirmationId: challenge?.id ?? null,
        operationId: challenge ? null : undo!.operationId,
      });
      await this.sendAttempt();
    } catch (error) {
      this.patch({ phase: 'failed', error: safeError(error).message });
    }
  };
  retry = async () => {
    if (this.attempt && ['unknown_outcome', 'completed'].includes(this.view.phase) && !this.request)
      await this.sendAttempt();
  };
  private correlate(
    dto: components['schemas']['MemoryMutationReceipt'],
    receipt: ConnectedMemoryReceipt,
    attempt: Attempt,
  ) {
    memoryCheck(
      dto.operation_key === attempt.key &&
        receipt.action === attempt.action &&
        receipt.targetId === attempt.targetId &&
        receipt.personId === attempt.scope.personId &&
        receipt.relationshipId === attempt.scope.relationshipId,
    );
    if (attempt.action === 'undo') memoryCheck(receipt.undoneMemoryId === attempt.targetId);
  }
  private async sendAttempt() {
    const attempt = this.attempt;
    if (!attempt || !this.authenticated()) return;
    const confirmed = this.view.phase === 'completed' ? this.view.receipt : null;
    this.patch({ phase: 'executing', error: null, feedback: null, canRetry: false });
    await this.task(
      async (signal, apply) => {
        const client = this.transport.client;
        const dto =
          attempt.action === 'undo'
            ? await this.data(
                client.POST('/api/v1/memory/undo', {
                  signal,
                  body: { expected_operation_id: attempt.operationId!, operation_key: attempt.key },
                }),
              )
            : await this.data(
                client.POST('/api/v1/memory/deletions/{confirmation_id}/execute', {
                  signal,
                  params: { path: { confirmation_id: attempt.confirmationId! } },
                  body: { operation_key: attempt.key },
                }),
              );
        const receipt = memoryReceiptView(dto);
        this.correlate(dto, receipt, attempt);
        apply({
          receipt,
          phase: 'completed',
          challenge: null,
          detail: null,
          canRetry: true,
          feedback: '已收到正式服务器回执。',
        });
        try {
          await this.read(signal, apply);
        } catch (error) {
          apply({
            status: 'error',
            control: null,
            items: [],
            cursor: null,
            undo: null,
            error: `操作回执已确认，刷新失败：${safeError(error).message}`,
          });
        }
      },
      (error, apply) => {
        if (confirmed) {
          apply({
            phase: 'completed',
            receipt: confirmed,
            canRetry: true,
            feedback: '本次重放响应未确认；此前正式服务器回执仍可查看。',
          });
          return;
        }
        if (error.status && error.status >= 400 && error.status < 500) {
          this.attempt = null;
          apply({
            phase:
              error instanceof MemoryHTTPError && error.code === 'confirmation_expired'
                ? 'expired'
                : 'stale_or_conflict',
            challenge: null,
            undo: null,
            canRetry: false,
          });
        } else {
          apply({
            phase: 'unknown_outcome',
            receipt: null,
            canRetry: true,
            feedback:
              '未确认操作结果。请重新读取权威状态；重试只会使用本次原始标识和原始目标，不会自动执行其它操作。',
          });
        }
      },
    );
  }
  inspectReceipt = async (id: string) => {
    if (this.request) return;
    // A failed lookup does not invalidate a previously verified receipt.
    await this.task(async (signal, apply) => {
      const dto = await this.data(
        this.transport.client.GET('/api/v1/memory/mutations/{mutation_id}', {
          signal,
          params: { path: { mutation_id: asUUID(id) } },
        }),
      );
      const receipt = memoryReceiptView(dto);
      if (this.attempt && this.view.phase === 'unknown_outcome') {
        this.correlate(dto, receipt, this.attempt);
        apply({ receipt, phase: 'completed', canRetry: true });
        await this.read(signal, apply);
      } else {
        memoryCheck(this.matches(receipt));
        if (this.attempt && dto.operation_key !== this.attempt.key) {
          this.attempt = null;
          apply({ phase: 'idle', canRetry: false });
        }
        apply({ receipt });
      }
    });
  };
  pause = () => {
    const phase = this.view.phase;
    this.cancel();
    const uncertain = phase === 'executing' || phase === 'unknown_outcome';
    if (!uncertain && phase !== 'completed') this.attempt = null;
    this.patch({
      control: null,
      items: [],
      cursor: null,
      detail: null,
      undo: null,
      challenge: null,
      retention: '',
      historicalNotice: '',
      status: 'idle',
      phase:
        this.view.receipt && this.attempt
          ? 'completed'
          : uncertain
            ? 'unknown_outcome'
            : phase === 'completed'
              ? 'completed'
              : 'idle',
      canRetry: this.attempt !== null,
      feedback: uncertain ? '等待已停止，结果可能未知；没有自动重试。' : null,
    });
  };
  resume = async () => {
    if (this.authenticated()) await this.refresh();
  };
}
