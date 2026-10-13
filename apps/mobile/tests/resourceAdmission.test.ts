import { importHTTPError } from '../src/api/importErrors';
import { ApiError } from '../src/api/errors';
import { file, json, sessions, setup } from './importSupport';

afterEach(async () => {
  for (const session of sessions.splice(0)) await session.logout();
});

it.each([
  [413, 'upload_too_large'],
  [429, 'http_error'],
  [503, 'artifact_unavailable'],
  [408, 'http_error'],
])(
  'formal resource rejection %s never reports success or automatically retries',
  async (status, code) => {
    const privateInput = `runtime-only-${Date.now()}-${Math.random()}`;
    const { controller, requests } = await setup(async (request) => {
      if (request.method === 'POST')
        return json({ error: { code, message: privateInput } }, status);
      return undefined;
    });
    await controller.select(async () => file());
    await controller.upload();
    // Existing503 contract conservatively keeps a possibly committed upload
    // unknown; admission must not weaken that response-loss safety policy.
    expect(controller.snapshot().upload).toBe(status === 503 ? 'unknown_outcome' : 'failed');
    expect(controller.snapshot().job).toBeNull();
    expect(controller.snapshot().error).not.toContain(privateInput);
    expect(requests.filter((request) => request.method === 'POST')).toHaveLength(1);
    const error = importHTTPError(
      status,
      JSON.stringify({ error: { code, message: privateInput } }),
    );
    expect(error.status).toBe(status);
    expect(error.kind).toBe('unavailable');
    expect(error.kind).not.toBe(new ApiError('offline').kind);
    expect(error.message).not.toContain(privateInput);
  },
);
