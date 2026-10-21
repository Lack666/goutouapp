import type { components, UUID } from '../api/generated/client';
import { ApiTransport } from '../api/transport';
import { ApiError, safeError } from '../api/errors';
import { asUUID, asUUIDv4 } from '../api/uuid';
import { personView, relationshipView, conversationView } from '../api/resourceAdapter';
import type {
  ResourceKind,
  ResourceModels,
  ResourceView,
  ResourcePage,
  ResourceDetail,
} from '../contracts/resources';
import type { DevelopmentSession } from '../session/developmentSession';

type Bodies = {
  persons: components['schemas']['PersonCreateRequest'];
  relationships: components['schemas']['RelationshipCreateRequest'];
  conversations: components['schemas']['ConversationCreateRequest'];
};
type Attempt = { [K in ResourceKind]: { kind: K; body: Readonly<Bodies[K]> } }[ResourceKind];
const emptyPage = <T>(): ResourcePage<T> => ({
  items: [],
  cursor: null,
  status: 'idle',
  error: null,
});
const emptyDetail = <T>(): ResourceDetail<T> => ({ value: null, status: 'idle', error: null });
function emptyView(): ResourceView {
  return {
    pages: { persons: emptyPage(), relationships: emptyPage(), conversations: emptyPage() },
    details: { persons: emptyDetail(), relationships: emptyDetail(), conversations: emptyDetail() },
    creates: {
      persons: { status: 'idle', error: null },
      relationships: { status: 'idle', error: null },
      conversations: { status: 'idle', error: null },
    },
    selectedRelationshipId: null,
    selectedConversationId: null,
  };
}
export class ResourceController {
  private view = emptyView();
  private readonly listeners = new Set<() => void>();
  private readonly pending = new Map<ResourceKind, Attempt>();
  private readonly pageRequests = new Map<ResourceKind, AbortController>();
  private readonly detailRequests = new Map<ResourceKind, AbortController>();
  private readonly creating = new Set<ResourceKind>();
  private currentEpoch: number;
  constructor(
    readonly transport: ApiTransport,
    private readonly session: DevelopmentSession,
    private readonly uuid: () => string,
    private readonly limit = 30,
  ) {
    this.currentEpoch = session.epoch();
    session.subscribe(() => {
      if (this.currentEpoch !== session.epoch()) {
        this.currentEpoch = session.epoch();
        transport.cancelAll();
        this.pending.clear();
        this.pageRequests.clear();
        this.detailRequests.clear();
        this.creating.clear();
        this.view = emptyView();
        this.emit();
      }
    });
  }
  snapshot = () => this.view;
  clear = () => {
    for (const request of this.pageRequests.values()) request.abort();
    for (const request of this.detailRequests.values()) request.abort();
    this.pageRequests.clear();
    this.detailRequests.clear();
    this.pending.clear();
    this.creating.clear();
    this.view = emptyView();
    this.emit();
  };
  invalidateConversation = (id: string) => {
    this.pending.delete('conversations');
    this.pageRequests.get('conversations')?.abort();
    this.pageRequests.delete('conversations');
    this.detailRequests.get('conversations')?.abort();
    this.detailRequests.delete('conversations');
    this.view = {
      ...this.view,
      selectedConversationId:
        this.view.selectedConversationId === id ? null : this.view.selectedConversationId,
      pages: { ...this.view.pages, conversations: emptyPage() },
      details: { ...this.view.details, conversations: emptyDetail() },
    };
    this.emit();
  };
  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  };
  private emit() {
    for (const fn of this.listeners) fn();
  }
  private authenticated() {
    return this.session.snapshot().status === 'authenticated' && this.session.credential() !== null;
  }
  private page<K extends ResourceKind>(kind: K, page: ResourcePage<ResourceModels[K]>) {
    this.view = { ...this.view, pages: { ...this.view.pages, [kind]: page } };
    // Person and Relationship pages may finish in either order. A late Person
    // page enriches names only; it must not refresh/reset the selected scope.
    if (kind === 'persons' && page.status === 'ready') {
      const relationships = this.view.pages.relationships;
      this.view = {
        ...this.view,
        pages: {
          ...this.view.pages,
          relationships: {
            ...relationships,
            items: relationships.items.map((relationship) => {
              const person = this.view.pages.persons.items.find(
                (item) => item.id === relationship.person.id,
              );
              return person
                ? {
                    ...relationship,
                    displayName: person.nickname ?? '对象名称未读取',
                    person: { id: person.id, nickname: person.nickname },
                  }
                : relationship;
            }),
          },
        },
      };
    }
    this.emit();
  }
  private detail<K extends ResourceKind>(kind: K, detail: ResourceDetail<ResourceModels[K]>) {
    this.view = { ...this.view, details: { ...this.view.details, [kind]: detail } };
    this.emit();
  }
  probe = async () => {
    const { data } = await this.transport.client.GET('/api/v1/persons', {
      params: { query: { limit: 1 } },
    });
    if (!data) throw new ApiError('protocol');
  };
  async load(kind: ResourceKind, more = false) {
    if (!this.authenticated() || this.pageRequests.has(kind)) return;
    const prior = this.view.pages[kind];
    if (more && !prior.cursor) return;
    const epoch = this.session.epoch();
    const controller = new AbortController();
    this.pageRequests.set(kind, controller);
    if (!more) {
      this.detailRequests.get(kind)?.abort();
      this.detailRequests.delete(kind);
      this.detail(kind, emptyDetail());
      this.view = {
        ...this.view,
        ...(kind === 'relationships'
          ? { selectedRelationshipId: null }
          : kind === 'conversations'
            ? { selectedConversationId: null }
            : {}),
      };
    }
    this.page(kind, {
      ...prior,
      ...(more ? {} : { items: [], cursor: null }),
      status: 'loading',
      error: null,
    });
    try {
      const query = { limit: this.limit, ...(more ? { cursor: prior.cursor! } : {}) };
      const options = { params: { query }, signal: controller.signal };
      const items: ResourceModels[ResourceKind][] = [];
      let cursor: string | null;
      switch (kind) {
        case 'persons': {
          const { data } = await this.transport.client.GET('/api/v1/persons', options);
          if (!data) throw new ApiError('protocol');
          items.push(...data.items.map(personView));
          cursor = data.next_cursor;
          break;
        }
        case 'relationships': {
          const { data } = await this.transport.client.GET('/api/v1/relationships', options);
          if (!data) throw new ApiError('protocol');
          items.push(
            ...data.items.map((dto) =>
              relationshipView(
                dto,
                this.view.pages.persons.items.find((p) => p.id === dto.person_id),
              ),
            ),
          );
          cursor = data.next_cursor;
          break;
        }
        case 'conversations': {
          const { data } = await this.transport.client.GET('/api/v1/conversations', options);
          if (!data) throw new ApiError('protocol');
          items.push(...data.items.map(conversationView));
          cursor = data.next_cursor;
          break;
        }
      }
      if (epoch !== this.session.epoch() || this.pageRequests.get(kind) !== controller) return;
      if (cursor !== null && cursor === prior.cursor) throw new ApiError('protocol');
      const merged = new Map<string, ResourceModels[ResourceKind]>(
        (more ? prior.items : []).map((item) => [item.id, item]),
      );
      for (const item of items) merged.set(item.id, item);
      this.page(kind, { items: [...merged.values()], cursor, status: 'ready', error: null });
    } catch (error) {
      if (epoch === this.session.epoch() && this.pageRequests.get(kind) === controller)
        this.page(kind, {
          ...prior,
          ...(more ? {} : { items: [], cursor: null }),
          status: 'error',
          error: safeError(error).message,
        });
    } finally {
      if (this.pageRequests.get(kind) === controller) this.pageRequests.delete(kind);
    }
  }
  async select(kind: ResourceKind, value: string) {
    if (!this.authenticated()) return;
    this.detailRequests.get(kind)?.abort();
    const controller = new AbortController();
    this.detailRequests.set(kind, controller);
    const epoch = this.session.epoch();
    this.view = {
      ...this.view,
      ...(kind === 'relationships'
        ? { selectedRelationshipId: null }
        : kind === 'conversations'
          ? { selectedConversationId: null }
          : {}),
    };
    this.detail(kind, { value: null, status: 'loading', error: null });
    try {
      const id = asUUID(value);
      let model: ResourceModels[ResourceKind];
      switch (kind) {
        case 'persons': {
          const { data } = await this.transport.client.GET('/api/v1/persons/{person_id}', {
            params: { path: { person_id: id } },
            signal: controller.signal,
          });
          if (!data) throw new ApiError('protocol');
          model = personView(data);
          break;
        }
        case 'relationships': {
          const { data } = await this.transport.client.GET(
            '/api/v1/relationships/{relationship_id}',
            { params: { path: { relationship_id: id } }, signal: controller.signal },
          );
          if (!data) throw new ApiError('protocol');
          const person = await this.transport.client.GET('/api/v1/persons/{person_id}', {
            params: { path: { person_id: data.person_id } },
            signal: controller.signal,
          });
          if (!person.data) throw new ApiError('protocol');
          model = relationshipView(data, personView(person.data));
          break;
        }
        case 'conversations': {
          const { data } = await this.transport.client.GET(
            '/api/v1/conversations/{conversation_id}',
            { params: { path: { conversation_id: id } }, signal: controller.signal },
          );
          if (!data) throw new ApiError('protocol');
          model = conversationView(data);
          break;
        }
      }
      if (epoch !== this.session.epoch() || this.detailRequests.get(kind) !== controller) return;
      this.view = {
        ...this.view,
        ...(kind === 'relationships'
          ? { selectedRelationshipId: model.id }
          : kind === 'conversations'
            ? { selectedConversationId: model.id }
            : {}),
      };
      this.detail(kind, { value: model, status: 'ready', error: null });
    } catch (error) {
      if (epoch === this.session.epoch() && this.detailRequests.get(kind) === controller)
        this.detail(kind, { value: null, status: 'error', error: safeError(error).message });
    } finally {
      if (this.detailRequests.get(kind) === controller) this.detailRequests.delete(kind);
    }
  }
  reservePerson(name: string) {
    return this.reserve({ kind: 'persons', body: { id: this.newID(), display_name: name } });
  }
  reserveRelationship(personId: string, type: string, status: string) {
    return this.reserve({
      kind: 'relationships',
      body: { id: this.newID(), person_id: asUUID(personId), relationship_type: type, status },
    });
  }
  reserveConversation(relationshipId: string | null) {
    return this.reserve({
      kind: 'conversations',
      body: {
        id: this.newID(),
        relationship_id: relationshipId === null ? null : asUUID(relationshipId),
      },
    });
  }
  private newID(): UUID {
    return asUUIDv4(this.uuid());
  }
  private reserve(attempt: Attempt) {
    if (!this.authenticated() || this.creating.has(attempt.kind)) return false;
    Object.freeze(attempt.body);
    this.pending.set(attempt.kind, Object.freeze(attempt));
    this.view = {
      ...this.view,
      creates: { ...this.view.creates, [attempt.kind]: { status: 'idle', error: null } },
    };
    this.emit();
    return true;
  }
  async retryCreate(kind: ResourceKind) {
    const attempt = this.pending.get(kind);
    if (!attempt || !this.authenticated() || this.creating.has(kind)) return;
    const epoch = this.session.epoch();
    this.creating.add(kind);
    this.view = {
      ...this.view,
      creates: { ...this.view.creates, [kind]: { status: 'pending', error: null } },
    };
    this.emit();
    try {
      switch (attempt.kind) {
        case 'persons': {
          const { data } = await this.transport.client.POST('/api/v1/persons', {
            body: attempt.body,
          });
          if (!data || data.id !== attempt.body.id) throw new ApiError('protocol');
          break;
        }
        case 'relationships': {
          const { data } = await this.transport.client.POST('/api/v1/relationships', {
            body: attempt.body,
          });
          if (!data || data.id !== attempt.body.id) throw new ApiError('protocol');
          break;
        }
        case 'conversations': {
          const { data } = await this.transport.client.POST('/api/v1/conversations', {
            body: attempt.body,
          });
          if (!data || data.id !== attempt.body.id) throw new ApiError('protocol');
          break;
        }
      }
      if (epoch !== this.session.epoch()) return;
      this.pending.delete(kind);
      this.view = {
        ...this.view,
        creates: { ...this.view.creates, [kind]: { status: 'saved', error: null } },
      };
      this.emit();
      await this.load(kind);
      await this.select(kind, attempt.body.id);
    } catch (error) {
      if (epoch === this.session.epoch()) {
        this.view = {
          ...this.view,
          creates: {
            ...this.view.creates,
            [kind]: { status: 'failed', error: safeError(error).message },
          },
        };
        this.emit();
      }
    } finally {
      if (epoch === this.session.epoch()) this.creating.delete(kind);
    }
  }
}
