import type { RelationshipProfileViewModel } from './relationship';

export type ImportDemoKind = 'pair' | 'group' | 'empty';
export type ImportStep = 'source' | 'speakers' | 'relationship' | 'readiness' | 'result';
export interface SpeakerInventoryItemViewModel {
  readonly id: string;
  readonly rawLabel: string;
  readonly sourceLabel: string;
  readonly messageCount: number;
}
export interface ImportSourceSummaryViewModel {
  readonly sourceFormat: string;
  readonly messageCount: number;
  readonly speakerCount: number;
  readonly firstTimestamp: string;
  readonly lastTimestamp: string;
  readonly sourceTimezone: string;
  readonly warnings: readonly string[];
  readonly possibleDuplicate: string | null;
}
export interface ImportWizardViewModel {
  readonly provenance: 'synthetic-demo';
  readonly summary: ImportSourceSummaryViewModel;
  readonly speakers: readonly SpeakerInventoryItemViewModel[];
}
export type SpeakerBindingDraft =
  | { readonly kind: 'unbound' | 'self' | 'system' | 'ignore' }
  | { readonly kind: 'person'; readonly personId: string | null };
export interface RelationshipBindingDraft {
  readonly relationshipId: string | null;
  readonly confirmed: boolean;
}
export interface ImportPresentationState {
  readonly step: ImportStep;
  readonly loaded: boolean;
  readonly bindings: Readonly<Record<string, SpeakerBindingDraft>>;
  readonly relationship: RelationshipBindingDraft;
}
export interface ImportReadinessViewModel {
  readonly ready: boolean;
  readonly issues: readonly string[];
  readonly authority: 'local-preview';
}
export function initialImport(relationshipId: string | null): ImportPresentationState {
  return {
    step: 'source',
    loaded: false,
    bindings: {},
    relationship: { relationshipId, confirmed: false },
  };
}
export function speakerIssues(
  model: ImportWizardViewModel,
  state: ImportPresentationState,
): string[] {
  const issues: string[] = [];
  const bindings = model.speakers.map((s) => state.bindings[s.id] ?? { kind: 'unbound' });
  const persons = bindings.filter(
    (b): b is Extract<SpeakerBindingDraft, { kind: 'person' }> => b.kind === 'person',
  );
  if (!state.loaded || !model.summary.messageCount) issues.push('尚无演示源数据');
  if (bindings.filter((b) => b.kind === 'self').length !== 1)
    issues.push('请明确确认且仅确认一位 self');
  if (persons.length !== 1 || persons.some((b) => !b.personId))
    issues.push('请明确确认且仅确认一位 Person');
  if (bindings.some((b) => b.kind === 'unbound')) issues.push('存在未处理说话人');
  if (bindings.filter((b) => b.kind === 'self' || b.kind === 'person').length > 2)
    issues.push('当前版本的一对一关系导入不支持多人群聊');
  return issues;
}
export function previewReadiness(
  model: ImportWizardViewModel,
  state: ImportPresentationState,
  profiles: readonly RelationshipProfileViewModel[],
): ImportReadinessViewModel {
  const issues = speakerIssues(model, state);
  const persons = model.speakers
    .map((s) => state.bindings[s.id])
    .filter((b): b is Extract<SpeakerBindingDraft, { kind: 'person' }> => b?.kind === 'person');
  const profile = profiles.find((p) => p.id === state.relationship.relationshipId);
  if (!state.relationship.relationshipId || !state.relationship.confirmed)
    issues.push('Relationship 未选择或未确认');
  if (state.relationship.relationshipId && !profile) issues.push('关系不可用，请返回选择有效关系');
  if (profile && persons.some((b) => b.personId !== null && b.personId !== profile.person.id))
    issues.push('speaker/relationship 不兼容');
  return { ready: issues.length === 0, issues, authority: 'local-preview' };
}
export function canAdvanceImport(
  model: ImportWizardViewModel,
  state: ImportPresentationState,
  profiles: readonly RelationshipProfileViewModel[],
): boolean {
  if (!state.loaded || !model.summary.messageCount || state.step === 'result') return false;
  if (state.step === 'speakers') return speakerIssues(model, state).length === 0;
  if (state.step === 'relationship')
    return (
      state.relationship.confirmed &&
      profiles.some((p) => p.id === state.relationship.relationshipId)
    );
  return state.step === 'source' || previewReadiness(model, state, profiles).ready;
}
export function moveImport(
  state: ImportPresentationState,
  direction: 'next' | 'back',
  canAdvance: boolean,
): ImportPresentationState {
  const steps: readonly ImportStep[] = [
    'source',
    'speakers',
    'relationship',
    'readiness',
    'result',
  ];
  const index = steps.indexOf(state.step);
  if (direction === 'next' && (!state.loaded || !canAdvance)) return state;
  return {
    ...state,
    step: steps[Math.max(0, Math.min(4, index + (direction === 'next' ? 1 : -1)))] ?? 'source',
  };
}
