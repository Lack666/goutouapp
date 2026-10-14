import type { components, UUID } from '../api/generated/client';
import type { AgentEvent, MemoryStatus, ProgressStatus } from '../api/agentEvents';
import { memoryStatuses } from '../api/agentEvents';
import { ApiError, safeError } from '../api/errors';
import { AgentApiError } from '../api/agentErrors';
import { ApiTransport } from '../api/transport';
import { asUUID, asUUIDv4, wireUUID } from '../api/uuid';
import { COMPOSER_LIMIT, type AgentChatMessageViewModel } from '../contracts/chat';
import type { DevelopmentSession } from '../session/developmentSession';

type Body = components['schemas']['CreateAgentRunRequest'];
type Message = components['schemas']['AgentMessagePublicResponse'];
export type ChatPhase =
  | 'idle'
  | 'submitting'
  | 'running'
  | 'committed'
  | 'completed'
  | 'failed'
  | 'running_unknown';
type Attempt = { conversationId: UUID; body: Readonly<Body>; phase: ChatPhase; runId: UUID | null };
export interface ConnectedChatView {
  conversationId: UUID | null;
  relationshipId: UUID | null;
  scope: 'idle' | 'loading' | 'ready' | 'error';
  messages: readonly AgentChatMessageViewModel[];
  history: 'idle' | 'loading' | 'ready' | 'error';
  cursor: string | null;
  historyError: string | null;
  phase: ChatPhase;
  progress: ProgressStatus | null;
  runId: UUID | null;
  operationKey: string | null;
  memoryStatus: MemoryStatus | null;
  warnings: readonly string[];
  error: string | null;
  errorKind: string | null;
}
const empty = (): ConnectedChatView => ({
  conversationId: null,
  relationshipId: null,
  scope: 'idle',
  messages: [],
  history: 'idle',
  cursor: null,
  historyError: null,
  phase: 'idle',
  progress: null,
  runId: null,
  operationKey: null,
  memoryStatus: null,
  warnings: [],
  error: null,
  errorKind: null,
});
const busy = (phase: ChatPhase) => ['submitting', 'running', 'committed'].includes(phase);
const subMillisecond = (value: string) =>
  Number((value.match(/\.(\d+)(?:Z|[+-])/i)?.[1] ?? '').padEnd(9, '0').slice(3, 9));
export class AgentChatController {
  private view = empty();
  private readonly listeners = new Set<() => void>();
  private readonly attempts = new Map<UUID, Attempt>();
  private readonly messages = new Map<UUID, Message>();
  private readonly finals = new Map<UUID, string>();
  private generation = 0;
  private epoch: number;
  private scopeRequest?: AbortController;
  private historyRequest?: AbortController;
  private runRequest?: AbortController;
  constructor(
    readonly transport: ApiTransport,
    private readonly session: DevelopmentSession,
    private readonly uuid: () => string,
    private readonly limit = 30,
  ) {
    this.epoch = session.epoch();
    session.subscribe(() => {
      if (this.epoch !== session.epoch()) {
        this.epoch = session.epoch();
        this.leave();
        this.attempts.clear();
        this.view = empty();
        this.emit();
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
  private emit() {
    for (const fn of this.listeners) fn();
  }
  private update(value: Partial<ConnectedChatView>) {
    this.view = { ...this.view, ...value };
    this.emit();
  }
  private valid(generation: number) {
    return (
      generation === this.generation &&
      this.epoch === this.session.epoch() &&
      this.session.snapshot().status === 'authenticated'
    );
  }
  private authenticated() {
    return (
      this.session.snapshot().mode === 'connected' &&
      this.session.snapshot().status === 'authenticated' &&
      this.session.credential() !== null
    );
  }
  leave = () => {
    const attempt = this.view.conversationId
      ? this.attempts.get(this.view.conversationId)
      : undefined;
    if (attempt && busy(attempt.phase)) attempt.phase = 'running_unknown';
    this.generation++;
    this.scopeRequest?.abort();
    this.historyRequest?.abort();
    this.runRequest?.abort();
    this.scopeRequest = undefined;
    this.historyRequest = undefined;
    this.runRequest = undefined;
    this.messages.clear();
    this.finals.clear();
    this.view = empty();
    this.emit();
  };
  pause = () => {
    this.historyRequest?.abort();
    this.historyRequest = undefined;
    if (this.view.history === 'loading')
      this.update({ history: 'error', historyError: '读取已暂停，请刷新历史。' });
    if (this.runRequest) {
      this.runRequest.abort();
      this.runRequest = undefined;
      const attempt = this.attempts.get(this.view.conversationId!);
      if (attempt) {
        attempt.phase = 'running_unknown';
        this.update({
          phase: attempt.phase,
          error: '已停止等待，无法确认该请求是否已完成。',
          errorKind: 'cancelled',
        });
      }
    }
  };
  invalidateConversation = (id: string) => {
    this.attempts.delete(asUUID(id));
    if (this.view.conversationId === id) this.leave();
  };
  async open(value: string, expectedRelationship: string | null = null) {
    this.leave();
    if (!this.authenticated()) {
      this.update({
        scope: 'error',
        error: new ApiError('unauthorized').message,
        errorKind: 'unauthorized',
      });
      return;
    }
    const generation = this.generation;
    const controller = new AbortController();
    this.scopeRequest = controller;
    this.update({ scope: 'loading' });
    try {
      const id = asUUID(value);
      const expected = expectedRelationship === null ? null : asUUID(expectedRelationship);
      const { data } = await this.transport.client.GET('/api/v1/conversations/{conversation_id}', {
        params: { path: { conversation_id: id } },
        signal: controller.signal,
      });
      if (!this.valid(generation) || controller.signal.aborted) return;
      if (!data || data.id !== id) throw new ApiError('protocol');
      const relationship = data.relationship_id === null ? null : wireUUID(data.relationship_id);
      if (expected !== null && expected !== relationship) throw new ApiError('invalid_scope');
      const attempt = this.attempts.get(id);
      this.update({
        scope: 'ready',
        conversationId: id,
        relationshipId: relationship,
        phase: attempt?.phase ?? 'idle',
        operationKey: attempt?.body.operation_key ?? null,
        runId: attempt?.runId ?? null,
        error:
          attempt?.phase === 'running_unknown'
            ? '无法确认该请求是否已完成。请查询历史或重试原操作。'
            : null,
      });
      await this.loadHistory();
    } catch (error) {
      if (this.valid(generation))
        this.update({
          scope: 'error',
          error: safeError(error).message,
          errorKind: safeError(error).kind,
        });
    } finally {
      if (this.scopeRequest === controller) this.scopeRequest = undefined;
    }
  }
  private presentMessages() {
    const rows: AgentChatMessageViewModel[] = [...this.messages.values()]
      .sort(
        (a, b) =>
          Date.parse(a.created_at) - Date.parse(b.created_at) ||
          subMillisecond(a.created_at) - subMillisecond(b.created_at) ||
          a.id.localeCompare(b.id),
      )
      .map((row) => ({
        id: row.id,
        role: row.role,
        text: row.content,
        timeLabel: row.created_at,
        source: 'server',
      }));
    for (const [id, text] of this.finals)
      if (!this.messages.has(id))
        rows.push({
          id,
          role: 'assistant',
          text,
          timeLabel: '已提交 · 等待历史时间',
          source: 'server',
        });
    this.update({ messages: rows });
  }
  async loadHistory(more = false) {
    const id = this.view.conversationId;
    if (
      !id ||
      this.view.scope !== 'ready' ||
      !this.authenticated() ||
      this.historyRequest ||
      (more && !this.view.cursor)
    )
      return;
    const generation = this.generation;
    const cursor = more ? this.view.cursor : null;
    const controller = new AbortController();
    this.historyRequest = controller;
    this.update({ history: 'loading', historyError: null });
    try {
      const { data } = await this.transport.client.GET(
        '/api/v1/conversations/{conversation_id}/messages',
        {
          params: {
            path: { conversation_id: id },
            query: { limit: this.limit, ...(cursor ? { cursor } : {}) },
          },
          signal: controller.signal,
        },
      );
      if (!this.valid(generation) || controller.signal.aborted) return;
      if (
        !data ||
        !Array.isArray(data.items) ||
        data.items.length > this.limit ||
        (data.next_cursor !== null &&
          (typeof data.next_cursor !== 'string' ||
            data.next_cursor.length > 512 ||
            data.next_cursor === cursor))
      )
        throw new ApiError('protocol');
      for (const row of data.items) {
        wireUUID(row.id);
        if (
          row.conversation_id !== id ||
          !['user', 'assistant'].includes(row.role) ||
          typeof row.content !== 'string' ||
          row.content.length > 100_000 ||
          !Number.isFinite(Date.parse(row.created_at))
        )
          throw new ApiError('protocol');
      }
      const merged = new Map(more ? this.messages : []);
      for (const row of data.items) merged.set(row.id, row);
      if (new Set([...merged.keys(), ...this.finals.keys()]).size > 1000)
        throw new ApiError('protocol');
      this.messages.clear();
      for (const [id, row] of merged) this.messages.set(id, row);
      this.presentMessages();
      this.update({ history: 'ready', cursor: data.next_cursor });
    } catch (error) {
      if (this.valid(generation) && !controller.signal.aborted)
        this.update({ history: 'error', historyError: safeError(error).message });
    } finally {
      if (this.historyRequest === controller) this.historyRequest = undefined;
    }
  }
  async send(text: string, mode: 'rest' | 'sse' = 'sse') {
    if (!this.authenticated()) {
      this.update({ error: new ApiError('unauthorized').message });
      return;
    }
    if (this.view.scope !== 'ready' || !this.view.conversationId || this.runRequest) return;
    if (this.view.messages.length >= 1000) {
      this.update({ error: '当前历史窗口已达上限，请刷新后再发送。' });
      return;
    }
    const old = this.attempts.get(this.view.conversationId);
    if (old && !['completed', 'failed'].includes(old.phase)) {
      this.update({ error: '原操作结果尚未确定；只能查询历史或重试原操作。' });
      return;
    }
    if (
      !text.trim() ||
      text.length > COMPOSER_LIMIT ||
      text.includes('\u0000') ||
      /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/.test(text)
    ) {
      this.update({ error: '消息须为非空有效文本，最多 2000 个字符。', errorKind: 'validation' });
      return;
    }
    if (!this.attempts.has(this.view.conversationId) && this.attempts.size >= 20) {
      this.update({ error: '本次会话的待处理操作已达上限，请先恢复原操作。' });
      return;
    }
    const attempt: Attempt = {
      conversationId: this.view.conversationId,
      body: Object.freeze({
        message: text.normalize('NFC').trim(),
        operation_key: asUUIDv4(this.uuid()),
        expected_relationship_id: this.view.relationshipId,
      }),
      phase: 'submitting',
      runId: null,
    };
    this.attempts.set(attempt.conversationId, attempt);
    await this.execute(attempt, mode);
  }
  async retry(mode: 'rest' | 'sse') {
    const attempt = this.view.conversationId
      ? this.attempts.get(this.view.conversationId)
      : undefined;
    if (attempt && this.authenticated() && this.view.scope === 'ready' && !this.runRequest)
      await this.execute(attempt, mode);
  }
  private async execute(attempt: Attempt, mode: 'rest' | 'sse') {
    const generation = this.generation;
    const controller = new AbortController();
    this.runRequest = controller;
    attempt.phase = 'submitting';
    this.update({
      phase: 'submitting',
      operationKey: attempt.body.operation_key!,
      runId: attempt.runId,
      error: null,
      errorKind: null,
      progress: null,
      warnings: [],
      memoryStatus: null,
    });
    let started = false;
    let finalId: UUID | null = null;
    let terminal = false;
    const acceptRun = (id: UUID) => {
      if (attempt.runId && attempt.runId !== id) throw new ApiError('protocol');
      attempt.runId = id;
      this.update({ runId: id });
    };
    const commit = (id: UUID, answer: string) => {
      finalId = id;
      this.finals.set(id, answer);
      attempt.phase = 'committed';
      this.presentMessages();
      this.update({ phase: 'committed' });
    };
    const event = (value: AgentEvent) => {
      if (!this.valid(generation) || controller.signal.aborted || this.runRequest !== controller)
        throw new ApiError('cancelled');
      if (terminal) throw new ApiError('protocol');
      acceptRun(value.run_id);
      switch (value.event) {
        case 'run_started':
          if (started || finalId) throw new ApiError('protocol');
          started = true;
          attempt.phase = 'running';
          this.update({ phase: 'running' });
          break;
        case 'status':
          if (!started || finalId) throw new ApiError('protocol');
          this.update({ progress: value.data.status });
          break;
        case 'final_response':
          if (finalId) throw new ApiError('protocol');
          commit(value.data.assistant_message_id, value.data.answer);
          break;
        case 'memory_status':
        case 'pending_confirmation':
          if (!finalId) throw new ApiError('protocol');
          this.update({ memoryStatus: value.data.status });
          break;
        case 'completed':
          if (!finalId || value.data.assistant_message_id !== finalId)
            throw new ApiError('protocol');
          terminal = true;
          attempt.phase = 'completed';
          this.update({
            phase: 'completed',
            memoryStatus: value.data.memory_status,
            progress: null,
          });
          break;
        case 'failed':
          if (finalId) throw new ApiError('protocol');
          terminal = true;
          attempt.phase =
            value.data.recovery_status === 'running_unknown' ? 'running_unknown' : 'failed';
          this.update({
            phase: attempt.phase,
            error:
              value.data.recovery_status === 'running_unknown'
                ? '无法确认该请求是否已完成。'
                : new ApiError('agent_failed').message,
            errorKind: 'agent_failed',
            progress: null,
          });
          break;
      }
    };
    try {
      if (mode === 'sse')
        await this.transport.streamAgent(
          attempt.conversationId,
          attempt.body,
          event,
          controller.signal,
        );
      else {
        const { data } = await this.transport.client.POST(
          '/api/v1/conversations/{conversation_id}/agent-runs',
          {
            params: { path: { conversation_id: attempt.conversationId } },
            body: attempt.body,
            signal: controller.signal,
          },
        );
        if (!this.valid(generation) || controller.signal.aborted || this.runRequest !== controller)
          return;
        if (
          !data ||
          data.conversation_id !== attempt.conversationId ||
          data.status !== 'completed' ||
          data.assistant_message.role !== 'assistant' ||
          typeof data.assistant_message.content !== 'string' ||
          !data.assistant_message.content ||
          data.assistant_message.content.length > 100_000 ||
          !memoryStatuses.includes(data.memory_status) ||
          !Array.isArray(data.warnings) ||
          data.warnings.length > 20 ||
          data.warnings.some((s) => typeof s !== 'string' || s.length > 256)
        )
          throw new ApiError('protocol');
        acceptRun(wireUUID(data.run_id));
        commit(wireUUID(data.assistant_message.id), data.assistant_message.content);
        attempt.phase = 'completed';
        this.update({
          phase: 'completed',
          memoryStatus: data.memory_status,
          warnings: data.warnings,
        });
      }
      if (this.valid(generation) && this.runRequest === controller) await this.loadHistory();
    } catch (error) {
      if (this.valid(generation) && this.runRequest === controller) {
        let failure = safeError(error);
        if (failure instanceof AgentApiError && failure.runId) {
          if (attempt.runId && attempt.runId !== failure.runId) failure = new ApiError('protocol');
          else acceptRun(failure.runId);
        }
        attempt.phase =
          failure instanceof AgentApiError && failure.recovery === 'running_unknown'
            ? 'running_unknown'
            : (failure instanceof AgentApiError && failure.recovery === 'failed') ||
                [
                  'not_found',
                  'invalid_scope',
                  'conflict',
                  'validation',
                  'operation_failed',
                ].includes(failure.kind)
              ? 'failed'
              : 'running_unknown';
        this.update({
          phase: attempt.phase,
          error: failure.message,
          errorKind: failure.kind,
          progress: null,
        });
      }
    } finally {
      if (this.runRequest === controller) this.runRequest = undefined;
    }
  }
}
