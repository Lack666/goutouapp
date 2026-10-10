import type {
  ImportSourceSummaryViewModel,
  SpeakerInventoryItemViewModel,
  ImportStep,
} from './import';

export const LOCAL_IMPORT_BYTE_LIMIT = 100 * 1024 * 1024;

export interface ImportFileSummary {
  readonly name: string;
  readonly size: number;
  readonly mimeType: string;
}
// Binary and URI remain private to the controller; never enter snapshots or logs.
export interface SelectedImportFile extends ImportFileSummary {
  binary(): Promise<Blob>;
  release(): void;
}
export interface ServerSpeakerView extends SpeakerInventoryItemViewModel {
  readonly binding: 'unbound' | 'self' | 'person' | 'system' | 'ignore';
  readonly personId: string | null;
}
export interface ImportReceiptView {
  readonly jobId: string;
  readonly datasetId: string;
  readonly relationshipId: string;
  readonly count: number;
  readonly ignored: number;
  readonly system: number;
  readonly newCount: number | null;
  readonly status: 'imported' | 'already_imported' | 'imported_summary';
  readonly importedAt: string;
  readonly firstTimestamp: string | null;
  readonly lastTimestamp: string | null;
}
export interface ServerImportJobView {
  readonly id: string;
  readonly status: 'awaiting_binding' | 'ready' | 'importing' | 'imported' | 'cancelled';
  readonly artifactState: string | null;
  readonly revision: number;
  readonly relationshipId: string | null;
  readonly summary: ImportSourceSummaryViewModel;
  readonly speakers: readonly ServerSpeakerView[];
  readonly readinessIssues: readonly string[];
  readonly warningCount: number;
  readonly errorCount: number;
  readonly truncatedIssues: number;
  readonly issueSamples: readonly string[];
  readonly parserVersion: string;
  readonly schemaVersion: string;
  readonly receipt: ImportReceiptView | null;
}
export type UploadState =
  | 'idle'
  | 'selecting'
  | 'selected'
  | 'uploading'
  | 'job_created'
  | 'failed'
  | 'unknown_outcome'
  | 'cancelled';
export interface ConnectedImportView {
  readonly step: ImportStep;
  readonly upload: UploadState;
  readonly file: ImportFileSummary | null;
  readonly timezone: string;
  readonly scopeId: string | null;
  readonly scope: 'idle' | 'loading' | 'ready' | 'error';
  readonly job: ServerImportJobView | null;
  readonly receipt: ImportReceiptView | null;
  readonly action: 'idle' | 'inspect' | 'binding' | 'ready' | 'finalize' | 'cancel';
  readonly outcome:
    | 'known'
    | 'unknown_finalize_outcome'
    | 'unknown_cancel_outcome'
    | 'unknown_binding_outcome';
  readonly confirmations: readonly string[];
  readonly relationshipConfirmed: boolean;
  readonly error: string | null;
}
