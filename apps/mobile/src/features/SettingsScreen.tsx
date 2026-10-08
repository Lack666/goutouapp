import { useRouter } from 'expo-router';
import { View } from 'react-native';
import {
  AppHeader,
  BodyText,
  DemoNotice,
  PrimaryButton,
  ScreenContainer,
  SectionCard,
} from '../components/ui';
import { useTheme, type ThemePreference } from '../theme/ThemeProvider';
import { tokens } from '../theme/tokens';

const preferences: readonly { id: ThemePreference; label: string }[] = [
  { id: 'system', label: '跟随系统' },
  { id: 'light', label: '浅色' },
  { id: 'dark', label: '深色' },
];
export default function SettingsScreen() {
  const router = useRouter();
  const { preference, setPreference, mode } = useTheme();
  const back = () => (router.canGoBack() ? router.back() : router.replace('/'));
  return (
    <ScreenContainer>
      <AppHeader title="设置" subtitle="让界面更适合你。" onBack={back} />
      <SectionCard title="外观">
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: tokens.space.sm }}>
          {preferences.map((item) => (
            <PrimaryButton
              key={item.id}
              label={item.label}
              variant="quiet"
              selected={preference === item.id}
              onPress={() => setPreference(item.id)}
            />
          ))}
        </View>
        <BodyText muted>
          当前外观：{mode === 'dark' ? '深色' : '浅色'}。本地偏好仅在本次打开期间保留。
        </BodyText>
      </SectionCard>
      <SectionCard title="应用信息">
        <BodyText>狗头军师 · 0.1.0</BodyText>
        <BodyText muted>移动端基础演示 · Phase 7A</BodyText>
      </SectionCard>
      <DemoNotice />
      <SectionCard title="账户与记忆">
        <BodyText muted>尚未接入账户或记忆服务。当前没有可管理的服务器资料。</BodyText>
      </SectionCard>
    </ScreenContainer>
  );
}
