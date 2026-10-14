import { useCallback, useSyncExternalStore } from 'react';
import { useFocusEffect } from 'expo-router';
import type { Connection } from '../session/ConnectionProvider';
import { BodyText, PrimaryButton, SectionCard } from '../components/ui';
import { ERASURE_RESTART_NOTICE, ERASURE_SCOPE_NOTICE } from '../data/erasureController';

export function ConnectedErasurePanel({
  connection,
  domain,
  targetId,
  relationshipId,
}: {
  connection: Connection;
  domain: 'dataset' | 'conversation';
  targetId: string | null;
  relationshipId: string | null;
}) {
  const controller = connection.erasure;
  const view = useSyncExternalStore(controller.subscribe, controller.snapshot, controller.snapshot);
  useFocusEffect(
    useCallback(() => {
      if (domain === 'dataset' && relationshipId) void controller.discover(relationshipId);
      else if (domain === 'conversation' && targetId)
        void controller.openConversation(targetId, relationshipId);
      return controller.leave;
    }, [controller, domain, relationshipId, targetId]),
  );
  const busy =
    view.phase === 'executing' || view.phase === 'preparing' || view.discovery === 'loading';
  return (
    <SectionCard title={domain === 'dataset' ? '删除指定导入 Dataset' : '删除指定 AI Conversation'}>
      <BodyText muted>{ERASURE_SCOPE_NOTICE}</BodyText>
      {domain === 'dataset' && (
        <>
          <BodyText>
            服务器 Dataset 列表：{view.discovery} · 最多展示 200 份，请按关系选择。
          </BodyText>
          {view.datasets.map((row) => (
            <SectionCard key={row.dataset_job_id} title={`Dataset ${row.dataset_job_id}`}>
              <BodyText>Relationship：{row.relationship_id}</BodyText>
              <BodyText>
                来源：{row.source_format} / {row.parser_version} · {row.source_timezone}
              </BodyText>
              <BodyText>
                原聊天时间：{row.first_timestamp_utc} — {row.last_timestamp_utc}
              </BodyText>
              <BodyText>
                导入回执：{row.imported_at} · 原导入 {row.imported_message_count} · 当前正式消息{' '}
                {row.current_message_count}
              </BodyText>
              <BodyText>
                {row.deletable
                  ? '服务器状态：可准备删除'
                  : '服务器状态：已删除 · Tombstone 保留，不能重新导入相同 Dataset'}
              </BodyText>
              <PrimaryButton
                label={`选择删除 Dataset ${row.dataset_job_id}`}
                variant="quiet"
                disabled={
                  (!row.deletable &&
                    !controller.recoverable({
                      domain: 'dataset',
                      target_id: row.dataset_job_id,
                      relationship_id: row.relationship_id,
                    })) ||
                  busy
                }
                selected={view.target?.target_id === row.dataset_job_id}
                onPress={() =>
                  controller.select({
                    domain,
                    target_id: row.dataset_job_id,
                    relationship_id: row.relationship_id,
                  })
                }
              />
            </SectionCard>
          ))}
          <PrimaryButton
            label="刷新服务器 Dataset"
            variant="quiet"
            disabled={!relationshipId || busy || view.discovery === 'loading'}
            onPress={() => {
              if (relationshipId) void controller.discover(relationshipId);
            }}
          />
          <PrimaryButton
            label="更多服务器 Dataset"
            variant="quiet"
            disabled={
              !relationshipId ||
              !view.cursor ||
              busy ||
              view.discovery === 'loading' ||
              view.datasets.length >= 200
            }
            onPress={() => {
              if (relationshipId) void controller.discover(relationshipId, true);
            }}
          />
        </>
      )}
      <BodyText>删除目标：{view.target?.target_id ?? '请明确选择'}</BodyText>
      <BodyText live>删除状态：{view.phase}</BodyText>
      {view.error && <BodyText live>{view.error}</BodyText>}
      <PrimaryButton
        label="向服务器准备删除"
        disabled={
          !view.target ||
          busy ||
          ['awaiting_confirmation', 'unknown_outcome', 'completed', 'target_busy'].includes(
            view.phase,
          )
        }
        onPress={() => {
          void controller.prepare();
        }}
      />
      {view.challenge && (
        <SectionCard title="请明确核对服务器确认范围">
          <BodyText>Confirmation ID：{view.challenge.confirmation_id}</BodyText>
          <BodyText>
            服务器删除范围：{view.challenge.domain} · {view.challenge.target_id}
          </BodyText>
          <BodyText>服务器 Relationship：{view.challenge.relationship_id ?? '通用会话'}</BodyText>
          <BodyText>
            服务器待删消息：{view.challenge.message_count} · 保留 Run 元数据：
            {view.challenge.run_count}
          </BodyText>
          <BodyText>确认到期：{view.challenge.expires_at}</BodyText>
          <BodyText>保留元数据：{view.challenge.retained_metadata}</BodyText>
          <PrimaryButton
            label="明确确认并执行此范围删除"
            disabled={view.phase !== 'awaiting_confirmation'}
            onPress={() => {
              void controller.confirm();
            }}
          />
          <PrimaryButton label="取消本次删除确认" variant="quiet" onPress={controller.cancel} />
        </SectionCard>
      )}
      {view.phase === 'target_busy' && (
        <PrimaryButton label="主动刷新 Busy 状态" onPress={controller.refreshBusy} />
      )}
      {['unknown_outcome', 'completed'].includes(view.phase) && (
        <PrimaryButton
          label="同 key 安全重放原删除"
          variant="quiet"
          disabled={busy}
          onPress={() => {
            void controller.retry();
          }}
        />
      )}
      {view.receipt && (
        <SectionCard title="正式删除回执">
          <BodyText>Receipt ID：{view.receipt.receipt_id}</BodyText>
          <BodyText>
            删除回执目标：{view.receipt.domain} · {view.receipt.target_id}
          </BodyText>
          <BodyText>主库已删除消息：{view.receipt.message_count} · Memory 未受影响</BodyText>
          <BodyText>服务器执行时间：{view.receipt.performed_at}</BodyText>
          <BodyText>权威刷新：{view.refresh}</BodyText>
          <PrimaryButton
            label="查询正式删除回执"
            variant="quiet"
            disabled={busy}
            onPress={() => {
              void controller.inspect();
            }}
          />
        </SectionCard>
      )}
      <BodyText muted>{ERASURE_RESTART_NOTICE}</BodyText>
    </SectionCard>
  );
}
