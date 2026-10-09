import type { components } from './generated/client';
import type {
  OwnedPersonViewModel,
  OwnedRelationshipViewModel,
  ConversationViewModel,
} from '../contracts/resources';
export function personView(dto: components['schemas']['PersonResponse']): OwnedPersonViewModel {
  return {
    id: dto.id,
    nickname: dto.display_name || null,
    createdAt: dto.created_at,
    source: 'server',
  };
}
export function relationshipView(
  dto: components['schemas']['RelationshipResponse'],
  person?: OwnedPersonViewModel,
): OwnedRelationshipViewModel {
  return {
    id: dto.id,
    displayName: person?.nickname ?? '对象名称未读取',
    person: { id: dto.person_id, nickname: person?.nickname ?? null },
    label: dto.relationship_type,
    statusLabel: dto.status,
    createdAt: dto.created_at,
    lastInteraction: null,
    known: [],
    missing: ['服务端未提供结构化 Profile。'],
    historySummary: null,
    analysisSummary: null,
    source: 'server',
  };
}
export function conversationView(
  dto: components['schemas']['ConversationResponse'],
): ConversationViewModel {
  return {
    id: dto.id,
    relationshipId: dto.relationship_id,
    createdAt: dto.created_at,
    source: 'server',
  };
}
