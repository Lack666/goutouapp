import { useEffect } from 'react';
import { useLocalSearchParams } from 'expo-router';
import { AppHeader, BodyText, PrimaryButton, ScreenContainer, SectionCard } from '../components/ui';
import { DevelopmentSessionControls } from '../components/DevelopmentSessionControls';
import { useLocalNavigation, useRelationshipScope } from '../navigation/scope';
import { useResourceView, useSessionView, type Connection } from '../session/ConnectionProvider';
export function ConnectedPendingScreen({
  connection,
  title,
}: {
  connection: Connection;
  title: string;
}) {
  const scope = useRelationshipScope();
  const { conversationId } = useLocalSearchParams<{ conversationId?: string | string[] }>();
  const { back } = useLocalNavigation();
  const session = useSessionView(connection);
  const view = useResourceView(connection);
  useEffect(() => {
    if (session.status === 'authenticated' && scope)
      void connection.resources.select('relationships', scope);
  }, [connection, scope, session.status]);
  useEffect(() => {
    if (session.status === 'authenticated' && conversationId)
      void connection.resources.select(
        'conversations',
        Array.isArray(conversationId) ? '__unavailable__' : conversationId,
      );
  }, [connection, conversationId, session.status]);
  const relationship = view.details.relationships;
  const conversation = view.details.conversations;
  return (
    <ScreenContainer>
      <AppHeader title={title} subtitle="Connected Development Mode" onBack={back} />
      <DevelopmentSessionControls />
      <SectionCard title="尚未接入服务器业务">
        <BodyText>
          对话页已支持 Agent 发送和正式历史。此页的导入、关系聊天历史或记忆操作尚未开放。
        </BodyText>
        {session.status === 'authenticated' && (
          <>
            <BodyText>
              关系上下文：
              {scope === null
                ? '未选择'
                : relationship.value?.id === scope
                  ? `${relationship.value.displayName} · ${scope}`
                  : '正在验证或不可用'}
            </BodyText>
            {relationship.error && <BodyText live>{relationship.error}</BodyText>}
            <BodyText>
              会话上下文：
              {typeof conversationId === 'string' && conversation.value?.id === conversationId
                ? conversation.value.id
                : '未选择或不可用'}
            </BodyText>
            {conversation.error && <BodyText live>{conversation.error}</BodyText>}
          </>
        )}
        <PrimaryButton label="执行服务器业务（尚未开放）" disabled />
      </SectionCard>
    </ScreenContainer>
  );
}
