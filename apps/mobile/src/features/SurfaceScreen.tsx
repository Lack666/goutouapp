import { useRouter } from 'expo-router';
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
const headings = {
  import: ['导入与分析', '让分散的聊天记录有一个清楚的入口。'],
  history: ['历史记录', '回看过去的交流。'],
} as const;
export default function SurfaceScreen({ id }: { id: 'import' | 'history' }) {
  const router = useRouter();
  const { state, scenario, setScenario, retry } = useSurface(id);
  const [title, subtitle] = headings[id];
  return (
    <ScreenContainer>
      <AppHeader
        title={title}
        subtitle={subtitle}
        onBack={() => (router.canGoBack() ? router.back() : router.replace('/'))}
      />
      <DemoNotice />
      <StatePreview state={state} scenario={scenario} onSelect={setScenario} onRetry={retry} />
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
