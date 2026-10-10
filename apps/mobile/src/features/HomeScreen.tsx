import { useRouter } from 'expo-router';
import { useConnection } from '../session/ConnectionProvider';
import {
  AppHeader,
  BodyText,
  DemoNotice,
  ErrorState,
  LoadingState,
  PrimaryButton,
  ScreenContainer,
  SectionCard,
} from '../components/ui';
import { useSurface } from '../hooks/useSurface';
import { routes } from '../navigation/routes';

export default function HomeScreen() {
  const connection = useConnection();
  return connection?.session.snapshot().mode === 'connected' ? (
    <ConnectedHomeScreen />
  ) : (
    <DemoHomeScreen />
  );
}
function ConnectedHomeScreen() {
  const router = useRouter();
  return (
    <ScreenContainer>
      <AppHeader title="狗头军师" subtitle="Connected Development Mode" />
      <SectionCard title="服务器资源">
        <BodyText>在关系资料中创建和选择对象、关系与会话。</BodyText>
        <PrimaryButton label="进入关系资料" onPress={() => router.push('/relationship')} />
        <PrimaryButton label="进入设置" variant="quiet" onPress={() => router.push('/settings')} />
        <PrimaryButton
          label="开始 Agent 对话"
          variant="quiet"
          onPress={() => router.push('/chat')}
        />
        <PrimaryButton
          label="进入导入与分析"
          variant="quiet"
          onPress={() => router.push('/import')}
        />
        <PrimaryButton
          label="进入历史记录"
          variant="quiet"
          onPress={() => router.push('/history')}
        />
        <BodyText muted>
          Agent 对话、微信 Markdown 导入与两种服务器历史已接入。Memory 控制仍未开放联网操作。
        </BodyText>
      </SectionCard>
    </ScreenContainer>
  );
}
function DemoHomeScreen() {
  const router = useRouter();
  const { state, retry } = useSurface('home');
  if (state.status !== 'empty')
    return (
      <ScreenContainer>
        <AppHeader title="狗头军师" subtitle="从一次对话，或一份关系资料开始。" />
        <DemoNotice />
        {state.status === 'loading' ? (
          <LoadingState />
        ) : (
          <ErrorState message={state.message} onRetry={retry} />
        )}
      </ScreenContainer>
    );
  return (
    <ScreenContainer>
      <AppHeader title="狗头军师" subtitle={state.view.description} />
      <SectionCard title="先照顾感受，再梳理关系">
        <BodyText>不急着得出结论。从一次对话，或一份关系资料开始。</BodyText>
        <PrimaryButton label="开始对话" onPress={() => router.push('/chat')} />
      </SectionCard>
      <DemoNotice />
      {routes
        .filter((route) => route.id !== 'chat')
        .map((route) => (
          <SectionCard key={route.id} title={route.label}>
            <BodyText muted>{route.summary}</BodyText>
            <PrimaryButton
              label={`进入${route.label}`}
              variant="quiet"
              onPress={() => router.push(route.path)}
            />
          </SectionCard>
        ))}
    </ScreenContainer>
  );
}
