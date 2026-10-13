import { file, json, sessions, setup } from './importSupport';

afterEach(async () => {
  for (const session of sessions.splice(0)) await session.logout();
});

it.each(['parse_failed', 'import_failed', 'PHASE9A_PRIVATE_CODE_SENTINEL'])(
  'never retains private upload error details for public code %s',
  async (code) => {
    const marker = 'PHASE9A_PRIVATE_BODY_TOKEN_PATH_SENTINEL';
    const { controller } = await setup(async (request) =>
      request.url.endsWith('/chat-imports')
        ? json(
            { error: { code, message: marker, authorization: `Bearer ${marker}`, sql: marker } },
            code === 'import_failed' ? 503 : 422,
          )
        : undefined,
    );
    await controller.select(async () => file());
    await controller.upload();
    const view = controller.snapshot();
    expect(view.upload).toBe(code === 'import_failed' ? 'unknown_outcome' : 'failed');
    expect(JSON.stringify(view)).not.toContain(marker);
    expect(JSON.stringify(view)).not.toContain('PHASE9A_PRIVATE_CODE_SENTINEL');
    expect(view.error).not.toBeNull();
  },
);
