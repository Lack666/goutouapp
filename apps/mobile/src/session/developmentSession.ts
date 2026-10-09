import { ApiError, safeError } from '../api/errors';
import { asUUID } from '../api/uuid';
import type { TokenStorage } from './storage';

export type SessionStatus =
  | 'no_token'
  | 'checking'
  | 'authenticated'
  | 'expired'
  | 'invalid'
  | 'network_unavailable'
  | 'storage_error';
export interface SessionView {
  readonly mode: 'demo' | 'connected';
  readonly status: SessionStatus;
  readonly epoch: number;
}
// Local expiry is a UX hint only. Signature, issuer, audience and owner remain server authorities.
function expiry(token: string, now: number): number {
  try {
    const parts = token.split('.');
    if (parts.length !== 3 || parts.some((p) => !/^[A-Za-z0-9_-]+$/.test(p))) throw new Error();
    const payload = JSON.parse(atob(parts[1]!.replace(/-/g, '+').replace(/_/g, '/'))) as Record<
      string,
      unknown
    >;
    if (
      typeof payload.sub !== 'string' ||
      typeof payload.exp !== 'number' ||
      !Number.isFinite(payload.exp)
    )
      throw new Error();
    asUUID(payload.sub);
    if (payload.exp * 1000 <= now) throw new ApiError('unauthorized');
    return payload.exp * 1000;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('validation');
  }
}
export class DevelopmentSession {
  private view: SessionView = { mode: 'demo', status: 'no_token', epoch: 0 };
  private token: string | null = null;
  private expiresAt = 0;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private storageQueue: Promise<void> = Promise.resolve();
  private readonly listeners = new Set<() => void>();
  constructor(
    private readonly storage: TokenStorage,
    private readonly now = Date.now,
  ) {}
  snapshot = () => this.view;
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };
  epoch = () => this.view.epoch;
  credential = () => {
    if (this.token && this.now() >= this.expiresAt) this.reset('connected', 'expired');
    return this.token;
  };
  private publish(view: SessionView) {
    this.view = view;
    for (const listener of this.listeners) listener();
  }
  private store(action: () => Promise<void>) {
    const result = this.storageQueue.then(action);
    this.storageQueue = result.catch(() => undefined);
    return result;
  }
  private reset(mode: SessionView['mode'], status: SessionStatus) {
    clearTimeout(this.timer);
    this.token = null;
    this.expiresAt = 0;
    this.publish({ mode, status, epoch: this.view.epoch + 1 });
    const epoch = this.epoch();
    void this.store(() => this.storage.clear()).catch(() => {
      if (this.epoch() === epoch) this.publish({ ...this.view, status: 'storage_error' });
    });
  }
  logout = () => this.reset('connected', 'no_token');
  demo = () => this.reset('demo', 'no_token');
  connected = () => this.reset('connected', 'no_token');
  invalidate = (epoch: number) => {
    if (epoch === this.epoch())
      this.reset('connected', this.now() >= this.expiresAt ? 'expired' : 'invalid');
  };
  resume = () => {
    this.credential();
  };
  async restore(probe: () => Promise<unknown>) {
    const epoch = this.epoch();
    try {
      const token = await this.storage.read();
      if (epoch === this.epoch() && token) await this.connect(token, probe);
    } catch {
      if (epoch === this.epoch()) this.reset('connected', 'storage_error');
    }
  }
  async connect(input: string, probe: () => Promise<unknown>) {
    this.reset('connected', 'checking');
    const epoch = this.epoch();
    const token = input.trim();
    if (!token) {
      this.reset('connected', 'no_token');
      return;
    }
    try {
      this.expiresAt = expiry(token, this.now());
      this.token = token;
      await probe();
      if (epoch !== this.epoch()) return;
      await this.store(() => this.storage.write(token));
      if (epoch !== this.epoch()) return;
      if (this.now() >= this.expiresAt) {
        this.reset('connected', 'expired');
        return;
      }
      this.publish({ ...this.view, status: 'authenticated' });
      this.timer = setTimeout(
        () => this.reset('connected', 'expired'),
        Math.min(this.expiresAt - this.now(), 2_147_483_647),
      );
    } catch (error) {
      if (epoch !== this.epoch()) return;
      const failure = safeError(error);
      this.reset(
        'connected',
        failure.kind === 'unauthorized'
          ? 'expired'
          : failure.kind === 'validation'
            ? 'invalid'
            : ['offline', 'timeout', 'unavailable'].includes(failure.kind)
              ? 'network_unavailable'
              : 'storage_error',
      );
    }
  }
}
