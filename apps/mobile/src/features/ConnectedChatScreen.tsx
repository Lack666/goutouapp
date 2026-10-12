import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';
import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';
import { KeyboardAvoidingView, Platform, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { AppHeader, BodyText, PrimaryButton, SectionCard } from '../components/ui';
import { ChatComposer } from '../components/ChatComposer';
import { ChatMessageList } from '../components/ChatMessageList';
import { DevelopmentSessionControls } from '../components/DevelopmentSessionControls';
import { useTheme } from '../theme/ThemeProvider';
import { useRelationshipScope, useLocalNavigation } from '../navigation/scope';
import { useResourceView, useSessionView, type Connection } from '../session/ConnectionProvider';
import type { ProgressStatus } from '../api/agentEvents';
import { nativeSseObserver } from '../diagnostics/nativeSseObserver';
const progressLabels: Record<ProgressStatus, string> = {
  preparing: '准备运行',
  checking_safety: '检查安全',
  understanding_request: '理解请求',
  loading_context: '读取上下文',
  analyzing: '正在分析',
  planning: '准备建议',
  composing: '整理回答',
  preparing_safety_response: '准备安全回应',
  updating_memory: '检查记忆结果',
};
const phaseLabels = {
  idle: '尚未发送',
  submitting: '正在提交',
  running: '运行中',
  committed: '回答已提交，等待终止事件',
  completed: '运行完成',
  failed: '运行失败',
  running_unknown: '无法确认该请求是否已完成。',
};
export function ConnectedChatScreen({ connection }: { connection: Connection }) {
  const { colors } = useTheme();
  const nav = useLocalNavigation();
  const router = useRouter();
  const params = useLocalSearchParams<{ conversationId?: string | string[] }>();
  const scope = useRelationshipScope();
  const session = useSessionView(connection);
  const resources = useResourceView(connection);
  const [text, setText] = useState('');
  const [mode, setMode] = useState<'rest' | 'sse'>('sse');
  const view = useSyncExternalStore(
    connection.chat.subscribe,
    connection.chat.snapshot,
    connection.chat.snapshot,
  );
  const observation = useSyncExternalStore(
    nativeSseObserver.subscribe,
    nativeSseObserver.snapshot,
    nativeSseObserver.snapshot,
  );
  // Runs after React commits the actual screen state, not from a server log.
  useEffect(() => {
    nativeSseObserver.ui(view.phase, view.progress);
  }, [view.phase, view.progress]);
  const conversation =
    params.conversationId === undefined
      ? resources.selectedConversationId
      : typeof params.conversationId === 'string'
        ? params.conversationId
        : '__invalid__';
  useFocusEffect(
    useCallback(() => {
      setText('');
      if (conversation && session.status === 'authenticated')
        void connection.chat.open(conversation, scope);
      return connection.chat.leave;
    }, [connection, conversation, scope, session.status]),
  );
  useEffect(() => {
    if (!conversation && session.status === 'authenticated')
      void connection.resources.load('conversations');
  }, [connection, conversation, session.status]);
  const active = ['submitting', 'running', 'committed'].includes(view.phase);
  const disabled =
    view.scope !== 'ready' ||
    active ||
    view.phase === 'running_unknown' ||
    session.status !== 'authenticated';
  const send = () => {
    const value = text;
    setText('');
    void connection.chat.send(value, mode);
  };
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ChatMessageList
          connected
          messages={view.messages}
          scrollToLatest={view.messages.length}
          header={
            <>
              <AppHeader
                title="对话"
                subtitle="Connected Development Mode"
                onBack={() => {
                  connection.chat.leave();
                  nav.back();
                }}
              />
              <DevelopmentSessionControls />
              <SectionCard title="Agent 对话 · 服务器记录">
                <BodyText>当前 Conversation：{view.conversationId ?? '未选择或正在验证'}</BodyText>
                <BodyText>关系范围：{view.relationshipId ?? '通用会话'}</BodyText>
                {view.scope === 'loading' && <BodyText live>正在验证 owned Conversation…</BodyText>}
                {!conversation &&
                  resources.pages.conversations.items.map((item) => (
                    <PrimaryButton
                      key={item.id}
                      label={`选择 Conversation ${item.id}`}
                      variant="quiet"
                      onPress={() =>
                        router.replace({
                          pathname: '/chat',
                          params: {
                            conversationId: item.id,
                            ...(scope ? { relationshipId: scope } : {}),
                          },
                        })
                      }
                    />
                  ))}
                {!conversation && (
                  <BodyText>请在关系资料中创建或选择真实会话。没有会话时不会发送。</BodyText>
                )}
                {resources.pages.conversations.error && !conversation && (
                  <BodyText>{resources.pages.conversations.error}</BodyText>
                )}
                {view.error && <BodyText live>{view.error}</BodyText>}
                {view.scope === 'error' && conversation && (
                  <PrimaryButton
                    label="重新验证 Conversation"
                    onPress={() => {
                      void connection.chat.open(conversation, scope);
                    }}
                  />
                )}
                <BodyText live>Agent 状态：{phaseLabels[view.phase]}</BodyText>
                {nativeSseObserver.enabled && observation && (
                  <View
                    accessible
                    accessibilityLabel={`NATIVE-SSE ${JSON.stringify(observation)}`}
                    style={{ height: 48, overflow: 'hidden' }}
                  >
                    <BodyText muted>
                      Native SSE · {observation.terminal ?? 'pending'} · reads:
                      {observation.reader.reads}
                    </BodyText>
                  </View>
                )}
                {view.progress && <BodyText live>{progressLabels[view.progress]}</BodyText>}
                {view.runId && <BodyText>run_id：{view.runId}</BodyText>}
                {view.operationKey && <BodyText>operation_key：{view.operationKey}</BodyText>}
                {view.memoryStatus && (
                  <BodyText>服务器 memory_status：{view.memoryStatus}</BodyText>
                )}
                {view.memoryStatus === 'pending_confirmation' && (
                  <BodyText>
                    需要通过正式 Memory 确认服务处理；此页不执行授权、撤销或删除。
                  </BodyText>
                )}
                {view.memoryStatus && (
                  <PrimaryButton
                    label="前往 Memory 控制与确认"
                    variant="quiet"
                    onPress={() => router.push('/settings')}
                  />
                )}
                {view.warnings.map((warning, i) => (
                  <BodyText key={i}>{warning}</BodyText>
                ))}
                <BodyText muted>
                  展示服务器提交的完整文本回答。安全与事实判断由服务器负责；此页没有公开结构化 FIU
                  数据。
                </BodyText>
                {active && (
                  <PrimaryButton label="停止等待" variant="quiet" onPress={connection.chat.pause} />
                )}
                {view.operationKey && !active && (
                  <View style={{ gap: 8 }}>
                    <PrimaryButton
                      label="重试原操作（REST）"
                      variant="quiet"
                      disabled={view.scope !== 'ready'}
                      onPress={() => {
                        void connection.chat.retry('rest');
                      }}
                    />
                    <PrimaryButton
                      label="重试原操作（SSE）"
                      variant="quiet"
                      disabled={view.scope !== 'ready'}
                      onPress={() => {
                        void connection.chat.retry('sse');
                      }}
                    />
                    <BodyText muted>
                      重试保留原请求与
                      key。超时或停止等待不代表服务器已取消；历史不能证明某次运行已终止。失败后发送新消息会创建新
                      key。
                    </BodyText>
                  </View>
                )}
                <PrimaryButton
                  label="刷新 Agent 历史"
                  variant="quiet"
                  disabled={view.scope !== 'ready' || view.history === 'loading'}
                  onPress={() => {
                    void connection.chat.loadHistory();
                  }}
                />
                {view.history === 'loading' && <BodyText live>正在加载 Agent 历史…</BodyText>}
                {view.historyError && (
                  <>
                    <BodyText live>{view.historyError}</BodyText>
                    <PrimaryButton
                      label="重试 Agent 历史"
                      onPress={() => {
                        void connection.chat.loadHistory(view.cursor !== null);
                      }}
                    />
                  </>
                )}
                <PrimaryButton
                  label="加载更多 Agent 历史"
                  variant="quiet"
                  disabled={!view.cursor || view.history === 'loading'}
                  onPress={() => {
                    void connection.chat.loadHistory(true);
                  }}
                />
                <View style={{ flexDirection: 'row', gap: 8 }}>
                  <PrimaryButton
                    label="使用 POST SSE"
                    variant="quiet"
                    selected={mode === 'sse'}
                    disabled={active}
                    onPress={() => setMode('sse')}
                  />
                  <PrimaryButton
                    label="使用 REST"
                    variant="quiet"
                    selected={mode === 'rest'}
                    disabled={active}
                    onPress={() => setMode('rest')}
                  />
                </View>
              </SectionCard>
            </>
          }
        />
        <ChatComposer connected state={{ text, disabled }} onChange={setText} onPreview={send} />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
