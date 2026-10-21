import { useEffect, useSyncExternalStore } from 'react';
import { BodyText, PrimaryButton, SectionCard } from '../components/ui';
import type { LifecycleController } from '../data/lifecycleController';

const labels: Record<string, string> = {
  persons: 'Person',
  relationships: 'Relationship',
  conversations: 'AI Conversation',
  agent_runs: '保留 Run 幂等屏障',
  messages: 'AI 对话消息',
  chat_import_jobs: '导入 Job / Dataset',
  relationship_messages: '导入聊天消息',
  chat_import_speakers: '导入说话人',
  chat_import_artifacts: '原始导入文件',
  memory_records: '长期记忆及关联 Undo',
};
export function ConnectedLifecyclePanel({ controller }: { controller: LifecycleController }) {
  const view = useSyncExternalStore(controller.subscribe, controller.snapshot, controller.snapshot);
  useEffect(() => controller.leave, [controller]);
  if (!view.target) return null;
  return (
    <SectionCard title="删除完整结构化范围">
      <BodyText>
        正式目标：{view.target.domain} · {view.target.target_id}
      </BodyText>
      <BodyText muted>
        Person 删除包含其全部关系；Relationship 删除保留 Person 和其它关系。关联 AI
        对话、导入聊天、原始文件和此结构化范围的 Memory 会删除。UUID、原操作
        key、去重屏障和必要回执保留。旧备份与外部副本须另行处理；文字提及不会扩大删除。
      </BodyText>
      <BodyText live>完整删除状态：{view.phase}</BodyText>
      {view.error && <BodyText live>{view.error}</BodyText>}
      {view.challenge && (
        <SectionCard title="核对服务器完整删除范围">
          <BodyText>
            服务器目标：{view.challenge.domain} · {view.challenge.target_id}
          </BodyText>
          {Object.entries(view.challenge.counts).map(([key, count]) => (
            <BodyText key={key}>
              {labels[key] ?? key}：{count}
            </BodyText>
          ))}
          <BodyText>Memory 策略：删除上述结构化范围的长期记忆与 Undo，保留必要幂等回执。</BodyText>
          <BodyText>确认到期：{view.challenge.expires_at}</BodyText>
          <BodyText>完整删除 Confirmation ID：{view.challenge.confirmation_id}</BodyText>
          <PrimaryButton
            label="明确确认并执行完整范围删除"
            disabled={view.phase !== 'awaiting_confirmation'}
            onPress={() => {
              void controller.confirm();
            }}
          />
          <PrimaryButton label="取消完整范围删除" variant="quiet" onPress={controller.cancel} />
        </SectionCard>
      )}
      {['idle', 'failed', 'stale', 'expired'].includes(view.phase) && (
        <PrimaryButton
          label="重新准备完整范围删除"
          onPress={() => {
            void controller.prepare();
          }}
        />
      )}
      {view.phase === 'target_busy' && (
        <PrimaryButton label="主动刷新完整删除 Busy" onPress={controller.refreshBusy} />
      )}
      {['unknown_outcome', 'completed'].includes(view.phase) && (
        <PrimaryButton
          label="同 key 重放完整范围删除"
          onPress={() => {
            void controller.retry();
          }}
        />
      )}
      {view.receipt && (
        <SectionCard title="完整范围正式回执">
          <BodyText>完整删除 Receipt ID：{view.receipt.receipt_id}</BodyText>
          <BodyText>
            正式回执目标：{view.receipt.domain} · {view.receipt.target_id}
          </BodyText>
          <BodyText>完整删除权威刷新：{view.refresh}</BodyText>
        </SectionCard>
      )}
      <BodyText muted>
        重启、退出或切换身份会丢失本地操作描述，绝不会自动执行旧删除；需重新读取权威状态。Owner
        Owned Data 清除由运营工具提供，当前 App 不支持生产账户注销。
      </BodyText>
    </SectionCard>
  );
}
