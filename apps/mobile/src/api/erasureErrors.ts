import { ApiError, httpError } from './errors';

// Backend-only contract adapter: no controller, automatic retry or App deletion UI.
const messages: Record<string, string> = {
  confirmation_not_found: '服务器删除确认不可用，请重新准备。',
  confirmation_expired: '删除确认已过期，请重新核对服务器范围。',
  confirmation_consumed: '该确认已使用；请查询原操作回执。',
  confirmation_mismatch: '确认与删除目标不一致，不能执行。',
  target_changed: '服务器目标已变化，请重新准备并明确确认。',
  target_busy: '目标仍有运行中或未完成的操作，当前不能删除。',
  target_deleted: '该目标已删除，请刷新历史。',
  idempotency_conflict: '操作标识与原请求不一致，请核对原目标与回执。',
};
export function erasureHTTPError(status: number, text: string): ApiError {
  try {
    const body = JSON.parse(text) as { error?: { code?: unknown } };
    const code = body.error?.code;
    if (typeof code === 'string' && Object.hasOwn(messages, code)) {
      const error = httpError(status);
      error.message = messages[code] ?? error.message;
      return error;
    }
  } catch {
    // Only fixed public messages survive; no exception/input retention.
  }
  return httpError(status);
}
