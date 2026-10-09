export type ApiErrorKind =
  | 'unauthorized'
  | 'not_found'
  | 'conflict'
  | 'validation'
  | 'unavailable'
  | 'timeout'
  | 'offline'
  | 'cancelled'
  | 'protocol';
const messages: Record<ApiErrorKind, string> = {
  unauthorized: '开发凭证已过期或无效，请重新获取。',
  not_found: '资源不存在或不属于当前会话。',
  conflict: '创建标识与原请求不一致，请核对后开始新的创建。',
  validation: '字段或分页信息无效，请核对输入。',
  unavailable: '服务器暂时不可用，请稍后重试。',
  timeout: '请求超时，提交结果可能未知；创建重试将保留原请求。',
  offline: '网络不可用，提交结果可能未知；请检查连接后重试。',
  cancelled: '请求已取消。',
  protocol: '服务器响应无法读取，请重试。',
};
export class ApiError extends Error {
  constructor(
    readonly kind: ApiErrorKind,
    readonly status?: number,
  ) {
    super(messages[kind]);
    this.name = 'ApiError';
  }
}
export function httpError(status: number) {
  const kind =
    status === 401
      ? 'unauthorized'
      : status === 404
        ? 'not_found'
        : status === 409
          ? 'conflict'
          : status === 422
            ? 'validation'
            : 'unavailable';
  return new ApiError(kind, status);
}
export const safeError = (error: unknown) =>
  error instanceof ApiError ? error : new ApiError('protocol');
