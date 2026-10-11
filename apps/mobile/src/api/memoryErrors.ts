import { ApiError, httpError } from './errors';
const messages: Record<string, string> = {
  stale_undo: '操作目标已发生变化，请重新检查。',
  undo_unavailable: '操作目标已发生变化，请重新检查。',
  confirmation_stale: '操作目标已发生变化，请重新检查。',
  confirmation_expired: '服务器确认已过期，请重新准备并确认。',
  confirmation_required: '服务器确认不存在、已消费或不可用，请重新检查。',
  mutation_conflict: '操作标识与原请求冲突，请重新检查；没有自动执行其它目标。',
  memory_not_found: '记忆不存在或不属于当前会话。',
  person_not_found: '对象不存在或不属于当前会话。',
  mutation_not_found: '回执不存在或不属于当前会话。',
  persistence_failure: '服务器暂不可用，操作结果可能未知，请保留原请求。',
  invalid_operation_key: '操作标识无效，请核对请求。',
};
export class MemoryHTTPError extends ApiError {
  constructor(
    readonly code: string,
    status: number,
  ) {
    super(httpError(status).kind, status);
    this.message = messages[code] ?? httpError(status).message;
  }
}
export function memoryHTTPError(status: number, value: string) {
  try {
    const body = JSON.parse(value) as { error?: { code?: unknown } };
    if (typeof body.error?.code === 'string' && Object.hasOwn(messages, body.error.code))
      return new MemoryHTTPError(body.error.code, status);
  } catch {
    /* Private server messages never enter UI or storage. */
  }
  return httpError(status);
}
