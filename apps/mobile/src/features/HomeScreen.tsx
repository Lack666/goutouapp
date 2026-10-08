import { useRouter } from 'expo-router';
import {
  AppHeader,
  BodyText,
  DemoNotice,
  PrimaryButton,
  ScreenContainer,
  SectionCard,
} from '../components/ui';
import { useSurface } from '../hooks/useSurface';
import { routes } from '../navigation/routes';

export default function HomeScreen() {
  const router = useRouter();
  const { state } = useSurface('home');
  if (state.status !== 'empty') return null;
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
