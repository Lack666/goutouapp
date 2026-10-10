import { ApiError, httpError } from './errors';

const messages: Record<string, string> = {
  invalid_upload: '文件或历史分页信息无效，请核对格式和源时区。',
  upload_too_large: '文件超过服务器大小限制。',
  unsupported_format: '仅支持版本化微信 Markdown v1。',
  parse_failed: '服务器无法解析该文件，请检查 Markdown v1 格式及源时区。',
  stale_revision: '服务器绑定已改变，已重新读取；请重新确认身份和关系。',
  binding_invalid: '绑定无效，或任务已取消／已完成；请读取任务当前状态。',
  job_not_ready: '服务器预检未通过，请处理说话人和关系问题。',
  artifact_unavailable: '源文件已过期、被清理或暂不可读；请读取任务状态。',
  transcript_mismatch: '源文件与服务器任务不匹配，无法导入。',
  import_failed: '服务器导入暂不可用，请先读取任务状态再决定下一步。',
};
export class ImportHTTPError extends ApiError {
  constructor(
    readonly code: string,
    status: number,
  ) {
    super(httpError(status).kind, status);
    this.message = messages[code] ?? httpError(status).message;
  }
}
export function importHTTPError(status: number, text: string) {
  try {
    const body = JSON.parse(text) as { error?: { code?: unknown } };
    if (typeof body.error?.code === 'string' && Object.hasOwn(messages, body.error.code))
      return new ImportHTTPError(body.error.code, status);
  } catch {
    /* Never retain raw errors or private content. */
  }
  return httpError(status);
}
