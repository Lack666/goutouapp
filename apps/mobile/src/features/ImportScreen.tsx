import { useMemo, useState } from 'react';
import { useConnection } from '../session/ConnectionProvider';
import { ConnectedPendingScreen } from './ConnectedPendingScreen';
import { View } from 'react-native';
import { useDataSource } from '../data/DataSourceProvider';
import {
  initialImport,
  canAdvanceImport,
  moveImport,
  previewReadiness,
  speakerIssues,
  type ImportDemoKind,
  type SpeakerBindingDraft,
} from '../contracts/import';
import { useRelationshipScope, useLocalNavigation } from '../navigation/scope';
import {
  AppHeader,
  BodyText,
  DemoNotice,
  EmptyState,
  PrimaryButton,
  ScreenContainer,
  SectionCard,
} from '../components/ui';
import { RelationshipSelector } from '../components/RelationshipSelector';
import { StatePreview } from '../components/StatePreview';
import { useSurface } from '../hooks/useSurface';

export default function ImportScreen() {
  const connection = useConnection();
  return connection?.session.snapshot().mode === 'connected' ? (
    <ConnectedPendingScreen connection={connection} title="导入与分析" />
  ) : (
    <DemoImportScreen />
  );
}
function DemoImportScreen() {
  const scope = useRelationshipScope();
  const source = useDataSource();
  return <ImportSession key={scope ?? 'unselected'} scope={scope} source={source} />;
}
export function ImportSession({
  scope,
  source,
}: {
  scope: string | null;
  source: ReturnType<typeof useDataSource>;
}) {
  const nav = useLocalNavigation();
  const profiles = useMemo(() => source.readRelationships(), [source]);
  const [kind, setKind] = useState<ImportDemoKind>('pair');
  const model = useMemo(() => source.readImport(kind), [source, kind]);
  const [draft, setDraft] = useState(() => initialImport(scope));
  const { state, scenario, setScenario, retry } = useSurface('import');
  const unavailable = scope !== null && !profiles.some((p) => p.id === scope);
  const readiness = previewReadiness(model, draft, profiles);
  const canAdvance = canAdvanceImport(model, draft, profiles);
  const bind = (id: string, value: SpeakerBindingDraft) =>
    setDraft((d) => ({ ...d, bindings: { ...d.bindings, [id]: value } }));
  const steps = {
    source: '1 / 5 · 演示来源',
    speakers: '2 / 5 · 说话人绑定',
    relationship: '3 / 5 · 关系绑定',
    readiness: '4 / 5 · 本地预检',
    result: '5 / 5 · 下一步',
  };
  return (
    <ScreenContainer>
      <AppHeader
        title="导入与分析"
        subtitle="确认来源与身份，再检查导入准备状态。"
        onBack={nav.back}
      />
      <DemoNotice />
      <BodyText muted>本地演示 · 未连接服务器。真实文件上传将在后续版本接入。</BodyText>
      <PrimaryButton label="选择文件（尚未开放）" disabled />
      {unavailable ? (
        <EmptyState
          title="关系不可用"
          description="传入的 Relationship 不存在。不会自动选择另一段关系。请返回修改。"
        />
      ) : scenario === 'empty' ? (
        <>
          <SectionCard title={steps[draft.step]}>
            <BodyText muted>
              匿名合成 Demo · 不创建 ImportJob，不写入 RelationshipMessage。
            </BodyText>
            {draft.step === 'source' && (
              <>
                <PrimaryButton
                  label="体验导入流程（演示数据）"
                  onPress={() => {
                    setKind('pair');
                    setDraft({ ...initialImport(scope), loaded: true });
                  }}
                />
                <PrimaryButton
                  label="体验群聊样例（演示数据）"
                  variant="quiet"
                  onPress={() => {
                    setKind('group');
                    setDraft({ ...initialImport(scope), loaded: true });
                  }}
                />
                <PrimaryButton
                  label="体验空来源（演示数据）"
                  variant="quiet"
                  onPress={() => {
                    setKind('empty');
                    setDraft({ ...initialImport(scope), loaded: true });
                  }}
                />
                {draft.loaded &&
                  (model.summary.messageCount ? (
                    <>
                      <BodyText>格式：{model.summary.sourceFormat}</BodyText>
                      <BodyText>
                        消息：{model.summary.messageCount} · 说话人：{model.summary.speakerCount}
                      </BodyText>
                      <BodyText>起始：{model.summary.firstTimestamp}</BodyText>
                      <BodyText>结束：{model.summary.lastTimestamp}</BodyText>
                      <BodyText>来源时区：{model.summary.sourceTimezone}</BodyText>
                      {model.summary.warnings.map((w) => (
                        <BodyText key={w}>{w}</BodyText>
                      ))}
                      <BodyText muted>
                        {model.summary.possibleDuplicate ?? '没有可能重复提示'}
                      </BodyText>
                    </>
                  ) : (
                    <BodyText>尚无演示源数据，请重新选择样例。</BodyText>
                  ))}
              </>
            )}
            {draft.step === 'speakers' &&
              model.speakers.map((speaker) => {
                const binding = draft.bindings[speaker.id] ?? { kind: 'unbound' };
                return (
                  <SectionCard key={speaker.id} title={speaker.rawLabel}>
                    <BodyText>
                      {speaker.sourceLabel} · {speaker.messageCount} 条消息
                    </BodyText>
                    <BodyText>
                      绑定：{binding.kind}
                      {binding.kind === 'person'
                        ? ` · ${binding.personId ?? '尚未选择 Person'}`
                        : ''}
                    </BodyText>
                    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                      {(['self', 'person', 'system', 'ignore'] as const).map((role) => (
                        <PrimaryButton
                          key={role}
                          label={`${speaker.rawLabel} → ${role}`}
                          variant="quiet"
                          selected={binding.kind === role}
                          onPress={() =>
                            bind(
                              speaker.id,
                              role === 'person' ? { kind: role, personId: null } : { kind: role },
                            )
                          }
                        />
                      ))}
                    </View>
                    {binding.kind === 'person' &&
                      profiles.map((p) => (
                        <PrimaryButton
                          key={p.id}
                          label={`${speaker.rawLabel} → ${p.person.id}`}
                          variant="quiet"
                          selected={binding.personId === p.person.id}
                          onPress={() =>
                            bind(speaker.id, { kind: 'person', personId: p.person.id })
                          }
                        />
                      ))}
                  </SectionCard>
                );
              })}
            {draft.step === 'speakers' &&
              speakerIssues(model, draft).map((issue) => <BodyText key={issue}>{issue}</BodyText>)}
            {draft.step === 'relationship' && (
              <>
                <RelationshipSelector
                  profiles={profiles}
                  selected={draft.relationship.relationshipId}
                  onSelect={(id) => {
                    if (id !== draft.relationship.relationshipId)
                      setDraft((d) => ({
                        ...d,
                        step: 'speakers',
                        bindings: {},
                        relationship: { relationshipId: id, confirmed: false },
                      }));
                  }}
                />
                <BodyText muted>
                  切换关系会清除全部说话人绑定并返回身份确认，防止沿用上一段关系。
                </BodyText>
                {!draft.relationship.confirmed && <BodyText>Relationship 未选择或未确认</BodyText>}
                <PrimaryButton
                  label="确认关系绑定（Demo）"
                  disabled={!profiles.some((p) => p.id === draft.relationship.relationshipId)}
                  selected={draft.relationship.confirmed}
                  onPress={() =>
                    setDraft((d) => ({
                      ...d,
                      relationship: { ...d.relationship, confirmed: true },
                    }))
                  }
                />
              </>
            )}
            {draft.step === 'readiness' && (
              <>
                <BodyText>本地 readiness preview，不等于服务器 ready。</BodyText>
                {readiness.ready ? (
                  <BodyText>演示预检通过</BodyText>
                ) : (
                  readiness.issues.map((issue) => <BodyText key={issue}>{issue}</BodyText>)
                )}
                <PrimaryButton
                  label="返回修改说话人"
                  variant="quiet"
                  onPress={() => setDraft((d) => ({ ...d, step: 'speakers' }))}
                />
                <PrimaryButton
                  label="返回修改关系"
                  variant="quiet"
                  onPress={() => setDraft((d) => ({ ...d, step: 'relationship' }))}
                />
              </>
            )}
            {draft.step === 'result' && (
              <>
                <BodyText>演示预检已完成，真实导入将在连接服务器后启用。</BodyText>
                <PrimaryButton label="正式导入（尚未开放）" disabled />
                <PrimaryButton
                  label="查看关系历史 Demo"
                  onPress={() => nav.open('/history', draft.relationship.relationshipId)}
                />
                <PrimaryButton
                  label="进入 Chat 本地预览"
                  variant="quiet"
                  onPress={() => nav.open('/chat', draft.relationship.relationshipId)}
                />
              </>
            )}
            <PrimaryButton
              label="上一步"
              variant="quiet"
              disabled={draft.step === 'source'}
              onPress={() => setDraft((d) => moveImport(d, 'back', canAdvance))}
            />
            <PrimaryButton
              label="下一步"
              disabled={!canAdvance}
              onPress={() => setDraft((d) => moveImport(d, 'next', canAdvance))}
            />
            <PrimaryButton
              label="重置 Demo"
              variant="quiet"
              onPress={() => {
                setKind('pair');
                setDraft(initialImport(scope));
                retry();
              }}
            />
          </SectionCard>
          <SectionCard title="分析概览 · Demo">
            <BodyText muted>
              目前没有运行真实 Agent 分析。以下是独立演示样例，不是对用户输入的分析。
            </BodyText>
            <BodyText>事实：合成样例有一项学习活动安排。来源：预置场景。</BodyText>
            <BodyText>推测：可能愿意讨论安排；也可能只是礼貌回应。</BodyText>
            <BodyText>未知：对方对关系的期待。</BodyText>
            <PrimaryButton label="运行 AI 分析（尚未开放）" disabled />
          </SectionCard>
        </>
      ) : null}
      <StatePreview
        showEmpty={!draft.loaded}
        state={state}
        scenario={scenario}
        onSelect={setScenario}
        onRetry={retry}
      />
    </ScreenContainer>
  );
}
