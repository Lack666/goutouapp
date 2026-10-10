import { memo, type ReactElement } from 'react';
import { FlatList, Text, View } from 'react-native';
import { historyKey, type HistoryItemViewModel } from '../contracts/history';
import { useTheme } from '../theme/ThemeProvider';
import { tokens } from '../theme/tokens';
import { EmptyState } from './ui';

const HistoryRow = memo(function HistoryRow({ item }: { item: HistoryItemViewModel }) {
  const { colors } = useTheme();
  const sender =
    item.kind === 'agent'
      ? item.role === 'user'
        ? '用户 · user'
        : item.provenance === 'server'
          ? 'AI 助手 · assistant'
          : 'AI 助手示例 · assistant'
      : `${item.sender} · ${item.rawSpeakerLabel}`;
  return (
    <View
      testID={`history-row-${item.id}`}
      style={{
        backgroundColor: colors.surface,
        borderColor: colors.border,
        borderWidth: 1,
        borderRadius: tokens.radius.md,
        padding: 16,
        marginVertical: 8,
        gap: 8,
      }}
    >
      <Text style={[tokens.type.caption, { color: colors.muted }]}>
        {sender} · {item.provenance === 'server' ? '服务器记录' : 'Demo · 匿名合成'}
      </Text>
      <Text
        selectable
        accessibilityLabel={`${sender}：${item.content}`}
        style={[tokens.type.body, { color: colors.text }]}
      >
        {item.content}
      </Text>
      <Text style={[tokens.type.caption, { color: colors.muted }]}>
        历史时间：{item.timestamp}
        {'\n'}来源：{item.datasetId} · source_index {item.sourceIndex}
        {'\n'}关系：
        {item.relationshipId ?? (item.provenance === 'server' ? '通用 AI 对话' : '通用 AI 示例')}
        {item.kind === 'relationship' &&
          item.provenance === 'server' &&
          `\n原始时间：${item.originalTimestamp} · 源时区 ${item.sourceTimezone}\nMessage ID：${item.id}`}
      </Text>
    </View>
  );
});
export function HistoryList({
  items,
  header,
  footer,
  connected = false,
}: {
  items: readonly HistoryItemViewModel[];
  header: ReactElement;
  footer?: ReactElement;
  connected?: boolean;
}) {
  return (
    <FlatList
      testID="history-list"
      accessibilityLabel="历史消息列表"
      style={{ flex: 1 }}
      contentContainerStyle={{
        padding: 16,
        maxWidth: tokens.layout.maxWidth,
        width: '100%',
        alignSelf: 'center',
      }}
      data={items}
      keyExtractor={historyKey}
      renderItem={({ item }) => <HistoryRow item={item} />}
      initialNumToRender={12}
      maxToRenderPerBatch={12}
      windowSize={5}
      ListHeaderComponent={header}
      ListFooterComponent={footer}
      ListEmptyComponent={
        <EmptyState
          title="还没有历史记录"
          description={
            connected
              ? '当前范围尚无已读取的服务器消息。'
              : '当前本地演示窗口为空；不是服务器保存的历史。'
          }
        />
      }
    />
  );
}
