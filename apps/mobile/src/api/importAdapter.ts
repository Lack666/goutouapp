import type { components } from './generated/client';
import { ApiError } from './errors';
import { asUUID } from './uuid';
import type { ImportReceiptView, ServerImportJobView } from '../contracts/connectedImport';
import type {
  RelationshipHistoryItemViewModel,
  AgentHistoryItemViewModel,
} from '../contracts/history';

function check(value: unknown): asserts value {
  if (!value) throw new ApiError('protocol');
}
const count = (value: number) => {
  check(Number.isSafeInteger(value) && value >= 0);
  return value;
};
export const awareTimestamp = (value: string) => {
  check(
    typeof value === 'string' &&
      /(?:Z|[+-]\d{2}:\d{2})$/.test(value) &&
      Number.isFinite(Date.parse(value)),
  );
  return value;
};
export function importJobView(
  dto: components['schemas']['ImportJobResponse'],
): ServerImportJobView {
  check(['awaiting_binding', 'ready', 'importing', 'imported', 'cancelled'].includes(dto.status));
  check(
    ['wechat_markdown_v1', 'chatlab_jsonl_v0_0_2'].includes(dto.source_format) &&
      typeof dto.source_timezone === 'string',
  );
  check(Array.isArray(dto.speakers) && dto.speakers.length === dto.speaker_count);
  check(new Set(dto.speakers.map((s) => s.raw_speaker_label)).size === dto.speakers.length);
  return {
    id: asUUID(dto.id),
    status: dto.status as ServerImportJobView['status'],
    artifactState: dto.artifact_state,
    revision: count(dto.binding_revision),
    relationshipId: dto.bound_relationship_id === null ? null : asUUID(dto.bound_relationship_id),
    parserVersion: dto.parser_version,
    schemaVersion: dto.schema_version,
    warningCount: count(dto.warning_count),
    errorCount: count(dto.error_count),
    truncatedIssues: count(dto.issues_truncated),
    issueSamples: dto.issue_code_samples,
    readinessIssues: dto.readiness_issues,
    summary: {
      sourceFormat: dto.source_format,
      sourceTimezone: dto.source_timezone,
      messageCount: count(dto.message_count),
      speakerCount: count(dto.speaker_count),
      firstTimestamp: awareTimestamp(dto.first_timestamp_utc),
      lastTimestamp: awareTimestamp(dto.last_timestamp_utc),
      warnings: dto.issue_code_samples,
      possibleDuplicate:
        dto.possible_duplicate_job_id === null ? null : asUUID(dto.possible_duplicate_job_id),
    },
    speakers: dto.speakers.map((s) => {
      check(typeof s.raw_speaker_label === 'string' && s.raw_speaker_label.length > 0);
      check(['unbound', 'self', 'person', 'system', 'ignore'].includes(s.binding_kind));
      check((s.binding_kind === 'person') === (s.person_id !== null));
      return {
        id: s.raw_speaker_label,
        rawLabel: s.raw_speaker_label,
        sourceLabel: dto.source_format,
        messageCount: count(s.message_count),
        binding: s.binding_kind,
        personId: s.person_id === null ? null : asUUID(s.person_id),
      };
    }),
    receipt:
      dto.receipt === null
        ? null
        : {
            jobId: dto.id,
            datasetId: asUUID(dto.receipt.dataset_job_id),
            relationshipId: asUUID(dto.receipt.relationship_id),
            count: count(dto.receipt.imported_message_count),
            ignored: count(dto.receipt.ignored_message_count),
            system: count(dto.receipt.system_message_count),
            newCount: null,
            status: 'imported_summary',
            importedAt: awareTimestamp(dto.receipt.imported_at),
            firstTimestamp: null,
            lastTimestamp: null,
          },
  };
}
export function importReceiptView(
  dto: components['schemas']['ImportReceiptResponse'],
): ImportReceiptView {
  check(['imported', 'already_imported'].includes(dto.status));
  return {
    jobId: asUUID(dto.import_job_id),
    datasetId: asUUID(dto.dataset_job_id),
    relationshipId: asUUID(dto.relationship_id),
    count: count(dto.imported_message_count),
    ignored: count(dto.ignored_message_count),
    system: count(dto.system_message_count),
    newCount: count(dto.new_message_count),
    status: dto.status,
    importedAt: awareTimestamp(dto.imported_at),
    firstTimestamp: awareTimestamp(dto.first_timestamp_utc),
    lastTimestamp: awareTimestamp(dto.last_timestamp_utc),
  };
}
export function relationshipHistoryView(
  dto: components['schemas']['RelationshipMessageResponse'],
  relationshipId: string,
): RelationshipHistoryItemViewModel {
  check(
    dto.relationship_id === relationshipId &&
      ['self', 'person', 'system'].includes(dto.sender_kind),
  );
  check(typeof dto.content === 'string' && typeof dto.raw_speaker_label === 'string');
  check(typeof dto.original_timestamp === 'string' && typeof dto.source_timezone === 'string');
  check((dto.sender_kind === 'person') === (dto.person_id !== null));
  return {
    kind: 'relationship',
    provenance: 'server',
    id: asUUID(dto.id),
    relationshipId: asUUID(dto.relationship_id),
    content: dto.content,
    timestamp: awareTimestamp(dto.timestamp_utc),
    datasetId: asUUID(dto.import_job_id),
    sourceIndex: count(dto.source_index),
    sender: dto.sender_kind as 'self' | 'person' | 'system',
    rawSpeakerLabel: dto.raw_speaker_label,
    originalTimestamp: dto.original_timestamp,
    sourceTimezone: dto.source_timezone,
    personId: dto.person_id === null ? null : asUUID(dto.person_id),
    contentType: dto.content_type,
    messageFingerprint: dto.message_fingerprint,
  };
}
export function agentHistoryView(
  dto: components['schemas']['AgentMessagePublicResponse'],
  conversationId: string,
  relationshipId: string | null,
): AgentHistoryItemViewModel {
  check(
    dto.conversation_id === conversationId &&
      ['user', 'assistant'].includes(dto.role) &&
      typeof dto.content === 'string',
  );
  return {
    kind: 'agent',
    provenance: 'server',
    id: asUUID(dto.id),
    relationshipId,
    content: dto.content,
    timestamp: awareTimestamp(dto.created_at),
    datasetId: asUUID(conversationId),
    sourceIndex: 0,
    role: dto.role,
  };
}
