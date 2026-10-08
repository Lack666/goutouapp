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
      <Text style={[tokens.type.caption, { color: colors.muted }]}>{sender} · Demo · 匿名合成</Text>
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
        {'\n'}关系：{item.relationshipId ?? '通用 AI 示例'}
      </Text>
    </View>
  );
});
export function HistoryList({
  items,
  header,
  footer,
}: {
  items: readonly HistoryItemViewModel[];
  header: ReactElement;
  footer?: ReactElement;
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
          description="当前本地演示窗口为空；不是服务器保存的历史。"
        />
      }
    />
  );
}
