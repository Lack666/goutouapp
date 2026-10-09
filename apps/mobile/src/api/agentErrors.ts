import { ApiError, httpError, type ApiErrorKind } from './errors';
import { asUUID } from './uuid';
import type { UUID } from './generated/client';

export class AgentApiError extends ApiError {
  constructor(
    kind: ApiErrorKind,
    status?: number,
    readonly runId?: UUID,
    readonly recovery?: 'failed' | 'running_unknown',
  ) {
    super(kind, status);
  }
}
export function agentHTTPError(status: number, body: string): ApiError {
  if (body.length > 16_384) return new ApiError('protocol');
  try {
    const value = JSON.parse(body).error as Record<string, unknown>;
    const kinds: Record<string, ApiErrorKind> = {
      invalid_scope: 'invalid_scope',
      invalid_relationship: 'invalid_scope',
      conversation_busy: 'active_run',
      operation_in_progress: 'active_run',
      idempotency_conflict: 'conflict',
      operation_failed: 'operation_failed',
      operation_unresolved: 'operation_unresolved',
      agent_failure: 'agent_failed',
      persistence_failure: 'unavailable',
    };
    const runId = typeof value.run_id === 'string' ? asUUID(value.run_id) : undefined;
    const recovery =
      value.recovery_status === 'failed' || value.recovery_status === 'running_unknown'
        ? value.recovery_status
        : undefined;
    return new AgentApiError(
      Object.hasOwn(kinds, String(value.code))
        ? kinds[String(value.code)]!
        : httpError(status).kind,
      status,
      runId,
      recovery,
    );
  } catch {
    return httpError(status);
  }
}
