export type ChatRunPresentationState =
  | 'idle'
  | 'unavailable'
  | 'starting'
  | 'progressing'
  | 'completed'
  | 'failed'
  | 'pending_confirmation';
// Public presentation only: no tools, private evidence or wire DTOs.
export interface AgentChatMessageViewModel {
  readonly id: string;
  readonly role: 'user' | 'assistant';
  readonly text: string;
  readonly timeLabel: string;
  readonly source: 'synthetic-demo' | 'local-preview';
}
export interface ChatThreadViewModel {
  readonly id: string;
  readonly relationshipId: string | null;
  readonly title: string;
  readonly messages: readonly AgentChatMessageViewModel[];
}
export interface ChatComposerState {
  readonly text: string;
  readonly disabled: boolean;
}
export type FiuPreviewItem =
  | { readonly kind: 'fact'; readonly text: string; readonly provenance: string }
  | { readonly kind: 'inference'; readonly text: string; readonly alternative: string }
  | { readonly kind: 'unknown'; readonly text: string };
export interface ChatScreenViewModel {
  readonly thread: ChatThreadViewModel;
  readonly fiu: readonly FiuPreviewItem[];
  readonly source: 'demo';
}
export const COMPOSER_LIMIT = 2000;
export function appendLocalPreview(
  messages: readonly AgentChatMessageViewModel[],
  message: AgentChatMessageViewModel & { readonly role: 'user'; readonly source: 'local-preview' },
): readonly AgentChatMessageViewModel[] {
  return [...messages, message];
}
