import { createApiClient } from './generated/client';
import { ApiError, httpError } from './errors';

export interface TransportSession {
  credential(): string | null;
  epoch(): number;
  invalidate(epoch: number): void;
}
export function validateBaseURL(value: string, localDevelopment: boolean) {
  try {
    const url = new URL(value);
    if (url.username || url.password || url.search || url.hash || url.pathname !== '/')
      throw new Error();
    const localHost =
      ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname) ||
      /^10\.\d+\.\d+\.\d+$|^192\.168\.\d+\.\d+$|^172\.(1[6-9]|2\d|3[01])\.\d+\.\d+$/.test(
        url.hostname,
      );
    if (url.protocol !== 'https:' && !(localDevelopment && localHost && url.protocol === 'http:'))
      throw new Error();
    return url.origin;
  } catch {
    throw new ApiError('validation');
  }
}
export class ApiTransport {
  private readonly active = new Set<AbortController>();
  readonly client;
  constructor(
    baseURL: string,
    private readonly session: TransportSession,
    private readonly fetcher: typeof fetch = fetch,
    private readonly timeoutMs = 12_000,
    localDevelopment = false,
  ) {
    this.client = createApiClient({
      baseUrl: validateBaseURL(baseURL, localDevelopment),
      fetch: this.send,
    });
  }
  cancelAll() {
    for (const controller of this.active) controller.abort();
    this.active.clear();
  }
  private send = async (request: Request): Promise<Response> => {
    // Phase 8B exposes only resource acquisition. Generated future operations are inert.
    const path = new URL(request.url).pathname;
    if (
      !/^\/api\/v1\/(persons|relationships|conversations)(\/[0-9a-f-]{36})?$/i.test(path) ||
      !['GET', 'POST'].includes(request.method)
    )
      throw new ApiError('validation');
    const epoch = this.session.epoch();
    const controller = new AbortController();
    let timedOut = false;
    const abort = () => controller.abort();
    request.signal.addEventListener('abort', abort);
    if (request.signal.aborted) abort();
    this.active.add(controller);
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, this.timeoutMs);
    let rejectAbort: ((error: ApiError) => void) | undefined;
    const failOnAbort = () => rejectAbort?.(new ApiError(timedOut ? 'timeout' : 'cancelled'));
    try {
      const token = this.session.credential();
      if (epoch !== this.session.epoch()) throw new ApiError('cancelled');
      if (controller.signal.aborted) throw new ApiError('cancelled');
      const headers = new Headers(request.headers);
      headers.delete('Authorization');
      if (token) headers.set('Authorization', `Bearer ${token}`);
      const cancelled = new Promise<never>((_, reject) => {
        rejectAbort = reject;
      });
      controller.signal.addEventListener('abort', failOnAbort);
      // Browser fetch must not receive ApiTransport as its this binding.
      const fetcher = this.fetcher;
      const response = await Promise.race([
        Promise.resolve().then(() => {
          if (controller.signal.aborted) throw new ApiError(timedOut ? 'timeout' : 'cancelled');
          return fetcher(new Request(request, { headers, signal: controller.signal }));
        }),
        cancelled,
      ]);
      if (epoch !== this.session.epoch() || controller.signal.aborted)
        throw new ApiError(timedOut ? 'timeout' : 'cancelled');
      if (!response.ok) {
        if (response.status === 401) this.session.invalidate(epoch);
        // Do not parse/retain raw server errors, tracebacks or private bodies.
        throw httpError(response.status);
      }
      const body = await Promise.race([response.text(), cancelled]);
      if (epoch !== this.session.epoch() || controller.signal.aborted)
        throw new ApiError(timedOut ? 'timeout' : 'cancelled');
      return new Response(body, { status: response.status, headers: response.headers });
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (controller.signal.aborted) throw new ApiError(timedOut ? 'timeout' : 'cancelled');
      throw new ApiError('offline');
    } finally {
      clearTimeout(timer);
      controller.signal.removeEventListener('abort', failOnAbort);
      request.signal.removeEventListener('abort', abort);
      this.active.delete(controller);
    }
  };
}
