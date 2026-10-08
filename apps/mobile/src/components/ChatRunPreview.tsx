import { View, Text } from 'react-native';
import type { ChatRunPresentationState, FiuPreviewItem } from '../contracts/chat';
import { BodyText, PrimaryButton, SectionCard, LoadingState } from './ui';
import { useTheme } from '../theme/ThemeProvider';
import { tokens } from '../theme/tokens';

export const runPreviews: readonly {
  state: ChatRunPresentationState;
  label: string;
  description: string;
}[] = [
  { state: 'idle', label: '空状态', description: '本地就绪，可以预览输入。服务器尚未连接。' },
  {
    state: 'unavailable',
    label: '未连接状态',
    description: '未连接服务器。当前没有网络操作可以重试。',
  },
  { state: 'starting', label: '加载状态', description: '启动展示示例；没有创建真实任务。' },
  {
    state: 'progressing',
    label: '进度状态',
    description: '状态展示示例：正在整理信息。未来先展示进度，再展示完整回复。',
  },
  { state: 'completed', label: '结果状态', description: '预置结果展示示例；没有分析你的输入。' },
  { state: 'failed', label: '错误状态', description: '演示读取失败。重试仅重置 Demo 状态。' },
  {
    state: 'pending_confirmation',
    label: '待确认状态',
    description: '此操作需要你确认后才能执行。当前仅为演示；未收到确认挑战。',
  },
];
export function ChatRunStatus({
  state,
  onReset,
}: {
  state: ChatRunPresentationState;
  onReset: () => void;
}) {
  const { colors } = useTheme();
  return (
    <View style={{ gap: 12, marginVertical: 12 }}>
      <Text
        accessibilityRole={state === 'failed' ? 'alert' : undefined}
        accessibilityLiveRegion="polite"
        style={[tokens.type.body, { color: state === 'failed' ? colors.danger : colors.muted }]}
      >
        Demo · {runPreviews.find((p) => p.state === state)?.description}
      </Text>
      {state === 'starting' && <LoadingState />}
      {state === 'failed' && (
        <>
          <BodyText muted>Demo state reset：只恢复本地就绪状态，不进行网络重试。</BodyText>
          <PrimaryButton label="重试" onPress={onReset} />
        </>
      )}
      {state === 'pending_confirmation' && <PrimaryButton label="确认执行（尚未开放）" disabled />}
    </View>
  );
}
export function FiuPreview({ items }: { items: readonly FiuPreviewItem[] }) {
  return (
    <SectionCard title="如何区分信息 · 合成示例">
      <BodyText muted>以下为预置教学内容，未分析当前输入。</BodyText>
      {items.map((item, index) => (
        <View key={`${item.kind}-${index}`} style={{ gap: 4 }}>
          <BodyText>
            {item.kind === 'fact' ? '事实' : item.kind === 'inference' ? '推测' : '尚不确定'}：
            {item.text}
          </BodyText>
          {item.kind === 'fact' && <BodyText muted>{item.provenance}</BodyText>}
          {item.kind === 'inference' && <BodyText muted>{item.alternative}</BodyText>}
        </View>
      ))}
    </SectionCard>
  );
}
