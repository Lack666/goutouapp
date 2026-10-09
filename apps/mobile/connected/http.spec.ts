import { randomUUID } from 'node:crypto';
import { test, expect } from './fixture';
import { DevelopmentSession } from '../src/session/developmentSession';
import { createVolatileTokenStorage } from '../src/session/storage';
import { ApiTransport } from '../src/api/transport';
import { ResourceController } from '../src/data/resourceController';
import { asUUID } from '../src/api/uuid';

test('generated mobile client + CLI signed JWT + real HTTP + PostgreSQL: retries, scopes, pages and conflicts', async ({
  backend,
}) => {
  const session = new DevelopmentSession(createVolatileTokenStorage());
  const sent: string[] = [];
  const committed: string[] = [];
  const lost = new Set<string>();
  const wire: typeof fetch = async (input, init) => {
    const request = new Request(input, init);
    const payload = request.method === 'POST' ? await request.clone().text() : null;
    const response = await fetch(request);
    if (request.method === 'POST') {
      const body = payload!;
      sent.push(body);
      const domain = new URL(request.url).pathname;
      if (!lost.has(domain) && response.status === 201) {
        lost.add(domain);
        committed.push(body);
        await response.text();
        throw new Error('Injected response loss after real server commit');
      }
    }
    return response;
  };
  const transport = new ApiTransport(backend.baseURL, session, wire, 5000, true);
  const resources = new ResourceController(transport, session, randomUUID, 1);
  try {
    await session.connect(backend.a, resources.probe);
    expect(session.snapshot().status).toBe('authenticated');
    resources.reservePerson('Mobile HTTP synthetic A');
    await resources.retryCreate('persons');
    expect(resources.snapshot().creates.persons.status).toBe('failed');
    await resources.retryCreate('persons');
    const person = resources.snapshot().details.persons.value!;
    expect(!!person).toBe(true);
    resources.reserveRelationship(person.id, 'unknown', 'unknown');
    await resources.retryCreate('relationships');
    await resources.retryCreate('relationships');
    const relationship = resources.snapshot().details.relationships.value!;
    expect(relationship.person.id).toBe(person.id);
    resources.reserveConversation(relationship.id);
    await resources.retryCreate('conversations');
    await resources.retryCreate('conversations');
    const conversation = resources.snapshot().details.conversations.value!;
    expect(conversation.relationshipId).toBe(relationship.id);
    expect(sent.length).toBe(6);
    expect(sent.every((body, i) => body === committed[Math.floor(i / 2)])).toBe(true);
    expect(await backend.counts()).toEqual({ persons: 1, relationships: 1, conversations: 1 });
    const conflicting = await transport.client
      .POST('/api/v1/persons', { body: { id: asUUID(person.id), display_name: 'changed' } })
      .catch((error: unknown) => error);
    expect(conflicting).toMatchObject({ status: 409 });
    const id = asUUID(randomUUID());
    const concurrent = await Promise.all(
      Array.from({ length: 6 }, () =>
        transport.client.POST('/api/v1/persons', {
          body: { id, display_name: 'Concurrent synthetic' },
        }),
      ),
    );
    expect(new Set(concurrent.map((r) => r.data?.id)).size).toBe(1);
    await resources.load('persons');
    await resources.load('persons', true);
    expect(resources.snapshot().pages.persons.items.length).toBe(2);
    expect(resources.snapshot().pages.persons.cursor).toBeNull();
    session.logout();
    expect(resources.snapshot().pages.persons.items).toEqual([]);
    expect(resources.snapshot().selectedRelationshipId).toBeNull();
    await session.connect(backend.b, resources.probe);
    for (const domain of ['persons', 'relationships', 'conversations'] as const) {
      await resources.load(domain);
      expect(resources.snapshot().pages[domain].items).toEqual([]);
    }
    await resources.select('persons', person.id);
    expect(resources.snapshot().details.persons.status).toBe('error');
    await expect(
      transport.client.POST('/api/v1/relationships', {
        body: {
          id: asUUID(randomUUID()),
          person_id: asUUID(person.id),
          relationship_type: 'unknown',
          status: 'unknown',
        },
      }),
    ).rejects.toMatchObject({ status: 404 });
    await expect(
      transport.client.POST('/api/v1/persons', {
        body: { id: asUUID(randomUUID()), display_name: '' },
      }),
    ).rejects.toMatchObject({ status: 422 });
    await session.connect(backend.expired, resources.probe);
    expect(session.snapshot().status).toBe('expired');
  } finally {
    session.logout();
  }
});
