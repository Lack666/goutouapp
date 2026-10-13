import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';
import { useFocusEffect } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTheme } from '../theme/ThemeProvider';
import { useLocalNavigation, useRelationshipScope } from '../navigation/scope';
import { useResourceView, useSessionView, type Connection } from '../session/ConnectionProvider';
import { AppHeader, BodyText, PrimaryButton, SectionCard } from '../components/ui';
import { DevelopmentSessionControls } from '../components/DevelopmentSessionControls';
import { RelationshipSelector } from '../components/RelationshipSelector';
import { HistoryList } from '../components/HistoryList';
import type { HistorySourceKind } from '../contracts/history';

export function ConnectedHistoryScreen({ connection }: { connection: Connection }) {
  const scope = useRelationshipScope();
  return <ConnectedHistorySession key={scope ?? 'general'} connection={connection} scope={scope} />;
}
function ConnectedHistorySession({
  connection,
  scope,
}: {
  connection: Connection;
  scope: string | null;
}) {
  const nav = useLocalNavigation();
  const { colors } = useTheme();
  const session = useSessionView(connection);
  const resources = useResourceView(connection);
  const [kind, setKind] = useState<HistorySourceKind>('relationship');
  const [parent, setParent] = useState<string | null>(scope);
  const controller = connection.history;
  const view = useSyncExternalStore(controller.subscribe, controller.snapshot, controller.snapshot);
  useFocusEffect(
    useCallback(() => {
      if (session.status === 'authenticated' && parent)
        void controller.open(kind, parent, kind === 'agent' ? scope : null);
      else controller.clear(kind);
      return controller.leave;
    }, [controller, kind, parent, scope, session.status]),
  );
  useEffect(() => {
    if (session.status === 'authenticated') {
      for (const kind of ['relationships', 'conversations'] as const)
        if (connection.resources.snapshot().pages[kind].status === 'idle')
          void connection.resources.load(kind);
    }
  }, [connection, session.status]);
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <HistoryList
        connected
        items={view.items}
        header={
          <>
            <AppHeader
              title="历史记录"
              subtitle="Connected Development Mode · 两种独立历史"
              onBack={nav.back}
            />
            <DevelopmentSessionControls />
            <BodyText muted>当前 App 尚无聊天历史删除入口；删除记忆不会清除聊天历史。</BodyText>
            <SectionCard title="历史类型">
              <PrimaryButton
                label="关系聊天"
                selected={kind === 'relationship'}
                variant="quiet"
                onPress={() => {
                  controller.clear('relationship');
                  setKind('relationship');
                  setParent(scope);
                }}
              />
              <PrimaryButton
                label="AI 对话"
                selected={kind === 'agent'}
                variant="quiet"
                onPress={() => {
                  controller.clear('agent');
                  setKind('agent');
                  setParent(null);
                }}
              />
              <BodyText muted>
                AI 对话是 Conversation user/assistant；关系聊天是导入的
                self/person/system，两者分别读取。
              </BodyText>
            </SectionCard>
            {kind === 'relationship' ? (
              <RelationshipSelector
                connected
                profiles={resources.pages.relationships.items}
                selected={parent}
                onSelect={(id) => {
                  controller.clear('relationship');
                  setParent(id);
                }}
              />
            ) : (
              <SectionCard title="明确选择 Conversation">
                {resources.pages.conversations.items
                  .filter((item) => scope === null || item.relationshipId === scope)
                  .map((item) => (
                    <PrimaryButton
                      key={item.id}
                      label={`历史 Conversation ${item.id}`}
                      variant="quiet"
                      selected={parent === item.id}
                      onPress={() => {
                        controller.clear('agent');
                        setParent(item.id);
                      }}
                    />
                  ))}
              </SectionCard>
            )}
            <SectionCard title="服务器历史状态">
              <BodyText>
                范围：{view.parentId ?? '未选择或不可用'} · 已读取 {view.items.length} 条
              </BodyText>
              <BodyText live>
                {view.status === 'loading' ? '正在加载服务器历史…' : view.status}
              </BodyText>
              {view.error && <BodyText live>{view.error}</BodyText>}
              <PrimaryButton
                label="刷新服务器历史"
                disabled={!parent || view.status === 'loading'}
                variant="quiet"
                onPress={() => {
                  if (parent) void controller.open(kind, parent, kind === 'agent' ? scope : null);
                }}
              />
              {view.status === 'error' && (
                <PrimaryButton
                  label="重试历史读取"
                  onPress={() => {
                    if (view.parentId) void controller.load(view.cursor !== null);
                    else if (parent)
                      void controller.open(kind, parent, kind === 'agent' ? scope : null);
                  }}
                />
              )}
              <BodyText muted>
                时间来自历史记录。原始聊天时间及源时区单独显示；导入完成时间不作为聊天日期。页面为实时分页视图，新导入后请刷新。
              </BodyText>
              <PrimaryButton
                label="进入真实导入"
                variant="quiet"
                onPress={() => nav.open('/import', kind === 'relationship' ? parent : scope)}
              />
              <PrimaryButton
                label="管理真实资源"
                variant="quiet"
                onPress={() => nav.open('/relationship', null)}
              />
              {(['relationships', 'conversations'] as const).map((resource) => (
                <SectionCard key={resource} title={`${resource} 选择器`}>
                  {resources.pages[resource].error && (
                    <BodyText>{resources.pages[resource].error}</BodyText>
                  )}
                  <PrimaryButton
                    label={`刷新历史 ${resource} 选择器`}
                    variant="quiet"
                    disabled={resources.pages[resource].status === 'loading'}
                    onPress={() => {
                      void connection.resources.load(resource);
                    }}
                  />
                  <PrimaryButton
                    label={`更多历史 ${resource} 选择器`}
                    variant="quiet"
                    disabled={
                      !resources.pages[resource].cursor ||
                      resources.pages[resource].status === 'loading'
                    }
                    onPress={() => {
                      void connection.resources.load(resource, true);
                    }}
                  />
                </SectionCard>
              ))}
            </SectionCard>
          </>
        }
        footer={
          <SectionCard title="有界分页">
            <PrimaryButton
              label="加载更多服务器历史"
              disabled={!view.cursor || view.status === 'loading' || view.bounded}
              onPress={() => {
                void controller.load(true);
              }}
            />
            {view.bounded && (
              <BodyText>
                已达到本页 2,000 条内存上限。刷新会从首批重新读取；这不是大型历史性能压测。
              </BodyText>
            )}
            <BodyText muted>
              每次最多 100 条，按正式 Message ID 合并；同时间或同内容的不同消息全部保留。
            </BodyText>
          </SectionCard>
        }
      />
    </SafeAreaView>
  );
}
