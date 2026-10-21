import { randomUUID } from 'node:crypto';
import { ApiTransport } from '../src/api/transport';
import { ImportController } from '../src/data/importController';
import { HistoryController } from '../src/data/historyController';
import { DevelopmentSession } from '../src/session/developmentSession';
import { createVolatileTokenStorage } from '../src/session/storage';
import { ResourceController } from '../src/data/resourceController';
import { expect } from '@playwright/test';
export function syntheticTranscript(count: number, marker = 'anonymous synthetic') {
  return Array.from(
    { length: count },
    (_, i) =>
      `## 2024-01-01 08:00:00 ${i % 2 === 0 ? '我' : '匿名同学🥰'}\n\n合成重复消息 ${marker}。\n\n`,
  ).join('');
}
export function selectedFixture(count: number, marker?: string) {
  const data = new Blob([syntheticTranscript(count, marker)], { type: 'text/markdown' });
  return {
    name: 'anonymous-wechat-v1.md',
    size: data.size,
    mimeType: data.type,
    binary: async () => data,
    release: () => undefined,
  };
}
export async function connected(
  baseURL: string,
  credential: string,
  wire: typeof fetch = fetch,
  displayName = '8D anonymous synthetic',
) {
  const session = new DevelopmentSession(createVolatileTokenStorage());
  const transport = new ApiTransport(
    baseURL,
    session,
    wire,
    5000,
    true,
    true,
    wire,
    5000,
    true,
    30_000,
  );
  const resources = new ResourceController(transport, session, randomUUID);
  const imports = new ImportController(transport, session);
  const history = new HistoryController(transport, session);
  await session.connect(credential, resources.probe);
  resources.reservePerson(displayName);
  await resources.retryCreate('persons');
  const person = resources.snapshot().details.persons.value!.id;
  resources.reserveRelationship(person, 'unknown', 'unknown');
  await resources.retryCreate('relationships');
  const relationship = resources.snapshot().selectedRelationshipId!;
  resources.reserveConversation(relationship);
  await resources.retryCreate('conversations');
  const conversation = resources.snapshot().selectedConversationId!;
  await imports.open(relationship);
  return { session, transport, resources, imports, history, person, relationship, conversation };
}
export async function bind(imports: ImportController, person: string) {
  await imports.bindSpeaker('我', 'self');
  expect(imports.snapshot().error).toBeNull();
  await imports.bindSpeaker('匿名同学🥰', 'person', person);
  expect(imports.snapshot().error).toBeNull();
  await imports.confirmRelationship();
  expect(imports.snapshot().error).toBeNull();
  await imports.ready();
  expect(imports.snapshot().error).toBeNull();
}
