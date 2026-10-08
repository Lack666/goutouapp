import { useRouter } from 'expo-router';
import { AppHeader, PrimaryButton, ScreenContainer } from '../src/components/ui';
export default function NotFoundRoute() {
  const router = useRouter();
  return (
    <ScreenContainer>
      <AppHeader title="页面不存在" subtitle="从首页选择一个入口继续。" />
      <PrimaryButton label="回到首页" onPress={() => router.replace('/')} />
    </ScreenContainer>
  );
}
