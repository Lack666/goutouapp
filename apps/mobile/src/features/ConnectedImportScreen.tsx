import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';
import { useFocusEffect } from 'expo-router';
import { TextInput } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import { useLocalNavigation, useRelationshipScope } from '../navigation/scope';
import { useResourceView, useSessionView, type Connection } from '../session/ConnectionProvider';
import { pickImportFile } from '../data/filePicker';
import { AppHeader, BodyText, PrimaryButton, ScreenContainer, SectionCard } from '../components/ui';
import { DevelopmentSessionControls } from '../components/DevelopmentSessionControls';
import { RelationshipSelector } from '../components/RelationshipSelector';
import { SpeakerBindingControls } from '../components/SpeakerBindingControls';
import type { SpeakerBindingDraft, ImportStep } from '../contracts/import';

const steps: Record<ImportStep, string> = {
  source: '1 / 5 · 文件来源',
  speakers: '2 / 5 · 说话人绑定',
  relationship: '3 / 5 · 关系绑定',
  readiness: '4 / 5 · 服务器预检',
  result: '5 / 5 · 导入结果',
};
const states = {
  idle: '未选择',
  selecting: '正在选择',
  selected: '已选择，尚未上传',
  uploading: '正在上传和解析',
  job_created: '服务器任务已创建',
  failed: '文件选择或上传失败',
  unknown_outcome: 'unknown_upload_outcome',
  cancelled: '已取消选择',
};
export function ConnectedImportScreen({ connection }: { connection: Connection }) {
  const nav = useLocalNavigation();
  const scope = useRelationshipScope();
  const { colors } = useTheme();
  const session = useSessionView(connection);
  const resources = useResourceView(connection);
  const controller = connection.imports;
  const view = useSyncExternalStore(controller.subscribe, controller.snapshot, controller.snapshot);
  const [draftState, setDraftState] = useState<{
    scope: string | null;
    revision: number;
    bindings: Record<string, SpeakerBindingDraft>;
  }>({ scope: null, revision: -1, bindings: {} });
  const drafts =
    draftState.scope === view.scopeId && draftState.revision === view.job?.revision
      ? draftState.bindings
      : {};
  const [recoverId, setRecoverId] = useState('');
  useFocusEffect(
    useCallback(() => {
      setDraftState({ scope: null, revision: -1, bindings: {} });
      setRecoverId('');
      if (session.status === 'authenticated') void controller.open(scope);
      return controller.leave;
    }, [controller, scope, session.status]),
  );
  useEffect(() => {
    if (session.status === 'authenticated') {
      // Refresh invalidates a resource selection. Reuse already loaded owned
      // pages so entering Import preserves the existing resource navigation.
      for (const kind of ['persons', 'relationships'] as const)
        if (connection.resources.snapshot().pages[kind].status === 'idle')
          void connection.resources.load(kind);
    }
  }, [connection, session.status]);
  const busy =
    view.action !== 'idle' || view.upload === 'uploading' || session.status !== 'authenticated';
  const editable = !!view.job && ['awaiting_binding', 'ready'].includes(view.job.status);
  const allConfirmed = !!view.job?.speakers.every((s) => view.confirmations.includes(s.rawLabel));
  return (
    <ScreenContainer>
      <AppHeader
        title="导入与分析"
        subtitle="Connected Development Mode · 真实聊天导入"
        onBack={nav.back}
      />
      <DevelopmentSessionControls />
      <BodyText muted>
        支持微信 Markdown v1 和 ChatLab JSONL v0.0.2（含 Weport
        导出）。不会读取微信数据库或自动同步。导入不会运行 AI 分析或自动写入长期记忆。
      </BodyText>
      <SectionCard title={steps[view.step]}>
        <BodyText live>文件状态：{states[view.upload]}</BodyText>
        {view.file && (
          <BodyText>
            文件：{view.file.name} · {view.file.size} bytes · {view.file.mimeType}
          </BodyText>
        )}
        {view.error && <BodyText live>{view.error}</BodyText>}
        {view.outcome !== 'known' && (
          <BodyText live>{view.outcome}：先读取服务器任务状态，原操作不会自动重发。</BodyText>
        )}
        {view.step === 'source' && (
          <>
            <BodyText>导入格式：{view.sourceFormat}</BodyText>
            <PrimaryButton
              label="微信 Markdown v1"
              disabled={busy || !!view.job}
              onPress={() => controller.format('wechat_markdown_v1')}
            />
            <PrimaryButton
              label="ChatLab JSONL v0.0.2（Weport）"
              disabled={busy || !!view.job}
              onPress={() => controller.format('chatlab_jsonl_v0_0_2')}
            />
            <BodyText>源时区（IANA）：这是文件中原始聊天时间的时区，请明确核对。</BodyText>
            <TextInput
              accessibilityLabel="源时区 IANA"
              value={view.timezone}
              editable={!busy && !view.job}
              autoCapitalize="none"
              style={{
                color: colors.text,
                borderColor: colors.border,
                borderWidth: 1,
                padding: 12,
              }}
              onChangeText={(value) => controller.timezone(value)}
            />
            <PrimaryButton
              label={view.file ? '重新选择文件' : '选择聊天导出文件'}
              disabled={
                busy ||
                !!view.job ||
                view.upload === 'selecting' ||
                view.upload === 'unknown_outcome'
              }
              onPress={() => {
                void controller.select(pickImportFile);
              }}
            />
            {view.upload === 'selecting' && (
              <PrimaryButton
                label="取消文件选择"
                variant="quiet"
                onPress={controller.cancelSelection}
              />
            )}
            <PrimaryButton
              label="上传并创建任务"
              disabled={busy || view.upload !== 'selected' || view.scope === 'error'}
              onPress={() => {
                void controller.upload();
              }}
            />
            <BodyText muted>
              选择文件不会自动上传。100 MiB 为本地提示上限，实际限制由服务器决定。
            </BodyText>
            <TextInput
              accessibilityLabel="已有 ImportJob UUID"
              value={recoverId}
              onChangeText={setRecoverId}
              autoCapitalize="none"
              editable={!busy}
              style={{
                color: colors.text,
                borderColor: colors.border,
                borderWidth: 1,
                padding: 12,
              }}
            />
            <PrimaryButton
              label="读取已有 Job（不上传）"
              variant="quiet"
              disabled={busy || !recoverId}
              onPress={() => {
                void controller.recoverJob(recoverId);
              }}
            />
            <BodyText muted>
              任务 ID 仅保留在当前凭证会话内。App 重启后可用已知 UUID
              读取正式状态；不会自动重新上传。
            </BodyText>
          </>
        )}
        {view.job && (
          <>
            <BodyText>Job ID：{view.job.id}</BodyText>
            <BodyText live>
              服务器状态：{view.job.status} · revision {view.job.revision} · artifact{' '}
              {view.job.artifactState ?? '无'}
            </BodyText>
            <BodyText>
              格式：{view.job.summary.sourceFormat} · parser {view.job.parserVersion} · schema{' '}
              {view.job.schemaVersion}
            </BodyText>
            <BodyText>
              消息：{view.job.summary.messageCount} · 说话人：{view.job.summary.speakerCount}
            </BodyText>
            <BodyText>历史起始 UTC：{view.job.summary.firstTimestamp}</BodyText>
            <BodyText>历史结束 UTC：{view.job.summary.lastTimestamp}</BodyText>
            <BodyText>来源时区：{view.job.summary.sourceTimezone}</BodyText>
            <BodyText>
              警告：{view.job.warningCount} · 错误：{view.job.errorCount} · 未保留 issue：
              {view.job.truncatedIssues}
            </BodyText>
            <BodyText muted>
              以下仅为最多 20 种 issue code 采样，不是完整解析报告；警告不等于解析失败。
            </BodyText>
            {view.job.issueSamples.map((code) => (
              <BodyText key={code}>{code}</BodyText>
            ))}
            {view.job.summary.possibleDuplicate && (
              <BodyText>
                可能重复 Job：{view.job.summary.possibleDuplicate}（仅提示，尚未去重）
              </BodyText>
            )}
            {view.step === 'speakers' &&
              view.job.speakers.map((speaker) => {
                const binding =
                  drafts[speaker.id] ??
                  (speaker.binding === 'person'
                    ? { kind: 'person' as const, personId: speaker.personId }
                    : { kind: speaker.binding });
                return (
                  <SectionCard key={speaker.id} title="明确确认说话人">
                    <SpeakerBindingControls
                      speaker={speaker}
                      binding={binding}
                      persons={resources.pages.persons.items}
                      disabled={busy || !editable}
                      onBind={(value) =>
                        setDraftState({
                          scope: view.scopeId,
                          revision: view.job?.revision ?? -1,
                          bindings: { ...drafts, [speaker.id]: value },
                        })
                      }
                    />
                    <BodyText>
                      {view.confirmations.includes(speaker.rawLabel)
                        ? '本次已明确提交'
                        : '需要你明确提交；昵称不代表身份'}
                    </BodyText>
                    <PrimaryButton
                      label={`提交 ${speaker.rawLabel} 绑定`}
                      disabled={
                        busy ||
                        !editable ||
                        binding.kind === 'unbound' ||
                        (binding.kind === 'person' && !binding.personId)
                      }
                      onPress={() => {
                        if (binding.kind !== 'unbound')
                          void controller.bindSpeaker(
                            speaker.rawLabel,
                            binding.kind,
                            binding.kind === 'person' ? binding.personId : null,
                          );
                      }}
                    />
                  </SectionCard>
                );
              })}
            {view.step === 'speakers' && (
              <PrimaryButton
                label="下一步：选择关系"
                disabled={busy || !allConfirmed}
                onPress={() => controller.step('relationship')}
              />
            )}
            {view.step === 'relationship' && (
              <>
                <RelationshipSelector
                  connected
                  disabled={busy || !editable}
                  profiles={resources.pages.relationships.items}
                  selected={view.scopeId}
                  onSelect={(id) => {
                    setDraftState({ scope: null, revision: -1, bindings: {} });
                    void controller.chooseRelationship(id);
                  }}
                />
                <BodyText>
                  当前 Relationship UUID：{view.scopeId ?? '未选择'} · {view.scope}
                </BodyText>
                <BodyText muted>
                  改变关系会清除身份确认，须返回重新提交全部说话人。服务端最终检查所有权和兼容性。
                </BodyText>
                <PrimaryButton
                  label="确认并提交关系绑定"
                  disabled={busy || !editable || !allConfirmed || view.scope !== 'ready'}
                  onPress={() => {
                    void controller.confirmRelationship();
                  }}
                />
              </>
            )}
            {view.step === 'readiness' && (
              <>
                <BodyText>服务器 readiness issues：</BodyText>
                {view.job.readinessIssues.map((issue) => (
                  <BodyText key={issue}>{issue}</BodyText>
                ))}
                <BodyText muted>
                  仅支持一对一关系。额外说话人须明确选择 system / ignore；不会合并为一个 Person。
                </BodyText>
                <PrimaryButton
                  label="请求服务器预检"
                  disabled={busy || !editable || !allConfirmed || !view.relationshipConfirmed}
                  onPress={() => {
                    void controller.ready();
                  }}
                />
                <PrimaryButton
                  label="正式导入聊天记录"
                  disabled={
                    busy ||
                    view.job.status !== 'ready' ||
                    !allConfirmed ||
                    !view.relationshipConfirmed ||
                    view.outcome !== 'known'
                  }
                  onPress={() => {
                    void controller.finalize();
                  }}
                />
              </>
            )}
            {view.receipt && (
              <SectionCard title="服务器导入回执">
                <BodyText>聊天记录已成功导入，可在历史记录中查看。</BodyText>
                <BodyText>
                  结果：{view.receipt.status} · 导入 {view.receipt.count} · 忽略{' '}
                  {view.receipt.ignored} · system {view.receipt.system}
                </BodyText>
                <BodyText>新增条数：{view.receipt.newCount ?? 'inspect 摘要不提供'}</BodyText>
                <BodyText>Relationship：{view.receipt.relationshipId}</BodyText>
                <BodyText>
                  Job：{view.receipt.jobId} · Dataset：{view.receipt.datasetId}
                </BodyText>
                <BodyText>完成时间 UTC：{view.receipt.importedAt}</BodyText>
                {view.receipt.firstTimestamp && (
                  <BodyText>
                    历史范围 UTC：{view.receipt.firstTimestamp} — {view.receipt.lastTimestamp}
                  </BodyText>
                )}
                <PrimaryButton
                  label="查看真实关系聊天历史"
                  onPress={() => nav.open('/history', view.receipt!.relationshipId)}
                />
                <BodyText muted>
                  没有运行 AI 关系分析；这里的导入结果不会自动生成画像或 FIU 卡片。
                </BodyText>
              </SectionCard>
            )}
            <PrimaryButton
              label="重新读取服务器任务"
              variant="quiet"
              disabled={busy}
              onPress={() => {
                void controller.inspect();
              }}
            />
            {view.outcome === 'unknown_finalize_outcome' && (
              <PrimaryButton
                label="重试原 Job finalize"
                disabled={
                  busy ||
                  view.job.status !== 'ready' ||
                  !allConfirmed ||
                  !view.relationshipConfirmed
                }
                onPress={() => {
                  void controller.finalize();
                }}
              />
            )}
            {(view.job.status === 'imported' ||
              (view.job.status === 'ready' && view.receipt?.status === 'already_imported')) && (
              <PrimaryButton
                label="读取完整回执（原 Job replay）"
                variant="quiet"
                disabled={busy}
                onPress={() => {
                  void controller.finalize();
                }}
              />
            )}
            <PrimaryButton
              label="取消服务器任务"
              variant="quiet"
              disabled={busy || !editable}
              onPress={() => {
                void controller.cancel();
              }}
            />
            {editable && (
              <>
                <PrimaryButton
                  label="返回修改说话人"
                  variant="quiet"
                  disabled={busy}
                  onPress={() => controller.step('speakers')}
                />
                <PrimaryButton
                  label="返回修改关系"
                  variant="quiet"
                  disabled={busy}
                  onPress={() => controller.step('relationship')}
                />
              </>
            )}
          </>
        )}
        {busy && session.status === 'authenticated' && (
          <PrimaryButton
            label="停止等待（不代表服务器取消）"
            variant="quiet"
            onPress={controller.pause}
          />
        )}
        <PrimaryButton
          label="主动开始新导入"
          variant="quiet"
          disabled={busy}
          onPress={controller.newImport}
        />
        <BodyText muted>
          已上传任务不会因离开页面或开始新导入自动取消。无 Job ID
          的未知上传结果需先核对服务器；新导入可能另建任务。
        </BodyText>
      </SectionCard>
      <SectionCard title="Person 与 Relationship 资源">
        <PrimaryButton
          label="创建或选择真实资源"
          variant="quiet"
          onPress={() => nav.open('/relationship', null)}
        />
        {(['persons', 'relationships'] as const).map((kind) => (
          <SectionCard key={kind} title={kind}>
            <BodyText>{resources.pages[kind].status}</BodyText>
            {resources.pages[kind].error && <BodyText>{resources.pages[kind].error}</BodyText>}
            <PrimaryButton
              label={`刷新 ${kind}`}
              variant="quiet"
              disabled={busy || resources.pages[kind].status === 'loading'}
              onPress={() => {
                void connection.resources.load(kind);
              }}
            />
            <PrimaryButton
              label={`更多 ${kind}`}
              variant="quiet"
              disabled={
                busy || !resources.pages[kind].cursor || resources.pages[kind].status === 'loading'
              }
              onPress={() => {
                void connection.resources.load(kind, true);
              }}
            />
          </SectionCard>
        ))}
      </SectionCard>
    </ScreenContainer>
  );
}
