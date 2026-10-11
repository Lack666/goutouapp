import { createApiClient } from './generated/client';
import { ApiError, httpError } from './errors';
import { agentHTTPError } from './agentErrors';
import { importHTTPError } from './importErrors';
import { memoryHTTPError } from './memoryErrors';
import type { components, UUID } from './generated/client';
import type { AgentEvent } from './agentEvents';
import { consumeSSE } from './sseParser';

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
  private readonly baseURL: string;
  constructor(
    baseURL: string,
    private readonly session: TransportSession,
    private readonly fetcher: typeof fetch = fetch,
    private readonly timeoutMs = 12_000,
    localDevelopment = false,
    private readonly agentEnabled = false,
    private readonly streamingFetcher: typeof fetch = fetcher,
    private readonly agentTimeoutMs = 60_000,
    private readonly importEnabled = false,
    private readonly importTimeoutMs = 120_000,
    private readonly memoryEnabled = false,
  ) {
    this.baseURL = validateBaseURL(baseURL, localDevelopment);
    this.client = createApiClient({
      baseUrl: this.baseURL,
      fetch: this.send,
    });
  }
  cancelAll() {
    for (const controller of this.active) controller.abort();
    this.active.clear();
  }
  private send = async (request: Request): Promise<Response> => {
    return this.perform(request, this.fetcher, async (response, _signal, wait) => {
      const body = await wait(response.text());
      return new Response(body, { status: response.status, headers: response.headers });
    });
  };
  streamAgent(
    conversationId: UUID,
    body: components['schemas']['CreateAgentRunRequest'],
    onEvent: (event: AgentEvent) => void,
    signal: AbortSignal,
  ) {
    return this.perform(
      new Request(`${this.baseURL}/api/v1/conversations/${conversationId}/agent-runs/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify(body),
        signal,
      }),
      this.streamingFetcher,
      (response, signal, wait) => consumeSSE(response, signal, onEvent, wait),
    );
  }
  private async perform<T>(
    request: Request,
    fetcher: typeof fetch,
    consume: (
      response: Response,
      signal: AbortSignal,
      wait: <V>(promise: Promise<V>) => Promise<V>,
    ) => Promise<T>,
  ): Promise<T> {
    const path = new URL(request.url).pathname;
    const isAgent =
      /^\/api\/v1\/conversations\/[0-9a-f-]{36}\/(agent-runs(?:\/stream)?|messages)$/i.test(path);
    const importMethod =
      path === '/api/v1/chat-imports'
        ? 'POST'
        : /^\/api\/v1\/chat-imports\/[0-9a-f-]{36}$/i.test(path)
          ? 'GET'
          : /^\/api\/v1\/chat-imports\/[0-9a-f-]{36}\/(speakers|relationship)$/i.test(path)
            ? 'PUT'
            : /^\/api\/v1\/chat-imports\/[0-9a-f-]{36}\/(ready|finalize|cancel)$/i.test(path)
              ? 'POST'
              : /^\/api\/v1\/relationships\/[0-9a-f-]{36}\/messages$/i.test(path)
                ? 'GET'
                : null;
    const isImport = importMethod !== null;
    const memoryMethod =
      /^\/api\/v1\/(memory\/control|memories(?:\/[0-9a-f-]{36})?|memory\/undo\/preview|memory\/mutations\/[0-9a-f-]{36})$/i.test(
        path,
      )
        ? 'GET'
        : /^\/api\/v1\/memory\/(consent|pause|resume|undo|deletions\/(one|person|all)\/prepare|deletions\/[0-9a-f-]{36}\/execute)$/i.test(
              path,
            )
          ? 'POST'
          : null;
    const isMemory = memoryMethod !== null;
    if (
      !(
        /^\/api\/v1\/(persons|relationships|conversations)(\/[0-9a-f-]{36})?$/i.test(path) &&
        ['GET', 'POST'].includes(request.method)
      ) &&
      !(
        this.agentEnabled &&
        isAgent &&
        request.method === (path.endsWith('/messages') ? 'GET' : 'POST')
      ) &&
      !(this.importEnabled && isImport && request.method === importMethod) &&
      !(this.memoryEnabled && isMemory && request.method === memoryMethod)
    )
      throw new ApiError('validation');
    const epoch = this.session.epoch();
    const controller = new AbortController();
    let timedOut = false;
    const abort = () => controller.abort();
    request.signal.addEventListener('abort', abort);
    if (request.signal.aborted) abort();
    this.active.add(controller);
    const timer = setTimeout(
      () => {
        timedOut = true;
        controller.abort();
      },
      isImport ? this.importTimeoutMs : isAgent ? this.agentTimeoutMs : this.timeoutMs,
    );
    let rejectAbort: ((error: ApiError) => void) | undefined;
    const failOnAbort = () => rejectAbort?.(new ApiError(timedOut ? 'timeout' : 'cancelled'));
    try {
      const token = this.session.credential();
      if (epoch !== this.session.epoch()) throw new ApiError('cancelled');
      if ((isAgent || isImport || isMemory) && !token) throw new ApiError('unauthorized');
      if (controller.signal.aborted) throw new ApiError('cancelled');
      const headers = new Headers(request.headers);
      headers.delete('Authorization');
      if (token) headers.set('Authorization', `Bearer ${token}`);
      const cancelled = new Promise<never>((_, reject) => {
        rejectAbort = reject;
      });
      controller.signal.addEventListener('abort', failOnAbort);
      // Browser fetch must not receive ApiTransport as its this binding.
      const response = await Promise.race([
        Promise.resolve().then(() => {
          if (controller.signal.aborted) throw new ApiError(timedOut ? 'timeout' : 'cancelled');
          return fetcher(
            new Request(request, {
              headers,
              signal: controller.signal,
              redirect: 'error',
              credentials: 'omit',
            }),
          );
        }),
        cancelled,
      ]);
      if (epoch !== this.session.epoch() || controller.signal.aborted)
        throw new ApiError(timedOut ? 'timeout' : 'cancelled');
      if (!response.ok) {
        if (response.status === 401) this.session.invalidate(epoch);
        // Agent recovery uses only allowlisted public codes/IDs; never retain raw messages.
        if (isAgent && response.status !== 401)
          throw agentHTTPError(response.status, await Promise.race([response.text(), cancelled]));
        if (isImport && response.status !== 401)
          throw importHTTPError(response.status, await Promise.race([response.text(), cancelled]));
        if (isMemory && response.status !== 401)
          throw memoryHTTPError(response.status, await Promise.race([response.text(), cancelled]));
        throw httpError(response.status);
      }
      const result = await consume(response, controller.signal, <V>(promise: Promise<V>) =>
        Promise.race([promise, cancelled]),
      );
      if (epoch !== this.session.epoch() || controller.signal.aborted)
        throw new ApiError(timedOut ? 'timeout' : 'cancelled');
      return result;
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
  }
}
