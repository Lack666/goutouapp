import type { PersonViewModel, RelationshipProfileViewModel } from './relationship';
export type ResourceKind = 'persons' | 'relationships' | 'conversations';
export interface OwnedPersonViewModel extends PersonViewModel {
  readonly createdAt: string;
  readonly source: 'server';
}
export interface OwnedRelationshipViewModel extends RelationshipProfileViewModel {
  readonly statusLabel: string;
  readonly createdAt: string;
}
export interface ConversationViewModel {
  readonly id: string;
  readonly relationshipId: string | null;
  readonly createdAt: string;
  readonly source: 'server';
}
export interface ResourceModels {
  persons: OwnedPersonViewModel;
  relationships: OwnedRelationshipViewModel;
  conversations: ConversationViewModel;
}
export interface ResourcePage<T> {
  readonly items: readonly T[];
  readonly cursor: string | null;
  readonly status: 'idle' | 'loading' | 'ready' | 'error';
  readonly error: string | null;
}
export interface ResourceDetail<T> {
  readonly value: T | null;
  readonly status: 'idle' | 'loading' | 'ready' | 'error';
  readonly error: string | null;
}
export interface CreateView {
  readonly status: 'idle' | 'pending' | 'failed' | 'saved';
  readonly error: string | null;
}
export type ResourcePages = { readonly [K in ResourceKind]: ResourcePage<ResourceModels[K]> };
export type ResourceDetails = { readonly [K in ResourceKind]: ResourceDetail<ResourceModels[K]> };
export interface ResourceView {
  readonly pages: ResourcePages;
  readonly details: ResourceDetails;
  readonly creates: Readonly<Record<ResourceKind, CreateView>>;
  readonly selectedRelationshipId: string | null;
  readonly selectedConversationId: string | null;
}
