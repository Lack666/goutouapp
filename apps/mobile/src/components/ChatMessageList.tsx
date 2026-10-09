import { memo, useRef } from 'react';
import type { ReactElement } from 'react';
import type { LayoutChangeEvent } from 'react-native';
import { FlatList, Text, View } from 'react-native';
import type { AgentChatMessageViewModel } from '../contracts/chat';
import { useTheme } from '../theme/ThemeProvider';
import { tokens } from '../theme/tokens';
import { EmptyState } from './ui';

export const messageKey = (message: AgentChatMessageViewModel) => message.id;
const MessageBubble = memo(function MessageBubble({
  message,
  onLayout,
}: {
  message: AgentChatMessageViewModel;
  onLayout?: (event: LayoutChangeEvent) => void;
}) {
  const { colors } = useTheme();
  const sender =
    message.role === 'user' ? '你' : message.source === 'server' ? '助手' : '助手（预置示例）';
  return (
    <View
      testID={`message-${message.id}`}
      onLayout={onLayout}
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
        {sender} ·{' '}
        {message.source === 'server'
          ? '服务器已提交'
          : `Demo · ${message.source === 'local-preview' ? '本地输入' : '合成示例'}`}{' '}
        · {message.timeLabel}
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
  connected = false,
}: {
  messages: readonly AgentChatMessageViewModel[];
  header?: ReactElement;
  footer?: ReactElement;
  scrollToLatest?: number;
  connected?: boolean;
}) {
  const list = useRef<FlatList<AgentChatMessageViewModel>>(null);
  const lastScroll = useRef(0);
  return (
    <FlatList
      ref={list}
      onContentSizeChange={() => {
        if (scrollToLatest !== lastScroll.current) {
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
      renderItem={({ item, index }) => (
        <MessageBubble
          message={item}
          onLayout={
            index === messages.length - 1
              ? () => {
                  if (scrollToLatest !== lastScroll.current) {
                    requestAnimationFrame(() => {
                      list.current?.scrollToEnd({ animated: false });
                      lastScroll.current = scrollToLatest;
                    });
                  }
                }
              : undefined
          }
        />
      )}
      initialNumToRender={12}
      maxToRenderPerBatch={12}
      windowSize={5}
      keyboardShouldPersistTaps="handled"
      ListHeaderComponent={header}
      ListFooterComponent={footer}
      ListEmptyComponent={
        <EmptyState
          title="还没有对话"
          description={
            connected
              ? '尚无服务器确认的 Agent 消息。'
              : '输入内容，添加到本地预览。不会发送给 AI，也不会保存到历史。'
          }
        />
      }
    />
  );
}
