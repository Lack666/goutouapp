// Generated from docs/contracts/openapi.json. DO NOT EDIT.
// Input SHA256: 492f8273938c3d248f2ce636f1de309645f9fd6357c72465cdabb83b945ed8b1
import createClient, { type ClientOptions } from 'openapi-fetch';
export type UUID = `${string}-${string}-${string}-${string}-${string}`;
export interface paths {
  '/api/v1/chat-imports': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Upload Chat Import */
    post: operations['upload_chat_import_api_v1_chat_imports_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/chat-imports/{job_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Inspect Chat Import */
    get: operations['inspect_chat_import_api_v1_chat_imports__job_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/chat-imports/{job_id}/cancel': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Cancel Chat Import */
    post: operations['cancel_chat_import_api_v1_chat_imports__job_id__cancel_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/chat-imports/{job_id}/finalize': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Finalize Chat Import */
    post: operations['finalize_chat_import_api_v1_chat_imports__job_id__finalize_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/chat-imports/{job_id}/ready': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Mark Chat Import Ready */
    post: operations['mark_chat_import_ready_api_v1_chat_imports__job_id__ready_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/chat-imports/{job_id}/relationship': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    /** Bind Relationship */
    put: operations['bind_relationship_api_v1_chat_imports__job_id__relationship_put'];
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/chat-imports/{job_id}/speakers': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    /** Bind Speaker */
    put: operations['bind_speaker_api_v1_chat_imports__job_id__speakers_put'];
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/conversations': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Conversations */
    get: operations['list_conversations_api_v1_conversations_get'];
    put?: never;
    /** Create Conversation */
    post: operations['create_conversation_api_v1_conversations_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/conversations/{conversation_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Conversation */
    get: operations['get_conversation_api_v1_conversations__conversation_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/conversations/{conversation_id}/agent-runs': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Create Agent Run */
    post: operations['create_agent_run_api_v1_conversations__conversation_id__agent_runs_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/conversations/{conversation_id}/agent-runs/stream': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Stream Agent Run */
    post: operations['stream_agent_run_api_v1_conversations__conversation_id__agent_runs_stream_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/conversations/{conversation_id}/messages': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Agent Messages */
    get: operations['list_agent_messages_api_v1_conversations__conversation_id__messages_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/memories': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Inspect Memories */
    get: operations['inspect_memories_api_v1_memories_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/memories/{memory_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Inspect Memory */
    get: operations['inspect_memory_api_v1_memories__memory_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/memory/consent': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Change Consent */
    post: operations['change_consent_api_v1_memory_consent_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/memory/control': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Inspect Control */
    get: operations['inspect_control_api_v1_memory_control_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/memory/deletions/all/prepare': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Prepare Delete All */
    post: operations['prepare_delete_all_api_v1_memory_deletions_all_prepare_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/memory/deletions/one/prepare': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Prepare Delete One */
    post: operations['prepare_delete_one_api_v1_memory_deletions_one_prepare_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/memory/deletions/person/prepare': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Prepare Delete Person */
    post: operations['prepare_delete_person_api_v1_memory_deletions_person_prepare_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/memory/deletions/{confirmation_id}/execute': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Execute Delete */
    post: operations['execute_delete_api_v1_memory_deletions__confirmation_id__execute_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/memory/mutations/{mutation_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Inspect Mutation */
    get: operations['inspect_mutation_api_v1_memory_mutations__mutation_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/memory/pause': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Pause */
    post: operations['pause_api_v1_memory_pause_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/memory/resume': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Resume */
    post: operations['resume_api_v1_memory_resume_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/memory/undo': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Undo Memory */
    post: operations['undo_memory_api_v1_memory_undo_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/memory/undo/preview': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Preview Undo */
    get: operations['preview_undo_api_v1_memory_undo_preview_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/persons': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Persons */
    get: operations['list_persons_api_v1_persons_get'];
    put?: never;
    /** Create Person */
    post: operations['create_person_api_v1_persons_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/persons/{person_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Person */
    get: operations['get_person_api_v1_persons__person_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/relationships': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Relationships */
    get: operations['list_relationships_api_v1_relationships_get'];
    put?: never;
    /** Create Relationship */
    post: operations['create_relationship_api_v1_relationships_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/relationships/{relationship_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Relationship */
    get: operations['get_relationship_api_v1_relationships__relationship_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/relationships/{relationship_id}/messages': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Relationship Messages */
    get: operations['relationship_messages_api_v1_relationships__relationship_id__messages_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/status': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Status */
    get: operations['status_api_v1_status_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/health': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Health */
    get: operations['health_health_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/ready': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Ready */
    get: operations['ready_ready_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
}
export type webhooks = Record<string, never>;
export interface components {
  schemas: {
    /** AgentMessagePage */
    AgentMessagePage: {
      /** Items */
      items: components['schemas']['AgentMessagePublicResponse'][];
      /** Next Cursor */
      next_cursor: string | null;
    };
    /** AgentMessagePublicResponse */
    AgentMessagePublicResponse: {
      /** Content */
      content: string;
      /**
       * Conversation Id
       * Format: uuid
       */
      conversation_id: UUID;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /**
       * Id
       * Format: uuid
       */
      id: UUID;
      /**
       * Role
       * @enum {string}
       */
      role: 'user' | 'assistant';
    };
    /** AgentRunResponse */
    AgentRunResponse: {
      assistant_message: components['schemas']['AssistantMessageResponse'];
      /**
       * Conversation Id
       * Format: uuid
       */
      conversation_id: UUID;
      memory_status: components['schemas']['MemoryWriteStatus'];
      /**
       * Run Id
       * Format: uuid
       */
      run_id: UUID;
      status: components['schemas']['AgentRunStatus'];
      /** Warnings */
      warnings: string[];
    };
    /**
     * AgentRunStatus
     * @enum {string}
     */
    AgentRunStatus: 'pending' | 'running' | 'completed' | 'failed';
    /** AssistantMessageResponse */
    AssistantMessageResponse: {
      /** Content */
      content: string;
      /**
       * Id
       * Format: uuid
       */
      id: UUID;
      /**
       * Role
       * @default assistant
       * @constant
       */
      role: 'assistant';
    };
    /** Body_upload_chat_import_api_v1_chat_imports_post */
    Body_upload_chat_import_api_v1_chat_imports_post: {
      /** File */
      file: string;
      /** Source Format */
      source_format?: string | null;
      /** Source Timezone */
      source_timezone: string;
    };
    /** ConsentRequest */
    ConsentRequest: {
      /** Enabled */
      enabled: boolean;
    };
    /** ConversationCreateRequest */
    ConversationCreateRequest: {
      /**
       * Id
       * Format: uuid4
       * @description Fresh UUID v4 for one creation; retain on every retry.
       */
      id: UUID;
      /** Relationship Id */
      relationship_id?: UUID | null;
    };
    /** ConversationPage */
    ConversationPage: {
      /** Items */
      items: components['schemas']['ConversationResponse'][];
      /** Next Cursor */
      next_cursor: string | null;
    };
    /** ConversationResponse */
    ConversationResponse: {
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /**
       * Id
       * Format: uuid
       */
      id: UUID;
      /** Relationship Id */
      relationship_id: UUID | null;
      /**
       * Updated At
       * Format: date-time
       */
      updated_at: string;
    };
    /** CreateAgentRunRequest */
    CreateAgentRunRequest: {
      /** Expected Relationship Id */
      expected_relationship_id?: UUID | null;
      /** Message */
      message: string;
      /**
       * Operation Key
       * @description Optional client-generated retry key scoped to this user and conversation. Reuse only with the same logical request; use a new key for a new attempt.
       */
      operation_key?: string | null;
    };
    /** DeleteAllPreparation */
    DeleteAllPreparation: {
      /** Revoke Consent After Delete */
      revoke_consent_after_delete: boolean;
    };
    /** DeleteOnePreparation */
    DeleteOnePreparation: {
      /**
       * Memory Id
       * Format: uuid
       */
      memory_id: UUID;
      /** Person Id */
      person_id?: UUID | null;
      /** Relationship Id */
      relationship_id?: UUID | null;
    };
    /** DeletePersonPreparation */
    DeletePersonPreparation: {
      /**
       * Person Id
       * Format: uuid
       */
      person_id: UUID;
    };
    /** ErrorDetail */
    ErrorDetail: {
      /** Code */
      code: string;
      /** Message */
      message: string;
      /** Recovery Status */
      recovery_status?: string | null;
      /** Run Id */
      run_id?: UUID | null;
    };
    /** ErrorResponse */
    ErrorResponse: {
      error: components['schemas']['ErrorDetail'];
    };
    /** ExecuteDeleteRequest */
    ExecuteDeleteRequest: {
      /** Operation Key */
      operation_key: string;
    };
    /** FinalizeRequest */
    FinalizeRequest: {
      /** Expected Revision */
      expected_revision: number;
    };
    /** HealthResponse */
    HealthResponse: {
      /**
       * Status
       * @default ok
       * @constant
       */
      status: 'ok';
    };
    /** ImportJobReceiptSummary */
    ImportJobReceiptSummary: {
      /**
       * Dataset Job Id
       * Format: uuid
       */
      dataset_job_id: UUID;
      /** Ignored Message Count */
      ignored_message_count: number;
      /**
       * Imported At
       * Format: date-time
       */
      imported_at: string;
      /** Imported Message Count */
      imported_message_count: number;
      /**
       * Relationship Id
       * Format: uuid
       */
      relationship_id: UUID;
      /** System Message Count */
      system_message_count: number;
      /** Transcript Fingerprint */
      transcript_fingerprint: string;
    };
    /** ImportJobResponse */
    ImportJobResponse: {
      /** Artifact Id */
      artifact_id: UUID | null;
      /** Artifact State */
      artifact_state: string | null;
      /** Binding Revision */
      binding_revision: number;
      /** Bound Relationship Id */
      bound_relationship_id: UUID | null;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /** Error Count */
      error_count: number;
      /**
       * First Timestamp Utc
       * Format: date-time
       */
      first_timestamp_utc: string;
      /**
       * Id
       * Format: uuid
       */
      id: UUID;
      /** Ignored Message Count */
      ignored_message_count: number | null;
      /** Imported At */
      imported_at: string | null;
      /** Imported Message Count */
      imported_message_count: number | null;
      /** Issue Code Samples */
      issue_code_samples: string[];
      /** Issues Truncated */
      issues_truncated: number;
      /**
       * Last Timestamp Utc
       * Format: date-time
       */
      last_timestamp_utc: string;
      /** Message Count */
      message_count: number;
      /** Parser Version */
      parser_version: string;
      /** Possible Duplicate Job Id */
      possible_duplicate_job_id: UUID | null;
      /** Readiness Issues */
      readiness_issues: string[];
      readonly receipt: components['schemas']['ImportJobReceiptSummary'] | null;
      /** Schema Version */
      schema_version: string;
      /** Source Fingerprint */
      source_fingerprint: string;
      /** Source Format */
      source_format: string;
      /** Source Timezone */
      source_timezone: string;
      /** Speaker Count */
      speaker_count: number;
      /** Speakers */
      speakers: components['schemas']['SpeakerResponse'][];
      /** Status */
      status: string;
      /** System Message Count */
      system_message_count: number | null;
      /** Transcript Fingerprint */
      transcript_fingerprint: string;
      /**
       * Updated At
       * Format: date-time
       */
      updated_at: string;
      /** Warning Count */
      warning_count: number;
    };
    /**
     * ImportMergeStatus
     * @enum {string}
     */
    ImportMergeStatus: 'imported' | 'already_imported';
    /** ImportReceiptResponse */
    ImportReceiptResponse: {
      /**
       * Dataset Job Id
       * Format: uuid
       */
      dataset_job_id: UUID;
      /**
       * First Timestamp Utc
       * Format: date-time
       */
      first_timestamp_utc: string;
      /** Ignored Message Count */
      ignored_message_count: number;
      /**
       * Import Job Id
       * Format: uuid
       */
      import_job_id: UUID;
      /**
       * Imported At
       * Format: date-time
       */
      imported_at: string;
      /** Imported Message Count */
      imported_message_count: number;
      /**
       * Last Timestamp Utc
       * Format: date-time
       */
      last_timestamp_utc: string;
      /** New Message Count */
      new_message_count: number;
      /**
       * Relationship Id
       * Format: uuid
       */
      relationship_id: UUID;
      status: components['schemas']['ImportMergeStatus'];
      /** System Message Count */
      system_message_count: number;
      /** Transcript Fingerprint */
      transcript_fingerprint: string;
    };
    /** MemoryConfirmationChallenge */
    MemoryConfirmationChallenge: {
      /** Action */
      action: string;
      /**
       * Confirmation Id
       * Format: uuid
       */
      confirmation_id: UUID;
      /**
       * Deletion Scope Notice
       * @default Only scoped primary memory and its undo history are removed. Confirmation and mutation metadata are retained by policy. Chats, imports, identities, backups, logs and external provider copies are outside this operation.
       */
      deletion_scope_notice: string;
      /** Expected Count */
      expected_count: number;
      /**
       * Expires At
       * Format: date-time
       */
      expires_at: string;
      /**
       * Issued At
       * Format: date-time
       */
      issued_at: string;
      /**
       * Owner User Id
       * Format: uuid
       */
      owner_user_id: UUID;
      /** Person Id */
      person_id: UUID | null;
      /** Relationship Id */
      relationship_id: UUID | null;
      /** Revoke Consent After Delete */
      revoke_consent_after_delete: boolean;
      /** Target Id */
      target_id: UUID | null;
    };
    /** MemoryControlView */
    MemoryControlView: {
      /** Consent Enabled */
      consent_enabled: boolean;
      /** Effective Read Enabled */
      effective_read_enabled: boolean;
      /** Effective Write Enabled */
      effective_write_enabled: boolean;
      /** Paused */
      paused: boolean;
      /** Updated At */
      updated_at: string | null;
    };
    /** MemoryListResult */
    MemoryListResult: {
      /**
       * Historical Notice
       * @default Saved memories describe past information and may no longer be accurate.
       */
      historical_notice: string;
      /** Items */
      items: components['schemas']['MemoryRecordView'][];
      /** Next Cursor */
      next_cursor: string | null;
      /**
       * Retention Policy Summary
       * @default
       */
      retention_policy_summary: string;
    };
    /** MemoryMutationReceipt */
    MemoryMutationReceipt: {
      /** Action */
      action: string;
      /** Affected Count */
      affected_count: number;
      /**
       * Deletion Scope Notice
       * @default Only scoped primary memory and its undo history are removed. Confirmation and mutation metadata are retained by policy. Chats, imports, identities, backups, logs and external provider copies are outside this operation.
       */
      deletion_scope_notice: string;
      /**
       * Mutation Id
       * Format: uuid
       */
      mutation_id: UUID;
      /** Operation Key */
      operation_key: string;
      /**
       * Performed At
       * Format: date-time
       */
      performed_at: string;
      /** Person Id */
      person_id: UUID | null;
      /**
       * Primary Store Only
       * @default true
       */
      primary_store_only: boolean;
      /** Relationship Id */
      relationship_id: UUID | null;
      /** Replayed */
      replayed: boolean;
      /** Status */
      status: string;
      /** Target Id */
      target_id: UUID | null;
      /** Undone Memory Id */
      undone_memory_id: UUID | null;
    };
    /** MemoryRecordView */
    MemoryRecordView: {
      /** Content */
      content: string;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /**
       * Expires At
       * Format: date-time
       */
      expires_at: string;
      /**
       * Historical Notice
       * @default Saved memories describe past information and may no longer be accurate.
       */
      historical_notice: string;
      /**
       * Id
       * Format: uuid
       */
      id: UUID;
      /** Person Id */
      person_id: UUID | null;
      /** Provenance Summary */
      provenance_summary: string;
      /** Relationship Id */
      relationship_id: UUID | null;
      /**
       * Retention Policy Summary
       * @default
       */
      retention_policy_summary: string;
      /** Source */
      source: string;
      /** State */
      state: string;
      /**
       * Subject Id
       * Format: uuid
       */
      subject_id: UUID;
      /** Type */
      type: string;
      /**
       * Updated At
       * Format: date-time
       */
      updated_at: string;
    };
    /**
     * MemoryWriteStatus
     * @enum {string}
     */
    MemoryWriteStatus:
      | 'none'
      | 'saved'
      | 'duplicate'
      | 'skipped_no_consent'
      | 'skipped_paused'
      | 'rejected_validation'
      | 'pending_confirmation'
      | 'control_updated'
      | 'failed'
      | 'undone'
      | 'nothing_to_undo';
    /** PersonCreateRequest */
    PersonCreateRequest: {
      /** Display Name */
      display_name: string;
      /**
       * Id
       * Format: uuid4
       * @description Fresh UUID v4 for one creation; retain on every retry.
       */
      id: UUID;
    };
    /** PersonPage */
    PersonPage: {
      /** Items */
      items: components['schemas']['PersonResponse'][];
      /** Next Cursor */
      next_cursor: string | null;
    };
    /** PersonResponse */
    PersonResponse: {
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /** Display Name */
      display_name: string;
      /**
       * Id
       * Format: uuid
       */
      id: UUID;
      /**
       * Updated At
       * Format: date-time
       */
      updated_at: string;
    };
    /** RelationshipBindingRequest */
    RelationshipBindingRequest: {
      /** Expected Revision */
      expected_revision: number;
      /** Relationship Id */
      relationship_id: UUID | null;
    };
    /** RelationshipCreateRequest */
    RelationshipCreateRequest: {
      /**
       * Id
       * Format: uuid4
       * @description Fresh UUID v4 for one creation; retain on every retry.
       */
      id: UUID;
      /**
       * Person Id
       * Format: uuid
       */
      person_id: UUID;
      /**
       * Relationship Type
       * @description Explicit caller label; unknown is allowed.
       */
      relationship_type: string;
      /**
       * Status
       * @description Explicit caller label; no inferred relationship state.
       */
      status: string;
    };
    /** RelationshipMessagePageResponse */
    RelationshipMessagePageResponse: {
      /** Items */
      items: components['schemas']['RelationshipMessageResponse'][];
      /** Next Cursor */
      next_cursor: string | null;
    };
    /** RelationshipMessageResponse */
    RelationshipMessageResponse: {
      /** Content */
      content: string;
      /** Content Type */
      content_type: string;
      /**
       * Id
       * Format: uuid
       */
      id: UUID;
      /**
       * Import Job Id
       * Format: uuid
       */
      import_job_id: UUID;
      /** Message Fingerprint */
      message_fingerprint: string;
      /** Original Timestamp */
      original_timestamp: string;
      /** Person Id */
      person_id: UUID | null;
      /** Raw Speaker Label */
      raw_speaker_label: string;
      /**
       * Relationship Id
       * Format: uuid
       */
      relationship_id: UUID;
      /** Sender Kind */
      sender_kind: string;
      /** Source Index */
      source_index: number;
      /** Source Timezone */
      source_timezone: string;
      /**
       * Timestamp Utc
       * Format: date-time
       */
      timestamp_utc: string;
    };
    /** RelationshipPage */
    RelationshipPage: {
      /** Items */
      items: components['schemas']['RelationshipResponse'][];
      /** Next Cursor */
      next_cursor: string | null;
    };
    /** RelationshipResponse */
    RelationshipResponse: {
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /**
       * Id
       * Format: uuid
       */
      id: UUID;
      /**
       * Person Id
       * Format: uuid
       */
      person_id: UUID;
      /** Relationship Type */
      relationship_type: string;
      /** Status */
      status: string;
      /**
       * Updated At
       * Format: date-time
       */
      updated_at: string;
    };
    /**
     * SpeakerBinding
     * @enum {string}
     */
    SpeakerBinding: 'unbound' | 'self' | 'person' | 'system' | 'ignore';
    /** SpeakerBindingRequest */
    SpeakerBindingRequest: {
      binding_kind: components['schemas']['SpeakerBinding'];
      /** Expected Revision */
      expected_revision: number;
      /** Person Id */
      person_id?: UUID | null;
      /** Raw Speaker Label */
      raw_speaker_label: string;
    };
    /** SpeakerResponse */
    SpeakerResponse: {
      binding_kind: components['schemas']['SpeakerBinding'];
      /** Message Count */
      message_count: number;
      /** Person Id */
      person_id: UUID | null;
      /** Raw Speaker Label */
      raw_speaker_label: string;
    };
    /** StatusResponse */
    StatusResponse: {
      /** Environment */
      environment: string;
      /**
       * Service
       * @default goutoujunshi-server
       * @constant
       */
      service: 'goutoujunshi-server';
      /**
       * Status
       * @default running
       * @constant
       */
      status: 'running';
    };
    /** UndoPreview */
    UndoPreview: {
      /** Available */
      available: boolean;
      /** Created At */
      created_at?: string | null;
      /** Latest Operation Id */
      latest_operation_id?: UUID | null;
      /** Memory Id */
      memory_id?: UUID | null;
      /** Person Id */
      person_id?: UUID | null;
      /** Relationship Id */
      relationship_id?: UUID | null;
      /** Type */
      type?: string | null;
    };
    /** UndoRequest */
    UndoRequest: {
      /**
       * Expected Operation Id
       * Format: uuid
       */
      expected_operation_id: UUID;
      /** Operation Key */
      operation_key: string;
    };
  };
  responses: never;
  parameters: never;
  requestBodies: never;
  headers: never;
  pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
  upload_chat_import_api_v1_chat_imports_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'multipart/form-data': components['schemas']['Body_upload_chat_import_api_v1_chat_imports_post'];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ImportJobResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  inspect_chat_import_api_v1_chat_imports__job_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        job_id: UUID;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ImportJobResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  cancel_chat_import_api_v1_chat_imports__job_id__cancel_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        job_id: UUID;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ImportJobResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  finalize_chat_import_api_v1_chat_imports__job_id__finalize_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        job_id: UUID;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['FinalizeRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ImportReceiptResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  mark_chat_import_ready_api_v1_chat_imports__job_id__ready_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        job_id: UUID;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ImportJobResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  bind_relationship_api_v1_chat_imports__job_id__relationship_put: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        job_id: UUID;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['RelationshipBindingRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ImportJobResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  bind_speaker_api_v1_chat_imports__job_id__speakers_put: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        job_id: UUID;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['SpeakerBindingRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ImportJobResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  list_conversations_api_v1_conversations_get: {
    parameters: {
      query?: {
        limit?: number;
        cursor?: string | null;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ConversationPage'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  create_conversation_api_v1_conversations_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['ConversationCreateRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ConversationResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  get_conversation_api_v1_conversations__conversation_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        conversation_id: UUID;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ConversationResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  create_agent_run_api_v1_conversations__conversation_id__agent_runs_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        conversation_id: UUID;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateAgentRunRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['AgentRunResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  stream_agent_run_api_v1_conversations__conversation_id__agent_runs_stream_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        conversation_id: UUID;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateAgentRunRequest'];
      };
    };
    responses: {
      /** @description Version 1 events; failures after headers use a failed event */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': unknown;
          'text/event-stream': string;
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  list_agent_messages_api_v1_conversations__conversation_id__messages_get: {
    parameters: {
      query?: {
        limit?: number;
        cursor?: string | null;
      };
      header?: never;
      path: {
        conversation_id: UUID;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['AgentMessagePage'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  inspect_memories_api_v1_memories_get: {
    parameters: {
      query?: {
        person_id?: UUID | null;
        relationship_id?: UUID | null;
        limit?: number;
        cursor?: string | null;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['MemoryListResult'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  inspect_memory_api_v1_memories__memory_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        memory_id: UUID;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['MemoryRecordView'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  change_consent_api_v1_memory_consent_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['ConsentRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['MemoryControlView'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  inspect_control_api_v1_memory_control_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['MemoryControlView'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  prepare_delete_all_api_v1_memory_deletions_all_prepare_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['DeleteAllPreparation'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['MemoryConfirmationChallenge'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  prepare_delete_one_api_v1_memory_deletions_one_prepare_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['DeleteOnePreparation'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['MemoryConfirmationChallenge'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  prepare_delete_person_api_v1_memory_deletions_person_prepare_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['DeletePersonPreparation'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['MemoryConfirmationChallenge'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  execute_delete_api_v1_memory_deletions__confirmation_id__execute_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        confirmation_id: UUID;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['ExecuteDeleteRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['MemoryMutationReceipt'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  inspect_mutation_api_v1_memory_mutations__mutation_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        mutation_id: UUID;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['MemoryMutationReceipt'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  pause_api_v1_memory_pause_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['MemoryControlView'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  resume_api_v1_memory_resume_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['MemoryControlView'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  undo_memory_api_v1_memory_undo_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['UndoRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['MemoryMutationReceipt'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  preview_undo_api_v1_memory_undo_preview_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['UndoPreview'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  list_persons_api_v1_persons_get: {
    parameters: {
      query?: {
        limit?: number;
        cursor?: string | null;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['PersonPage'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  create_person_api_v1_persons_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['PersonCreateRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['PersonResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  get_person_api_v1_persons__person_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        person_id: UUID;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['PersonResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  list_relationships_api_v1_relationships_get: {
    parameters: {
      query?: {
        limit?: number;
        cursor?: string | null;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['RelationshipPage'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  create_relationship_api_v1_relationships_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['RelationshipCreateRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['RelationshipResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  get_relationship_api_v1_relationships__relationship_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        relationship_id: UUID;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['RelationshipResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  relationship_messages_api_v1_relationships__relationship_id__messages_get: {
    parameters: {
      query?: {
        limit?: number;
        cursor?: string | null;
      };
      header?: never;
      path: {
        relationship_id: UUID;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['RelationshipMessagePageResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  status_api_v1_status_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['StatusResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  health_health_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HealthResponse'];
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Dependency unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
    };
  };
  ready_ready_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': unknown;
        };
      };
      /** @description Invalid request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Authentication required */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Resource not found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Active run or idempotency conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Validation error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Internal server error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Agent execution failed */
      502: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorResponse'];
        };
      };
      /** @description Database unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
    };
  };
}

export const createApiClient = (options: ClientOptions) => createClient<paths>(options);
export const operationInventory = [
  {
    method: 'post',
    path: '/api/v1/chat-imports',
    operationId: 'upload_chat_import_api_v1_chat_imports_post',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/chat-imports/{job_id}',
    operationId: 'inspect_chat_import_api_v1_chat_imports__job_id__get',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/chat-imports/{job_id}/cancel',
    operationId: 'cancel_chat_import_api_v1_chat_imports__job_id__cancel_post',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/chat-imports/{job_id}/finalize',
    operationId: 'finalize_chat_import_api_v1_chat_imports__job_id__finalize_post',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/chat-imports/{job_id}/ready',
    operationId: 'mark_chat_import_ready_api_v1_chat_imports__job_id__ready_post',
    bearer: true,
  },
  {
    method: 'put',
    path: '/api/v1/chat-imports/{job_id}/relationship',
    operationId: 'bind_relationship_api_v1_chat_imports__job_id__relationship_put',
    bearer: true,
  },
  {
    method: 'put',
    path: '/api/v1/chat-imports/{job_id}/speakers',
    operationId: 'bind_speaker_api_v1_chat_imports__job_id__speakers_put',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/conversations',
    operationId: 'list_conversations_api_v1_conversations_get',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/conversations',
    operationId: 'create_conversation_api_v1_conversations_post',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/conversations/{conversation_id}',
    operationId: 'get_conversation_api_v1_conversations__conversation_id__get',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/conversations/{conversation_id}/agent-runs',
    operationId: 'create_agent_run_api_v1_conversations__conversation_id__agent_runs_post',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/conversations/{conversation_id}/agent-runs/stream',
    operationId: 'stream_agent_run_api_v1_conversations__conversation_id__agent_runs_stream_post',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/conversations/{conversation_id}/messages',
    operationId: 'list_agent_messages_api_v1_conversations__conversation_id__messages_get',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/memories',
    operationId: 'inspect_memories_api_v1_memories_get',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/memories/{memory_id}',
    operationId: 'inspect_memory_api_v1_memories__memory_id__get',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/memory/consent',
    operationId: 'change_consent_api_v1_memory_consent_post',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/memory/control',
    operationId: 'inspect_control_api_v1_memory_control_get',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/memory/deletions/all/prepare',
    operationId: 'prepare_delete_all_api_v1_memory_deletions_all_prepare_post',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/memory/deletions/one/prepare',
    operationId: 'prepare_delete_one_api_v1_memory_deletions_one_prepare_post',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/memory/deletions/person/prepare',
    operationId: 'prepare_delete_person_api_v1_memory_deletions_person_prepare_post',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/memory/deletions/{confirmation_id}/execute',
    operationId: 'execute_delete_api_v1_memory_deletions__confirmation_id__execute_post',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/memory/mutations/{mutation_id}',
    operationId: 'inspect_mutation_api_v1_memory_mutations__mutation_id__get',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/memory/pause',
    operationId: 'pause_api_v1_memory_pause_post',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/memory/resume',
    operationId: 'resume_api_v1_memory_resume_post',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/memory/undo',
    operationId: 'undo_memory_api_v1_memory_undo_post',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/memory/undo/preview',
    operationId: 'preview_undo_api_v1_memory_undo_preview_get',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/persons',
    operationId: 'list_persons_api_v1_persons_get',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/persons',
    operationId: 'create_person_api_v1_persons_post',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/persons/{person_id}',
    operationId: 'get_person_api_v1_persons__person_id__get',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/relationships',
    operationId: 'list_relationships_api_v1_relationships_get',
    bearer: true,
  },
  {
    method: 'post',
    path: '/api/v1/relationships',
    operationId: 'create_relationship_api_v1_relationships_post',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/relationships/{relationship_id}',
    operationId: 'get_relationship_api_v1_relationships__relationship_id__get',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/relationships/{relationship_id}/messages',
    operationId: 'relationship_messages_api_v1_relationships__relationship_id__messages_get',
    bearer: true,
  },
  {
    method: 'get',
    path: '/api/v1/status',
    operationId: 'status_api_v1_status_get',
    bearer: false,
  },
  {
    method: 'get',
    path: '/health',
    operationId: 'health_health_get',
    bearer: false,
  },
  {
    method: 'get',
    path: '/ready',
    operationId: 'ready_ready_get',
    bearer: false,
  },
] as const;
