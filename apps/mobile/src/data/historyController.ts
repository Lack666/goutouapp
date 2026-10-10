import { ApiTransport } from '../api/transport';
import { ApiError, safeError } from '../api/errors';
import { asUUID } from '../api/uuid';
import { agentHistoryView, relationshipHistoryView } from '../api/importAdapter';
import type { HistoryItemViewModel, HistorySourceKind } from '../contracts/history';
import type { DevelopmentSession } from '../session/developmentSession';

export interface ConnectedHistoryView {
  readonly kind: HistorySourceKind;
  readonly parentId: string | null;
  readonly relationshipId: string | null;
  readonly items: readonly HistoryItemViewModel[];
  readonly cursor: string | null;
  readonly status: 'idle' | 'loading' | 'ready' | 'error';
  readonly error: string | null;
  readonly bounded: boolean;
}
const empty = (kind: HistorySourceKind = 'relationship'): ConnectedHistoryView => ({
  kind,
  parentId: null,
  relationshipId: null,
  items: [],
  cursor: null,
  status: 'idle',
  error: null,
  bounded: false,
});
export class HistoryController {
  private view = empty();
  private readonly listeners = new Set<() => void>();
  private generation = 0;
  private epoch: number;
  private request: AbortController | null = null;
  private resumeScope: {
    kind: HistorySourceKind;
    parent: string;
    relationship: string | null;
  } | null = null;
  constructor(
    private readonly transport: ApiTransport,
    private readonly session: DevelopmentSession,
    private readonly limit = 100,
    private readonly maxItems = 2000,
  ) {
    if (limit < 1 || limit > 100) throw new ApiError('validation');
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
  private patch(value: Partial<ConnectedHistoryView>) {
    this.view = { ...this.view, ...value };
    for (const fn of this.listeners) fn();
  }
  clear = (kind: HistorySourceKind = 'relationship') => {
    this.resumeScope = null;
    this.generation++;
    this.request?.abort();
    this.request = null;
    this.view = empty(kind);
    this.patch({});
  };
  leave = () => this.clear(this.view.kind);
  pause = () => {
    const prior = this.view;
    this.clear(prior.kind);
    if (prior.parentId)
      this.resumeScope = {
        kind: prior.kind,
        parent: prior.parentId,
        relationship: prior.relationshipId,
      };
  };
  resume = async () => {
    const scope = this.resumeScope;
    if (scope && this.authenticated())
      await this.open(scope.kind, scope.parent, scope.kind === 'agent' ? scope.relationship : null);
  };
  private authenticated() {
    return this.session.snapshot().status === 'authenticated' && this.session.credential() !== null;
  }
  async open(kind: HistorySourceKind, value: string, expectedRelationship: string | null = null) {
    this.clear(kind);
    if (!this.authenticated()) return;
    const generation = this.generation;
    const request = new AbortController();
    this.request = request;
    this.patch({ status: 'loading' });
    try {
      const id = asUUID(value);
      let relationshipId: string | null = id;
      if (kind === 'relationship') {
        const { data } = await this.transport.client.GET(
          '/api/v1/relationships/{relationship_id}',
          { params: { path: { relationship_id: id } }, signal: request.signal },
        );
        if (!data || data.id !== id) throw new ApiError('protocol');
      } else {
        const { data } = await this.transport.client.GET(
          '/api/v1/conversations/{conversation_id}',
          { params: { path: { conversation_id: id } }, signal: request.signal },
        );
        if (!data || data.id !== id) throw new ApiError('protocol');
        if (expectedRelationship !== null && data.relationship_id !== asUUID(expectedRelationship))
          throw new ApiError('invalid_scope');
        relationshipId = data.relationship_id;
      }
      if (generation !== this.generation) return;
      this.patch({ parentId: id, relationshipId, status: 'ready' });
    } catch (error) {
      if (generation === this.generation)
        this.patch({ status: 'error', error: safeError(error).message });
    } finally {
      if (this.request === request) this.request = null;
    }
    if (generation === this.generation && this.view.parentId) await this.load();
  }
  async load(more = false) {
    if (
      !this.authenticated() ||
      this.request ||
      !this.view.parentId ||
      (more && (!this.view.cursor || this.view.bounded))
    )
      return;
    const prior = this.view;
    const generation = this.generation;
    const request = new AbortController();
    this.request = request;
    this.patch({
      status: 'loading',
      error: null,
      ...(!more ? { items: [], cursor: null, bounded: false } : {}),
    });
    try {
      const query = { limit: this.limit, ...(more ? { cursor: prior.cursor! } : {}) };
      let items: HistoryItemViewModel[];
      let cursor: string | null;
      if (prior.kind === 'relationship') {
        const { data } = await this.transport.client.GET(
          '/api/v1/relationships/{relationship_id}/messages',
          {
            params: { path: { relationship_id: asUUID(prior.parentId!) }, query },
            signal: request.signal,
          },
        );
        if (!data || !Array.isArray(data.items) || data.items.length > this.limit)
          throw new ApiError('protocol');
        items = data.items.map((dto) => relationshipHistoryView(dto, prior.parentId!));
        cursor = data.next_cursor;
      } else {
        const { data } = await this.transport.client.GET(
          '/api/v1/conversations/{conversation_id}/messages',
          {
            params: { path: { conversation_id: asUUID(prior.parentId!) }, query },
            signal: request.signal,
          },
        );
        if (!data || !Array.isArray(data.items) || data.items.length > this.limit)
          throw new ApiError('protocol');
        items = data.items.map((dto) =>
          agentHistoryView(dto, prior.parentId!, prior.relationshipId),
        );
        cursor = data.next_cursor;
      }
      if (
        cursor !== null &&
        (typeof cursor !== 'string' || cursor.length === 0 || (more && cursor === prior.cursor))
      )
        throw new ApiError('protocol');
      if (generation !== this.generation) return;
      const merged = new Map((more ? prior.items : []).map((item) => [item.id, item]));
      for (const item of items) merged.set(item.id, item);
      const all = [...merged.values()];
      const bounded = all.length >= this.maxItems && cursor !== null;
      // Preserve server order, including microseconds and equal-time occurrences.
      this.patch({
        items: all.slice(0, this.maxItems),
        cursor,
        bounded,
        status: 'ready',
        error: null,
      });
    } catch (error) {
      if (generation === this.generation)
        this.patch({
          ...(more ? { items: prior.items, cursor: prior.cursor } : { items: [], cursor: null }),
          status: 'error',
          error: safeError(error).message,
        });
    } finally {
      if (this.request === request) this.request = null;
    }
  }
}
