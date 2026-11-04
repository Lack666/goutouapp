import { ApiTransport } from '../src/api/transport';

it('ICA transport is explicitly enabled, signed and admits no execute or Memory route', async () => {
  const requests: Request[] = [];
  const fetcher: typeof fetch = async (input) => {
    requests.push(input as Request);
    return new Response(JSON.stringify({}), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };
  const session = {
    credential: () => 'synthetic-test-credential',
    epoch: () => 1,
    invalidate: jest.fn(),
  };
  const enabled = new ApiTransport(
    'http://127.0.0.1:8000',
    session,
    fetcher,
    12000,
    true,
    false,
    fetcher,
    60000,
    false,
    120000,
    false,
    false,
    true,
  );
  await enabled.client.POST('/api/v1/imported-analysis/prepare', {
    body: {
      dataset_id: '11111111-1111-4111-8111-111111111111',
      person_id: '22222222-2222-4222-8222-222222222222',
      relationship_id: '33333333-3333-4333-8333-333333333333',
      timezone: 'UTC',
      windows: [{ days: 7 }],
      question: 'Synthetic',
      model: 'unquoted',
      max_tokens: 100,
      max_requests: 10,
    },
  });
  expect(requests).toHaveLength(1);
  const request = requests[0]!;
  expect(request.headers.get('Authorization')).toBe('Bearer synthetic-test-credential');
  const disabled = new ApiTransport('http://127.0.0.1:8000', session, fetcher, 12000, true);
  await expect(
    disabled.client.GET('/api/v1/imported-analysis/grants/{grant_id}', {
      params: { path: { grant_id: '11111111-1111-4111-8111-111111111111' } },
    }),
  ).rejects.toThrow();
  expect(requests).toHaveLength(1);
  await expect(
    enabled.client.POST('/api/v1/imported-analysis/execution-prepare', {
      body: { grant_id: '11111111-1111-4111-8111-111111111111' },
    }),
  ).rejects.toThrow();
  expect(requests).toHaveLength(1);
});

it('Mock execution transport requires its own explicit opt-in', async () => {
  const requests: Request[] = [];
  const fetcher: typeof fetch = async (input) => {
    requests.push(input as Request);
    return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } });
  };
  const session = { credential: () => 'synthetic', epoch: () => 1, invalidate: jest.fn() };
  const enabled = new ApiTransport(
    'http://127.0.0.1:8000',
    session,
    fetcher,
    12000,
    true,
    false,
    fetcher,
    60000,
    false,
    120000,
    false,
    false,
    false,
    true,
  );
  await enabled.client.POST('/api/v1/imported-analysis/execution-prepare', {
    body: { grant_id: '11111111-1111-4111-8111-111111111111' },
  });
  expect(requests).toHaveLength(1);
  expect(requests[0]!.headers.get('Authorization')).toBe('Bearer synthetic');
  await expect(
    enabled.client.POST('/api/v1/imported-analysis/prepare', {
      body: {
        dataset_id: '11111111-1111-4111-8111-111111111111',
        relationship_id: '22222222-2222-4222-8222-222222222222',
        person_id: '33333333-3333-4333-8333-333333333333',
        timezone: 'UTC',
        windows: [{ days: 7 }],
        question: 'Synthetic',
        model: 'mock',
        max_tokens: 1,
        max_requests: 1,
      },
    }),
  ).rejects.toThrow();
});
