import type { components, UUID } from './generated/client';
import { ApiError } from './errors';
import { wireUUID } from './uuid';

// SSE is a string in OpenAPI. This narrow V1 union mirrors schemas/stream_event.py.
export type MemoryStatus = components['schemas']['MemoryWriteStatus'];
export const memoryStatuses: readonly MemoryStatus[] = [
  'none',
  'saved',
  'duplicate',
  'skipped_no_consent',
  'skipped_paused',
  'rejected_validation',
  'pending_confirmation',
  'control_updated',
  'failed',
  'undone',
  'nothing_to_undo',
];
export const progressStatuses = [
  'preparing',
  'checking_safety',
  'understanding_request',
  'loading_context',
  'analyzing',
  'planning',
  'composing',
  'preparing_safety_response',
  'updating_memory',
] as const;
export type ProgressStatus = (typeof progressStatuses)[number];
type EventData = {
  run_started: Record<string, never>;
  status: { status: ProgressStatus };
  final_response: { assistant_message_id: UUID; answer: string };
  memory_status: { status: MemoryStatus };
  pending_confirmation: { status: 'pending_confirmation' };
  completed: { status: 'completed'; assistant_message_id: UUID; memory_status: MemoryStatus };
  failed: {
    code: 'agent_failure' | 'persistence_failure';
    recovery_status: 'failed' | 'running_unknown';
  };
};
export type AgentEvent = {
  [K in keyof EventData]: { schema_version: '1'; event: K; run_id: UUID; data: EventData[K] };
}[keyof EventData];
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new ApiError('protocol');
  return value as Record<string, unknown>;
}
function exact(value: Record<string, unknown>, fields: string[]) {
  if (Object.keys(value).length !== fields.length || fields.some((key) => !(key in value)))
    throw new ApiError('protocol');
}
export function validateAgentEvent(name: string, input: unknown): AgentEvent {
  const envelope = record(input);
  if (envelope.schema_version !== '1') throw new ApiError('unsupported_version');
  exact(envelope, ['schema_version', 'event', 'run_id', 'data']);
  if (envelope.event !== name || typeof envelope.run_id !== 'string')
    throw new ApiError('protocol');
  wireUUID(envelope.run_id);
  const data = record(envelope.data);
  const memory = (value: unknown) => memoryStatuses.includes(value as MemoryStatus);
  switch (name) {
    case 'run_started':
      exact(data, []);
      break;
    case 'status':
      exact(data, ['status']);
      if (!progressStatuses.includes(data.status as ProgressStatus)) throw new ApiError('protocol');
      break;
    case 'final_response':
      exact(data, ['assistant_message_id', 'answer']);
      if (
        typeof data.assistant_message_id !== 'string' ||
        typeof data.answer !== 'string' ||
        !data.answer ||
        data.answer.length > 100_000
      )
        throw new ApiError('protocol');
      wireUUID(data.assistant_message_id);
      break;
    case 'memory_status':
      exact(data, ['status']);
      if (!memory(data.status)) throw new ApiError('protocol');
      break;
    case 'pending_confirmation':
      exact(data, ['status']);
      if (data.status !== name) throw new ApiError('protocol');
      break;
    case 'completed':
      exact(data, ['status', 'assistant_message_id', 'memory_status']);
      if (
        data.status !== name ||
        typeof data.assistant_message_id !== 'string' ||
        !memory(data.memory_status)
      )
        throw new ApiError('protocol');
      wireUUID(data.assistant_message_id);
      break;
    case 'failed':
      exact(data, ['code', 'recovery_status']);
      if (
        !['agent_failure', 'persistence_failure'].includes(String(data.code)) ||
        !['failed', 'running_unknown'].includes(String(data.recovery_status))
      )
        throw new ApiError('protocol');
      break;
    default:
      throw new ApiError('protocol'); // V1 unknown events fail closed; no silent reinterpretation.
  }
  return envelope as AgentEvent;
}
