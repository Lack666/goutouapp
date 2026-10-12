import { ApiError } from './errors';
import { validateAgentEvent, type AgentEvent } from './agentEvents';
import { nativeSseObserver } from '../diagnostics/nativeSseObserver';

export class SSEParser {
  private readonly decoder = new TextDecoder('utf-8', { fatal: true });
  private line = '';
  private name = '';
  private data: string[] = [];
  private frameBytes = 0;
  private totalBytes = 0;
  private afterCR = false;
  private ended = false;
  constructor(
    private readonly onEvent: (event: AgentEvent) => void,
    private readonly maxFrame = 128 * 1024,
    private readonly maxTotal = 512 * 1024,
  ) {}
  push(bytes: Uint8Array) {
    if (this.ended) throw new ApiError('protocol');
    this.totalBytes += bytes.byteLength;
    if (this.totalBytes > this.maxTotal) throw new ApiError('protocol');
    let text: string;
    try {
      text = this.decoder.decode(bytes, { stream: true });
    } catch {
      throw new ApiError('protocol');
    }
    this.process(text);
  }
  finish() {
    let text: string;
    try {
      text = this.decoder.decode();
    } catch {
      throw new ApiError('protocol');
    }
    this.process(text);
    this.ended = true;
    // V1 requires a blank-line delimiter. An unterminated final frame is incomplete.
    if (this.line || this.data.length || this.name) throw new ApiError('incomplete_stream');
  }
  private process(text: string) {
    for (const char of text) {
      if (this.afterCR) {
        this.afterCR = false;
        if (char === '\n') continue;
      }
      if (char === '\r' || char === '\n') {
        this.processLine();
        this.afterCR = char === '\r';
      } else {
        this.line += char;
        if (this.line.length > this.maxFrame) throw new ApiError('protocol');
      }
    }
    if (this.frameBytes + new TextEncoder().encode(this.line).byteLength > this.maxFrame)
      throw new ApiError('protocol');
  }
  private processLine() {
    const line = this.line;
    this.line = '';
    this.frameBytes += new TextEncoder().encode(line).byteLength + 1;
    if (this.frameBytes > this.maxFrame) throw new ApiError('protocol');
    if (!line) {
      if (this.data.length) {
        let value: unknown;
        try {
          value = JSON.parse(this.data.join('\n'));
        } catch {
          throw new ApiError('protocol');
        }
        const event = validateAgentEvent(this.name, value);
        this.onEvent(event);
      } else if (this.name) throw new ApiError('protocol');
      this.name = '';
      this.data = [];
      this.frameBytes = 0;
      return;
    }
    if (line.startsWith(':')) return; // Harmless comment; server V1 does not emit heartbeat events.
    const colon = line.indexOf(':');
    const field = colon < 0 ? line : line.slice(0, colon);
    const value = colon < 0 ? '' : line.slice(colon + 1).replace(/^ /, '');
    if (field === 'data') this.data.push(value);
    else if (field === 'event' && !this.name) this.name = value;
    else throw new ApiError('protocol'); // id/retry/extensions are outside the controlled V1 protocol.
  }
}

export async function consumeSSE(
  response: Response,
  signal: AbortSignal,
  onEvent: (event: AgentEvent) => void,
  wait: <T>(promise: Promise<T>) => Promise<T>,
) {
  if (
    response.headers.get('Content-Type')?.split(';')[0]?.trim().toLowerCase() !==
      'text/event-stream' ||
    !response.body
  ) {
    void response.body?.cancel().catch(() => undefined);
    throw new ApiError('protocol');
  }
  const reader = response.body.getReader();
  const observation = nativeSseObserver.ticket(response);
  let terminal = false;
  const cancel = () => {
    nativeSseObserver.reader(observation, 'cancels');
    void reader.cancel().catch(() => undefined);
  };
  signal.addEventListener('abort', cancel);
  const parser = new SSEParser((event) => {
    if (signal.aborted) throw new ApiError('cancelled');
    if (terminal) throw new ApiError('protocol');
    onEvent(event);
    nativeSseObserver.event(observation, event);
    if (event.event === 'completed' || event.event === 'failed') terminal = true;
  });
  try {
    while (!terminal) {
      nativeSseObserver.reader(observation, 'reads');
      const result = await wait(reader.read());
      if (signal.aborted) throw new ApiError('cancelled');
      if (result.done) {
        parser.finish();
        throw new ApiError('incomplete_stream');
      }
      parser.push(result.value);
    }
    // A terminal event is the protocol's completion, not a requirement to wait for socket EOF.
    parser.finish();
  } catch (error) {
    nativeSseObserver.interrupted(observation, signal.aborted);
    throw error;
  } finally {
    signal.removeEventListener('abort', cancel);
    cancel();
    try {
      reader.releaseLock();
      nativeSseObserver.reader(observation, 'releases');
    } catch {
      /* A native pending read can settle after cancellation. */
    }
  }
}
