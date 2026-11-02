import { ApiTransport } from '../api/transport';
import { ApiError, safeError } from '../api/errors';
import { ImportHTTPError } from '../api/importErrors';
import { asUUID } from '../api/uuid';
import { importJobView, importReceiptView } from '../api/importAdapter';
import type { components } from '../api/generated/client';
import {
  LOCAL_IMPORT_BYTE_LIMIT,
  type ConnectedImportView,
  type SelectedImportFile,
} from '../contracts/connectedImport';
import type { ImportStep } from '../contracts/import';
import type { DevelopmentSession } from '../session/developmentSession';

export { LOCAL_IMPORT_BYTE_LIMIT } from '../contracts/connectedImport';
export function validateImportFile(file: SelectedImportFile) {
  if (!/\.(md|markdown|jsonl)$/i.test(file.name)) throw new ApiError('unsupported_file');
  if (!Number.isSafeInteger(file.size) || file.size <= 0) throw new ApiError('file_unreadable');
  if (file.size > LOCAL_IMPORT_BYTE_LIMIT) throw new ApiError('file_too_large');
}
export function validateSourceTimezone(value: string) {
  if (
    value !== value.trim() ||
    !(value === 'UTC' || /^[A-Za-z_+-]+(?:\/[A-Za-z0-9_+-]+)+$/.test(value))
  )
    throw new ApiError('validation');
  try {
    new Intl.DateTimeFormat('en', { timeZone: value }).format();
  } catch {
    throw new ApiError('validation');
  }
}
function emptyView(scopeId: string | null = null): ConnectedImportView {
  return {
    step: 'source',
    upload: 'idle',
    file: null,
    timezone: 'Asia/Shanghai',
    sourceFormat: 'wechat_markdown_v1',
    scopeId,
    scope: 'idle',
    job: null,
    receipt: null,
    action: 'idle',
    outcome: 'known',
    confirmations: [],
    relationshipConfirmed: false,
    error: null,
  };
}
const uncertain = (error: ApiError) =>
  (error.status === undefined &&
    ['offline', 'timeout', 'cancelled', 'protocol', 'incomplete_stream'].includes(error.kind)) ||
  (error.status !== undefined && error.status >= 500);
export class ImportController {
  private view = emptyView();
  private file: SelectedImportFile | null = null;
  private request: AbortController | null = null;
  private generation = 0;
  private pickGeneration = 0;
  private epoch: number;
  private routeScope: string | null | undefined;
  private personId: string | null = null;
  private readonly listeners = new Set<() => void>();
  constructor(
    private readonly transport: ApiTransport,
    private readonly session: DevelopmentSession,
  ) {
    this.epoch = session.epoch();
    session.subscribe(() => {
      if (this.epoch !== session.epoch()) {
        this.epoch = session.epoch();
        this.clear();
        this.routeScope = undefined;
      }
    });
  }
  snapshot = () => this.view;
  format(value: ConnectedImportView['sourceFormat']) {
    if (!this.view.job && this.view.upload !== 'uploading') this.patch({ sourceFormat: value });
  }
  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => {
      this.listeners.delete(fn);
    };
  };
  private patch(value: Partial<ConnectedImportView>) {
    this.view = { ...this.view, ...value };
    for (const fn of this.listeners) fn();
  }
  private authenticated() {
    return this.session.snapshot().status === 'authenticated' && this.session.credential() !== null;
  }
  private releaseFile() {
    this.file?.release();
    this.file = null;
  }
  clear = () => {
    this.generation++;
    this.pickGeneration++;
    this.request?.abort();
    this.request = null;
    this.releaseFile();
    this.personId = null;
    this.view = emptyView();
    this.patch({});
  };
  async open(scope: string | null) {
    if (!this.authenticated()) return;
    if (this.routeScope !== scope) {
      this.clear();
      this.routeScope = scope;
    }
    if (scope && this.view.scope === 'idle') await this.chooseRelationship(scope);
    if (this.view.job) await this.inspect();
  }
  async chooseRelationship(value: string) {
    if (!this.authenticated() || this.request) return;
    this.personId = null;
    this.patch({
      scopeId: value,
      scope: 'loading',
      confirmations: [],
      relationshipConfirmed: false,
      error: null,
      ...(this.view.job && value !== this.view.scopeId ? { step: 'speakers' as const } : {}),
    });
    const generation = ++this.generation;
    const request = new AbortController();
    this.request = request;
    try {
      const id = asUUID(value);
      const { data } = await this.transport.client.GET('/api/v1/relationships/{relationship_id}', {
        params: { path: { relationship_id: id } },
        signal: request.signal,
      });
      if (generation !== this.generation) return;
      if (!data || data.id !== id) throw new ApiError('protocol');
      this.personId = asUUID(data.person_id);
      this.patch({ scope: 'ready' });
    } catch (error) {
      if (generation === this.generation)
        this.patch({ scope: 'error', error: safeError(error).message });
    } finally {
      if (this.request === request) this.request = null;
    }
  }
  timezone(value: string) {
    if (!this.request && !this.view.job) this.patch({ timezone: value, error: null });
  }
  async select(picker: () => Promise<SelectedImportFile | null>) {
    if (
      !this.authenticated() ||
      this.request ||
      this.view.job ||
      this.view.upload === 'unknown_outcome'
    )
      return;
    const pick = ++this.pickGeneration;
    const epoch = this.session.epoch();
    this.patch({ upload: 'selecting', error: null });
    try {
      // Called synchronously from the user gesture (required on Web).
      const file = await picker();
      if (pick !== this.pickGeneration || epoch !== this.session.epoch()) {
        file?.release();
        return;
      }
      if (!file) {
        this.patch({ upload: this.file ? 'selected' : 'cancelled' });
        return;
      }
      try {
        validateImportFile(file);
      } catch (error) {
        file.release();
        throw error;
      }
      this.releaseFile();
      this.file = file;
      this.patch({
        file: { name: file.name, size: file.size, mimeType: file.mimeType },
        upload: 'selected',
        outcome: 'known',
      });
    } catch (error) {
      if (pick === this.pickGeneration && epoch === this.session.epoch())
        this.patch({ upload: 'failed', error: safeError(error).message });
    }
  }
  cancelSelection = () => {
    this.pickGeneration++;
    this.patch({ upload: this.file ? 'selected' : 'cancelled' });
  };
  async upload() {
    if (
      !this.authenticated() ||
      this.request ||
      !this.file ||
      this.view.job ||
      this.view.upload !== 'selected' ||
      this.view.scope === 'error'
    )
      return;
    try {
      validateImportFile(this.file);
      validateSourceTimezone(this.view.timezone);
    } catch (error) {
      this.patch({ error: safeError(error).message });
      return;
    }
    const generation = ++this.generation;
    const request = new AbortController();
    this.request = request;
    const file = this.file;
    const timezone = this.view.timezone;
    const sourceFormat = this.view.sourceFormat;
    let sent = false;
    this.patch({ upload: 'uploading', error: null });
    try {
      const binary = await file.binary();
      if (generation !== this.generation || request.signal.aborted) return;
      if (binary.size !== file.size) throw new ApiError('file_unreadable');
      const form = new FormData();
      form.append('file', binary, file.name);
      form.append('source_timezone', timezone);
      form.append('source_format', sourceFormat);
      // OpenAPI binary is generated as string; serializer replaces only that representation
      // with the binary form. No URI, JSON/base64 or hand-written boundary is transmitted.
      const body: components['schemas']['Body_upload_chat_import_api_v1_chat_imports_post'] = {
        file: '',
        source_timezone: timezone,
        source_format: sourceFormat,
      };
      sent = true;
      const { data } = await this.transport.client.POST('/api/v1/chat-imports', {
        body,
        bodySerializer: () => form,
        signal: request.signal,
      });
      if (generation !== this.generation) return;
      if (!data) throw new ApiError('protocol');
      const job = importJobView(data);
      this.patch({ job, upload: 'job_created', step: 'speakers', error: null });
      this.releaseFile();
    } catch (error) {
      if (generation === this.generation) {
        const failure = safeError(error);
        const unknown = sent && uncertain(failure);
        this.patch({
          upload: unknown ? 'unknown_outcome' : 'failed',
          error: unknown
            ? 'unknown_upload_outcome：服务器可能已创建任务，未收到 Job ID。不会自动重新上传；请核对服务器后再主动开始新导入。'
            : failure.message,
        });
      }
    } finally {
      if (this.request === request) this.request = null;
    }
    if (this.view.job && generation === this.generation) await this.inspect();
  }
  pause = () => {
    this.pickGeneration++;
    if (this.view.upload === 'selecting')
      this.patch({ upload: this.file ? 'selected' : 'cancelled' });
    if (!this.request) return;
    this.generation++;
    this.request.abort();
    this.request = null;
    const action = this.view.action;
    this.patch({
      action: 'idle',
      ...(this.view.upload === 'uploading' ? { upload: 'unknown_outcome' as const } : {}),
      outcome:
        action === 'finalize'
          ? 'unknown_finalize_outcome'
          : action === 'cancel'
            ? 'unknown_cancel_outcome'
            : action === 'binding'
              ? 'unknown_binding_outcome'
              : this.view.outcome,
      error:
        this.view.upload === 'uploading'
          ? 'unknown_upload_outcome：已停止等待；服务器可能已创建任务，不会自动重传。'
          : '客户端已停止等待，未确认服务器取消。已知 Job 可重新读取。',
    });
  };
  leave = () => {
    this.pause();
    if (this.file && this.view.upload !== 'unknown_outcome')
      this.patch({ upload: 'failed', error: '离开页面已释放临时文件，请主动重新选择。' });
    this.releaseFile();
  };
  private async perform(
    action: ConnectedImportView['action'],
    operation: (signal: AbortSignal) => Promise<void>,
  ) {
    if (!this.authenticated() || this.request || !this.view.job) return;
    const epoch = this.session.epoch();
    const jobId = this.view.job.id;
    const generation = ++this.generation;
    const request = new AbortController();
    this.request = request;
    this.patch({ action, error: null });
    let reinspect = false;
    let displayError: string | null = null;
    try {
      // Each operation checks generation before committing its adapted result.
      await operation(request.signal);
    } catch (error) {
      if (generation === this.generation) {
        const failure = safeError(error);
        displayError = failure.message;
        const unknown = uncertain(failure) && action !== 'inspect';
        this.patch({
          error: failure.message,
          outcome: unknown
            ? action === 'finalize'
              ? 'unknown_finalize_outcome'
              : action === 'cancel'
                ? 'unknown_cancel_outcome'
                : 'unknown_binding_outcome'
            : this.view.outcome,
        });
        if (
          action === 'binding' ||
          (failure instanceof ImportHTTPError && failure.code === 'stale_revision')
        )
          this.patch({ confirmations: [], relationshipConfirmed: false });
        reinspect = action !== 'inspect';
      }
    } finally {
      if (this.request === request) {
        this.request = null;
        this.patch({ action: 'idle' });
      }
    }
    if (reinspect && generation === this.generation) {
      const inspectionGeneration = this.generation + 1;
      await this.inspect();
      if (
        epoch !== this.session.epoch() ||
        this.view.job?.id !== jobId ||
        this.generation !== inspectionGeneration
      )
        return;
      if (this.view.outcome !== 'known' || !this.view.receipt)
        this.patch({ error: displayError ?? this.view.error });
    }
  }
  private acceptJob(dto: components['schemas']['ImportJobResponse'], signal: AbortSignal) {
    if (signal.aborted || !this.authenticated()) return;
    const job = importJobView(dto);
    if (job.id !== this.view.job?.id) throw new ApiError('protocol');
    const changed = this.view.job.revision !== job.revision;
    this.patch({
      job,
      ...(changed ? { confirmations: [], relationshipConfirmed: false } : {}),
      ...(job.receipt ? { receipt: job.receipt, step: 'result', outcome: 'known' } : {}),
      ...(job.status === 'cancelled' ? { outcome: 'known' } : {}),
    });
  }
  inspect = async () => {
    const job = this.view.job;
    if (!job) return;
    await this.perform('inspect', async (signal) => {
      const { data } = await this.transport.client.GET('/api/v1/chat-imports/{job_id}', {
        params: { path: { job_id: asUUID(job.id) } },
        signal,
      });
      if (!data) throw new ApiError('protocol');
      this.acceptJob(data, signal);
    });
  };
  async recoverJob(value: string) {
    if (!this.authenticated() || this.request) return;
    const generation = ++this.generation;
    const request = new AbortController();
    this.request = request;
    this.patch({ action: 'inspect', error: null, confirmations: [], relationshipConfirmed: false });
    try {
      const { data } = await this.transport.client.GET('/api/v1/chat-imports/{job_id}', {
        params: { path: { job_id: asUUID(value) } },
        signal: request.signal,
      });
      if (!data) throw new ApiError('protocol');
      const job = importJobView(data);
      if (this.routeScope && job.relationshipId && job.relationshipId !== this.routeScope)
        throw new ApiError('invalid_scope');
      if (generation !== this.generation) return;
      this.releaseFile();
      this.patch({
        job,
        receipt: job.receipt,
        file: null,
        upload: 'job_created',
        step: job.receipt ? 'result' : 'speakers',
        scopeId: job.relationshipId ?? this.view.scopeId,
        scope: 'idle',
        outcome: 'known',
      });
    } catch (error) {
      if (generation === this.generation) this.patch({ error: safeError(error).message });
    } finally {
      if (this.request === request) {
        this.request = null;
        this.patch({ action: 'idle' });
      }
    }
    if (generation === this.generation && this.view.scopeId)
      await this.chooseRelationship(this.view.scopeId);
  }
  async bindSpeaker(
    label: string,
    kind: 'self' | 'person' | 'system' | 'ignore',
    personId: string | null = null,
  ) {
    const job = this.view.job;
    if (!job || !job.speakers.some((s) => s.rawLabel === label)) return;
    await this.perform('binding', async (signal) => {
      const body: components['schemas']['SpeakerBindingRequest'] = {
        raw_speaker_label: label,
        binding_kind: kind,
        person_id: kind === 'person' ? asUUID(personId ?? '') : null,
        expected_revision: job.revision,
      };
      const { data } = await this.transport.client.PUT('/api/v1/chat-imports/{job_id}/speakers', {
        params: { path: { job_id: asUUID(job.id) } },
        body,
        signal,
      });
      if (!data) throw new ApiError('protocol');
      const confirmed = this.view.confirmations;
      this.acceptJob(data, signal);
      if (!signal.aborted)
        this.patch({
          confirmations: [...new Set([...confirmed, label])],
          relationshipConfirmed: false,
          outcome: 'known',
        });
    });
  }
  async confirmRelationship() {
    const job = this.view.job;
    if (!job || this.view.scope !== 'ready' || !this.view.scopeId) return;
    await this.perform('binding', async (signal) => {
      if (job.speakers.some((s) => s.binding === 'person' && s.personId !== this.personId))
        throw new ApiError('binding_mismatch');
      const { data } = await this.transport.client.PUT(
        '/api/v1/chat-imports/{job_id}/relationship',
        {
          params: { path: { job_id: asUUID(job.id) } },
          body: { relationship_id: asUUID(this.view.scopeId!), expected_revision: job.revision },
          signal,
        },
      );
      if (!data) throw new ApiError('protocol');
      const confirmations = this.view.confirmations;
      this.acceptJob(data, signal);
      if (!signal.aborted)
        this.patch({
          confirmations,
          relationshipConfirmed: true,
          outcome: 'known',
          step: 'readiness',
        });
    });
  }
  private confirmed() {
    return (
      this.view.relationshipConfirmed &&
      this.view.job?.speakers.every((s) => this.view.confirmations.includes(s.rawLabel))
    );
  }
  async ready() {
    const job = this.view.job;
    if (!job || !this.confirmed()) return;
    await this.perform('ready', async (signal) => {
      const { data } = await this.transport.client.POST('/api/v1/chat-imports/{job_id}/ready', {
        params: { path: { job_id: asUUID(job.id) } },
        signal,
      });
      if (!data) throw new ApiError('protocol');
      this.acceptJob(data, signal);
      if (!signal.aborted) this.patch({ outcome: 'known' });
    });
  }
  async finalize() {
    const epoch = this.session.epoch();
    const job = this.view.job;
    if (!job || !(job.status === 'imported' || (job.status === 'ready' && this.confirmed())))
      return;
    await this.perform('finalize', async (signal) => {
      const { data } = await this.transport.client.POST('/api/v1/chat-imports/{job_id}/finalize', {
        params: { path: { job_id: asUUID(job.id) } },
        body: { expected_revision: job.revision },
        signal,
      });
      if (!data) throw new ApiError('protocol');
      const receipt = importReceiptView(data);
      if (receipt.jobId !== job.id || receipt.relationshipId !== job.relationshipId)
        throw new ApiError('protocol');
      if (!signal.aborted) this.patch({ receipt, step: 'result', outcome: 'known' });
    });
    if (epoch === this.session.epoch() && this.view.job?.id === job.id && this.view.receipt) {
      const fullReceipt = this.view.receipt;
      await this.inspect();
      if (
        epoch === this.session.epoch() &&
        this.view.job?.id === fullReceipt.jobId &&
        this.authenticated()
      )
        this.patch({ receipt: fullReceipt });
    }
  }
  async cancel() {
    const job = this.view.job;
    if (!job) return;
    await this.perform('cancel', async (signal) => {
      const { data } = await this.transport.client.POST('/api/v1/chat-imports/{job_id}/cancel', {
        params: { path: { job_id: asUUID(job.id) } },
        signal,
      });
      if (!data) throw new ApiError('protocol');
      this.acceptJob(data, signal);
      if (!signal.aborted && data.status === 'cancelled')
        this.patch({ outcome: 'known', error: '服务器已确认取消任务。' });
    });
  }
  step(step: ImportStep) {
    if (!this.request) this.patch({ step });
  }
  newImport = () => {
    if (!this.request) {
      const scope = this.view.scopeId;
      this.clear();
      if (scope) void this.chooseRelationship(scope);
    }
  };
}
