import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';
import { TextInput, View, type TextStyle } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { BodyText, PrimaryButton, SectionCard } from '../components/ui';
import { useResourceView, useSessionView, type Connection } from '../session/ConnectionProvider';
import { useTheme } from '../theme/ThemeProvider';
import { MEMORY_RESTART_NOTICE, MEMORY_WINDOW_LIMIT } from '../data/memoryController';
import type { ConnectedMemoryRecord, MemoryMutationPhase } from '../contracts/connectedMemory';
const phases: Record<MemoryMutationPhase, string> = {
  idle: '尚未准备操作',
  preparing: '正在请求服务器确认',
  awaiting_user_confirmation: '等待你明确确认',
  executing: '正在执行原操作',
  completed: '正式回执已确认',
  stale_or_conflict: '目标已变化或操作冲突',
  expired: '服务器确认已过期',
  failed: '操作未准备完成',
  unknown_outcome: '操作结果未知',
};
export function ConnectedMemoryPanel({ connection }: { connection: Connection }) {
  const controller = connection.memory;
  const session = useSessionView(connection);
  const resources = useResourceView(connection);
  const view = useSyncExternalStore(controller.subscribe, controller.snapshot, controller.snapshot);
  const { colors } = useTheme();
  const inputScope = `${session.epoch}:${view.scope.personId}:${view.scope.relationshipId}`;
  useFocusEffect(
    useCallback(() => {
      if (session.status === 'authenticated') {
        void controller.resume();
        for (const kind of ['persons', 'relationships'] as const) {
          if (connection.resources.snapshot().pages[kind].status === 'idle')
            void connection.resources.load(kind);
        }
      }
      return controller.pause;
    }, [connection, controller, session.status]),
  );
  useEffect(() => {
    const timer = setInterval(controller.tick, 1000);
    return () => clearInterval(timer);
  }, [controller]);
  const busy = view.status === 'loading' || session.status !== 'authenticated';
  const locked = busy || ['executing', 'unknown_outcome'].includes(view.phase);
  const inputStyle = {
    color: colors.text,
    borderColor: colors.border,
    borderWidth: 1,
    padding: 12,
    borderRadius: 8,
  };
  const record = (item: ConnectedMemoryRecord, detail = false) => (
    <SectionCard
      key={`${detail ? 'detail' : 'list'}-${item.id}`}
      title={detail ? '服务器记忆详情' : '服务器记忆'}
    >
      <BodyText>{item.summary}</BodyText>
      <BodyText>Memory ID：{item.id}</BodyText>
      <BodyText>
        类型：{item.type} · subject：{item.subjectId}
      </BodyText>
      <BodyText>
        Person：{item.personId ?? '用户级'} · Relationship：{item.relationshipId ?? '无'}
      </BodyText>
      <BodyText>
        创建：{item.createdAt} · 更新：{item.updatedAt}
      </BodyText>
      <BodyText>
        过期：{item.expiresAt} · 状态：{item.state === 'active' ? '有效' : '过期（不可召回）'}
      </BodyText>
      <BodyText>
        来源：{item.source} · {item.provenance}
      </BodyText>
      <BodyText muted>{item.historicalNotice}</BodyText>
      {detail && <BodyText muted>{item.retention}</BodyText>}
      {!detail && (
        <PrimaryButton
          label={`查看记忆 ${item.id}`}
          variant="quiet"
          disabled={busy}
          onPress={() => {
            void controller.inspect(item.id);
          }}
        />
      )}
      <PrimaryButton
        label={`准备删除记忆 ${item.id}${detail ? '（详情）' : ''}`}
        variant="quiet"
        disabled={locked}
        onPress={() => {
          void controller.prepare('delete_one', item.id);
        }}
      />
    </SectionCard>
  );
  return (
    <>
      <SectionCard title="Memory 控制 · 服务器权威状态">
        {session.status !== 'authenticated' && <BodyText>请先接入有效开发会话。</BodyText>}
        {view.control ? (
          <>
            <BodyText>Consent：{view.control.consentEnabled ? '已授权' : '未授权'}</BodyText>
            <BodyText>Pause：{view.control.paused ? '已暂停' : '未暂停'}</BodyText>
            <BodyText>
              服务器召回：{view.control.readEnabled ? '允许' : '关闭'} · 写入：
              {view.control.writeEnabled ? '允许' : '关闭'}
            </BodyText>
            <BodyText>更新时间：{view.control.updatedAt ?? '尚无控制变更'}</BodyText>
          </>
        ) : (
          <BodyText>控制状态尚未确认。</BodyText>
        )}
        <BodyText muted>
          开发会话不代表 Memory
          授权。撤销授权保留已有记录并暂停；重新授权保留暂停状态。未授权时恢复不会重新授权。暂停阻止后续召回及最终写入，不会追溯移除已载入运行上下文的记忆。
        </BodyText>
        {(['grant', 'revoke', 'pause', 'resume'] as const).map((action, index) => (
          <PrimaryButton
            key={action}
            label={['授权长期记忆', '撤销长期记忆授权', '暂停记忆', '恢复记忆'][index]!}
            disabled={locked}
            variant="quiet"
            onPress={() => {
              void controller.changeControl(action);
            }}
          />
        ))}
        <PrimaryButton
          label="重新读取 Memory 权威状态"
          disabled={busy}
          onPress={() => {
            void controller.refresh();
          }}
        />
        {view.status === 'loading' && <BodyText live>正在读取或提交 Memory…</BodyText>}
        {view.error && <BodyText live>{view.error}</BodyText>}
        {view.feedback && <BodyText live>{view.feedback}</BodyText>}
      </SectionCard>
      <SectionCard title="记忆范围 · owned resources">
        <BodyText>
          当前 Person：{view.scope.personId ?? '全部本人记忆'} · Relationship：
          {view.scope.relationshipId ?? '全部关系'}
        </BodyText>
        <PrimaryButton
          label="选择全部本人记忆"
          selected={!view.scope.personId}
          variant="quiet"
          disabled={locked}
          onPress={() => {
            void controller.open(null, null);
          }}
        />
        {resources.pages.persons.items.map((person) => (
          <PrimaryButton
            key={person.id}
            label={`记忆 Person ${person.nickname ?? '未命名'} · ${person.id}`}
            selected={view.scope.personId === person.id && !view.scope.relationshipId}
            variant="quiet"
            disabled={locked}
            onPress={() => {
              void controller.open(person.id, null);
            }}
          />
        ))}
        {resources.pages.relationships.items
          .filter((item) => item.person.id === view.scope.personId)
          .map((item) => (
            <PrimaryButton
              key={item.id}
              label={`记忆 Relationship ${item.id}`}
              selected={view.scope.relationshipId === item.id}
              variant="quiet"
              disabled={locked}
              onPress={() => {
                void controller.open(item.person.id, item.id);
              }}
            />
          ))}
        {(['persons', 'relationships'] as const).map((kind) => (
          <View key={kind} style={{ gap: 8 }}>
            {resources.pages[kind].error && <BodyText live>{resources.pages[kind].error}</BodyText>}
            <PrimaryButton
              label={`刷新记忆 ${kind} 选择器`}
              variant="quiet"
              disabled={locked || resources.pages[kind].status === 'loading'}
              onPress={() => {
                void connection.resources.load(kind);
              }}
            />
            <PrimaryButton
              label={`更多记忆 ${kind} 选择器`}
              variant="quiet"
              disabled={
                locked ||
                !resources.pages[kind].cursor ||
                resources.pages[kind].status === 'loading'
              }
              onPress={() => {
                void connection.resources.load(kind, true);
              }}
            />
          </View>
        ))}
      </SectionCard>
      <SectionCard title="Inspect Memory · 服务器记录">
        <BodyText>
          当前窗口：{view.items.length} 条 · 最多 {MEMORY_WINDOW_LIMIT} 条
        </BodyText>
        {view.status === 'ready' && !view.items.length && (
          <BodyText>当前范围没有有效记忆。</BodyText>
        )}
        <BodyText muted>{view.retention || '等待服务器保留策略。'}</BodyText>
        <BodyText muted>{view.historicalNotice || '已保存的历史信息不一定仍然正确。'}</BodyText>
        <BodyText muted>
          过期记忆不再召回，默认列表排除过期记录；后台物理清理可能稍后执行。已知 ID
          的详情可显示尚未清理的过期记录。
        </BodyText>
        <PrimaryButton
          label="加载更多 Memory"
          disabled={busy || !view.cursor || view.items.length >= MEMORY_WINDOW_LIMIT}
          variant="quiet"
          onPress={() => {
            void controller.refresh(true);
          }}
        />
        <MemoryLookup
          key={`memory:${inputScope}`}
          label="已知 Memory ID"
          button="按已知 ID 检查记忆"
          disabled={busy}
          style={inputStyle}
          submit={(id) => {
            void controller.inspect(id);
          }}
        />
      </SectionCard>
      {view.items.map((item) => record(item))}
      {view.detail && record(view.detail, true)}
      <SectionCard title="Guarded Undo · 最新服务器操作">
        <BodyText>
          Undo 只针对当前用户最新操作；不会自动寻找或撤销更早的记录。预览不执行撤销。
        </BodyText>
        <PrimaryButton
          label="检查最新 Undo 并准备确认"
          disabled={locked}
          onPress={() => {
            void controller.armUndo();
          }}
        />
        {view.undo ? (
          <>
            <BodyText>最新 operation ID：{view.undo.operationId}</BodyText>
            <BodyText>
              目标 Memory：{view.undo.memoryId} · 类型：{view.undo.type}
            </BodyText>
            <BodyText>
              Person：{view.undo.personId ?? '用户级'} · Relationship：
              {view.undo.relationshipId ?? '无'} · 创建：{view.undo.createdAt}
            </BodyText>
          </>
        ) : (
          <BodyText>尚无已读取的可撤销操作。</BodyText>
        )}
      </SectionCard>
      <SectionCard title="确认删除 · 仅主库长期记忆">
        <BodyText>
          Person 删除按服务器结构化 Person
          范围执行，包含该对象各关系的记忆；不会靠文本搜索匹配，也不删除
          Person、Relationship、Conversation、Agent History 或导入聊天。
        </BodyText>
        <PrimaryButton
          label="准备删除当前 Person 的记忆"
          disabled={locked || !view.scope.personId}
          variant="quiet"
          onPress={() => {
            void controller.prepare('delete_person');
          }}
        />
        <BodyText>
          删除全部记忆后是否撤销授权：
          {view.allConsentChoice === null
            ? '尚未选择'
            : view.allConsentChoice
              ? '撤销授权'
              : '保留授权'}
        </BodyText>
        <PrimaryButton
          label="全部删除后保留授权"
          selected={view.allConsentChoice === false}
          disabled={locked}
          variant="quiet"
          onPress={() => controller.chooseAllConsent(false)}
        />
        <PrimaryButton
          label="全部删除后撤销授权"
          selected={view.allConsentChoice === true}
          disabled={locked}
          variant="quiet"
          onPress={() => controller.chooseAllConsent(true)}
        />
        <PrimaryButton
          label="准备删除全部本人记忆"
          disabled={locked || view.allConsentChoice === null || !!view.scope.personId}
          onPress={() => {
            void controller.prepare('delete_all');
          }}
        />
        <BodyText muted>
          修改授权选择会使旧确认失效，需重新向服务器准备。删除包含范围内的过期主库记录及 Undo
          历史；确认和回执元数据按策略保留。主库删除不代表备份、日志或外部提供商副本即时擦除，也不代表删除所有个人资料。
        </BodyText>
      </SectionCard>
      <SectionCard title="操作确认与恢复">
        <BodyText live>Mutation 状态：{phases[view.phase]}</BodyText>
        {view.challenge && (
          <>
            <BodyText>Confirmation ID：{view.challenge.id}</BodyText>
            <BodyText>
              Action：{view.challenge.action} · Target：{view.challenge.targetId ?? '本人全部记忆'}
            </BodyText>
            <BodyText>服务器待删数量：{view.challenge.expectedCount}</BodyText>
            <BodyText>
              Person：{view.challenge.personId ?? '用户级／全部'} · Relationship：
              {view.challenge.relationshipId ?? '全部／无'}
            </BodyText>
            <BodyText>删除后撤销授权：{view.challenge.revokeConsent ? '是' : '否'}</BodyText>
            <BodyText>
              签发：{view.challenge.issuedAt} · 过期：{view.challenge.expiresAt}
            </BodyText>
            <BodyText muted>{view.challenge.notice}</BodyText>
          </>
        )}
        <PrimaryButton
          label={view.challenge ? '确认执行服务器删除' : '确认撤销该最新操作'}
          disabled={busy || view.phase !== 'awaiting_user_confirmation'}
          onPress={() => {
            void controller.execute();
          }}
        />
        <PrimaryButton
          label="安全重试原 Memory 操作"
          disabled={
            busy || !view.canRetry || !['unknown_outcome', 'completed'].includes(view.phase)
          }
          variant="quiet"
          onPress={() => {
            void controller.retry();
          }}
        />
        <BodyText muted>{MEMORY_RESTART_NOTICE}</BodyText>
      </SectionCard>
      <SectionCard title="持久化 Mutation Receipt">
        <MemoryLookup
          key={`receipt:${inputScope}`}
          label="已知 Mutation ID"
          button="查询服务器持久化回执"
          disabled={busy}
          fallback={view.receipt?.id}
          style={inputStyle}
          submit={(id) => {
            void controller.inspectReceipt(id);
          }}
        />
        {view.receipt ? (
          <>
            <BodyText>Mutation ID：{view.receipt.id}</BodyText>
            <BodyText>
              Action：{view.receipt.action} · Status：{view.receipt.status}
            </BodyText>
            <BodyText>
              实际影响数量：{view.receipt.affectedCount} · Target：
              {view.receipt.targetId ?? '本人全部记忆'}
            </BodyText>
            <BodyText>
              Person：{view.receipt.personId ?? '用户级／全部'} · Relationship：
              {view.receipt.relationshipId ?? '全部／无'}
            </BodyText>
            <BodyText>undone Memory：{view.receipt.undoneMemoryId ?? '不适用'}</BodyText>
            <BodyText>执行时间：{view.receipt.performedAt}</BodyText>
            <BodyText>
              本次响应 replayed：{view.receipt.replayed ? '是' : '否'} · primary_store_only：
              {view.receipt.primaryStoreOnly ? '是' : '否'}
            </BodyText>
            <BodyText muted>{view.receipt.notice}</BodyText>
          </>
        ) : (
          <BodyText>尚无已确认的服务器回执。</BodyText>
        )}
      </SectionCard>
    </>
  );
}
function MemoryLookup({
  label,
  button,
  disabled,
  fallback,
  style,
  submit,
}: {
  label: string;
  button: string;
  disabled: boolean;
  fallback?: string;
  style: TextStyle;
  submit: (id: string) => void;
}) {
  const [value, setValue] = useState('');
  const id = value.trim() || fallback;
  return (
    <>
      <TextInput
        accessibilityLabel={label}
        value={value}
        onChangeText={setValue}
        autoCapitalize="none"
        style={style}
      />
      <PrimaryButton
        label={button}
        disabled={disabled || !id}
        onPress={() => {
          if (id) submit(id);
        }}
      />
    </>
  );
}
