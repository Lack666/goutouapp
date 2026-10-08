import { memo, useRef } from 'react';
import type { ReactElement } from 'react';
import { FlatList, Text, View } from 'react-native';
import type { AgentChatMessageViewModel } from '../contracts/chat';
import { useTheme } from '../theme/ThemeProvider';
import { tokens } from '../theme/tokens';
import { EmptyState } from './ui';

export const messageKey = (message: AgentChatMessageViewModel) => message.id;
const MessageBubble = memo(function MessageBubble({
  message,
}: {
  message: AgentChatMessageViewModel;
}) {
  const { colors } = useTheme();
  const sender = message.role === 'user' ? '你' : '助手（预置示例）';
  return (
    <View
      testID={`message-${message.id}`}
      style={{
        alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
        width: '92%',
        gap: 8,
        padding: 16,
        marginVertical: 8,
        borderRadius: tokens.radius.md,
        backgroundColor: message.role === 'user' ? colors.tint : colors.surface,
        borderWidth: 1,
        borderColor: colors.border,
      }}
    >
      <Text style={[tokens.type.caption, { color: colors.muted }]}>
        {sender} · Demo · {message.source === 'local-preview' ? '本地输入' : '合成示例'} ·{' '}
        {message.timeLabel}
      </Text>
      <Text
        selectable
        accessibilityLabel={`${sender}：${message.text}`}
        style={[tokens.type.body, { color: colors.text, flexShrink: 1 }]}
      >
        {message.text}
      </Text>
    </View>
  );
});
export function ChatMessageList({
  messages,
  header,
  footer,
  scrollToLatest = 0,
}: {
  messages: readonly AgentChatMessageViewModel[];
  header?: ReactElement;
  footer?: ReactElement;
  scrollToLatest?: number;
}) {
  const list = useRef<FlatList<AgentChatMessageViewModel>>(null);
  const lastScroll = useRef(0);
  return (
    <FlatList
      ref={list}
      onContentSizeChange={() => {
        if (scrollToLatest !== lastScroll.current) {
          lastScroll.current = scrollToLatest;
          list.current?.scrollToEnd({ animated: false });
        }
      }}
      testID="chat-message-list"
      accessibilityLabel="对话消息列表"
      style={{ flex: 1 }}
      contentContainerStyle={{
        paddingHorizontal: 16,
        paddingBottom: 24,
        width: '100%',
        maxWidth: tokens.layout.maxWidth,
        alignSelf: 'center',
      }}
      data={messages}
      keyExtractor={messageKey}
      renderItem={({ item }) => <MessageBubble message={item} />}
      initialNumToRender={12}
      maxToRenderPerBatch={12}
      windowSize={5}
      keyboardShouldPersistTaps="handled"
      ListHeaderComponent={header}
      ListFooterComponent={footer}
      ListEmptyComponent={
        <EmptyState
          title="还没有对话"
          description="输入内容，添加到本地预览。不会发送给 AI，也不会保存到历史。"
        />
      }
    />
  );
}
