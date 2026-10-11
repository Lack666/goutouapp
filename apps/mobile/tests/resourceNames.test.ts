import { runInThisContext } from 'node:vm';
import { ApiTransport } from '../src/api/transport';
import { ResourceController } from '../src/data/resourceController';
import { DevelopmentSession } from '../src/session/developmentSession';
import { createVolatileTokenStorage } from '../src/session/storage';
Object.assign(globalThis, {
  Request: runInThisContext('Request'),
  Response: runInThisContext('Response'),
  Headers: runInThisContext('Headers'),
  AbortController: runInThisContext('AbortController'),
});
const id = '11111111-1111-4111-8111-111111111111';
const rel = '22222222-2222-4222-8222-222222222222';
const json = (data: unknown) => new Response(JSON.stringify(data));
it.each(['persons', 'relationships'] as const)(
  'late %s page resolves owned names without resetting selection/cursor',
  async (late) => {
    let finish: (response: Response) => void = () => undefined;
    let delayed = false;
    const session = new DevelopmentSession(createVolatileTokenStorage());
    const transport = new ApiTransport(
      'http://localhost:8000',
      session,
      async (input) => {
        const path = new URL(new Request(input).url).pathname;
        const persons = {
          items: [{ id, display_name: '匿名对象', created_at: '', updated_at: '' }],
          next_cursor: null,
        };
        const relationships = {
          items: [
            {
              id: rel,
              person_id: id,
              relationship_type: 'unknown',
              status: 'unknown',
              created_at: '',
              updated_at: '',
            },
          ],
          next_cursor: 'opaque',
        };
        const result = path.endsWith('persons') ? persons : relationships;
        if (path.includes('/persons/')) return json(persons.items[0]);
        if (path.includes('/relationships/')) return json(relationships.items[0]);
        if (delayed && path.endsWith(late))
          return new Promise((resolve) => {
            finish = () => resolve(json(result));
          });
        return json(result);
      },
      1000,
      true,
    );
    const resources = new ResourceController(transport, session, () => id);
    const token = `${Buffer.from('{}').toString('base64url')}.${Buffer.from(JSON.stringify({ sub: id, exp: Date.now() / 1000 + 900 })).toString('base64url')}.synthetic`;
    try {
      await session.connect(token, resources.probe);
      delayed = true;
      const pending = resources.load(late);
      for (let i = 0; i < 8; i++) await Promise.resolve();
      await resources.load(late === 'persons' ? 'relationships' : 'persons');
      await resources.select('relationships', rel);
      finish(json({}));
      await pending;
      expect(resources.snapshot().pages.relationships.items[0]?.displayName).toBe('匿名对象');
      expect(resources.snapshot().pages.relationships.cursor).toBe('opaque');
      expect(resources.snapshot().selectedRelationshipId).toBe(rel);
    } finally {
      await session.logout();
    }
  },
);
