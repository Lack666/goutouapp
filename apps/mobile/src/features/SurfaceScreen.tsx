import { useRouter } from 'expo-router';
import { TextInput } from 'react-native';
import type { SurfaceId } from '../contracts/shell';
import {
  AppHeader,
  BodyText,
  DemoNotice,
  PrimaryButton,
  ScreenContainer,
  SectionCard,
} from '../components/ui';
import { StatePreview } from '../components/StatePreview';
import { useSurface } from '../hooks/useSurface';
import { useTheme } from '../theme/ThemeProvider';
import { tokens } from '../theme/tokens';

const headings = {
  chat: ['对话', '整理你的困惑，也给自己一点空间。'],
  relationship: ['关系资料', '认识自己，也理解你正在关注的人。'],
  import: ['导入与分析', '让分散的聊天记录有一个清楚的入口。'],
  history: ['历史记录', '回看过去的交流。'],
} as const;

export default function SurfaceScreen({ id }: { id: Exclude<SurfaceId, 'home' | 'settings'> }) {
  const router = useRouter();
  const { state, scenario, setScenario, retry } = useSurface(id);
  const { colors } = useTheme();
  const [title, subtitle] = headings[id];
  const back = () => (router.canGoBack() ? router.back() : router.replace('/'));
  return (
    <ScreenContainer>
      <AppHeader title={title} subtitle={subtitle} onBack={back} />
      <DemoNotice />
      <StatePreview state={state} scenario={scenario} onSelect={setScenario} onRetry={retry} />
      {id === 'chat' && (
        <SectionCard title="消息输入区">
          <TextInput
            accessibilityLabel="消息输入（尚未开放）"
            accessibilityState={{ disabled: true }}
            editable={false}
            multiline
            placeholder="消息发送尚未开放"
            placeholderTextColor={colors.muted}
            style={{
              ...tokens.type.body,
              color: colors.text,
              backgroundColor: colors.tint,
              padding: tokens.space.lg,
              borderRadius: tokens.radius.sm,
              minHeight: tokens.layout.touchTarget,
            }}
          />
          <PrimaryButton label="发送（尚未开放）" disabled />
        </SectionCard>
      )}
      {id === 'relationship' && (
        <SectionCard title="资料区域">
          <BodyText muted>个人资料 · 对象资料 · 关系背景</BodyText>
          <PrimaryButton label="编辑资料（尚未开放）" disabled />
        </SectionCard>
      )}
      {id === 'import' && (
        <>
          <SectionCard title="聊天记录入口">
            <BodyText muted>文件选择和上传尚未开放。</BodyText>
            <PrimaryButton label="选择文件（尚未开放）" disabled />
          </SectionCard>
          <SectionCard title="分析展示区">
            <BodyText muted>尚无分析内容；不会根据空白资料给出关系判断。</BodyText>
          </SectionCard>
        </>
      )}
    </ScreenContainer>
  );
}
