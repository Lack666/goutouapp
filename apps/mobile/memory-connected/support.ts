import { randomUUID } from 'node:crypto';
import { ApiTransport } from '../src/api/transport';
import { MemoryController } from '../src/data/memoryController';
import { AgentChatController } from '../src/data/agentChatController';
import { ResourceController } from '../src/data/resourceController';
import { ImportController } from '../src/data/importController';
import { DevelopmentSession } from '../src/session/developmentSession';
import { createVolatileTokenStorage } from '../src/session/storage';
import { expect } from '@playwright/test';
export async function connected(baseURL: string, credential: string, wire: typeof fetch = fetch) {
  const session = new DevelopmentSession(createVolatileTokenStorage());
  const transport = new ApiTransport(
    baseURL,
    session,
    wire,
    5000,
    true,
    true,
    wire,
    10000,
    true,
    10000,
    true,
  );
  const resources = new ResourceController(transport, session, randomUUID);
  const memory = new MemoryController(transport, session, randomUUID);
  const chat = new AgentChatController(transport, session, randomUUID);
  const imports = new ImportController(transport, session);
  await session.connect(credential, resources.probe);
  expect(session.snapshot().status).toBe('authenticated');
  return { session, transport, resources, memory, chat, imports };
}
export async function scope(
  value: Awaited<ReturnType<typeof connected>>,
  nickname = '8E anonymous synthetic',
) {
  value.resources.reservePerson(nickname);
  await value.resources.retryCreate('persons');
  const person = value.resources.snapshot().details.persons.value!.id;
  value.resources.reserveRelationship(person, 'unknown', 'unknown');
  await value.resources.retryCreate('relationships');
  const relationship = value.resources.snapshot().selectedRelationshipId!;
  value.resources.reserveConversation(relationship);
  await value.resources.retryCreate('conversations');
  const conversation = value.resources.snapshot().selectedConversationId!;
  return { person, relationship, conversation };
}
export async function save(
  value: Awaited<ReturnType<typeof connected>>,
  target: Awaited<ReturnType<typeof scope>>,
  week = '一',
  mode: 'rest' | 'sse' = 'rest',
) {
  await value.chat.open(target.conversation, target.relationship);
  await value.chat.send(`我们计划第${week}周见面。请存入长期记忆。`, mode);
  expect(value.chat.snapshot().phase).toBe('completed');
  return value.chat.snapshot().memoryStatus;
}
