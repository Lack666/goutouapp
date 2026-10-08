import type { PropsWithChildren, ReactNode } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTheme } from '../theme/ThemeProvider';
import { tokens } from '../theme/tokens';

export function ScreenContainer({ children }: PropsWithChildren) {
  const { colors } = useTheme();
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.scroll}>
          <View style={styles.content}>{children}</View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

export function BodyText({
  children,
  muted = false,
  live = false,
}: PropsWithChildren<{ muted?: boolean; live?: boolean }>) {
  const { colors } = useTheme();
  return (
    <Text
      accessibilityLiveRegion={live ? 'polite' : undefined}
      style={[tokens.type.body, { color: muted ? colors.muted : colors.text }]}
    >
      {children}
    </Text>
  );
}

export function AppHeader({
  title,
  subtitle,
  onBack,
}: {
  title: string;
  subtitle: string;
  onBack?: () => void;
}) {
  const { colors } = useTheme();
  return (
    <View style={styles.header}>
      {onBack && (
        <PrimaryButton
          label="返回"
          accessibilityLabel="返回上一级"
          variant="quiet"
          onPress={onBack}
        />
      )}
      <Text accessibilityRole="header" style={[tokens.type.title, { color: colors.text }]}>
        {title}
      </Text>
      <BodyText muted>{subtitle}</BodyText>
    </View>
  );
}

interface ButtonProps {
  label: string;
  accessibilityLabel?: string;
  onPress?: () => void;
  disabled?: boolean;
  selected?: boolean;
  variant?: 'primary' | 'quiet';
}
export function PrimaryButton({
  label,
  accessibilityLabel = label,
  onPress,
  disabled = false,
  selected,
  variant = 'primary',
}: ButtonProps) {
  const { colors } = useTheme();
  const quiet = variant === 'quiet';
  const webToggle =
    Platform.OS === 'web' && selected !== undefined ? { 'aria-pressed': selected } : {};
  return (
    <Pressable
      {...webToggle}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      accessibilityState={{ disabled, ...(selected === undefined ? {} : { selected }) }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        {
          backgroundColor: disabled ? colors.disabled : quiet ? colors.tint : colors.primary,
          opacity: pressed ? 0.75 : 1,
          borderWidth: 1,
          borderColor: selected ? colors.primary : 'transparent',
        },
      ]}
    >
      <Text
        style={[
          tokens.type.button,
          {
            color: disabled ? colors.muted : quiet ? colors.text : colors.onPrimary,
            textAlign: 'center',
          },
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

export function SectionCard({
  title,
  children,
  trailing,
}: PropsWithChildren<{ title: string; trailing?: ReactNode }>) {
  const { colors } = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text accessibilityRole="header" style={[tokens.type.heading, { color: colors.text }]}>
        {title}
      </Text>
      {children}
      {trailing}
    </View>
  );
}

export function DemoNotice() {
  return (
    <SectionCard title="本地演示 · Demo">
      <BodyText muted>
        当前未连接服务器。页面展示的是演示布局，没有登录、真实对话或已保存资料。
      </BodyText>
    </SectionCard>
  );
}
export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <SectionCard title={title}>
      <BodyText muted>{description}</BodyText>
    </SectionCard>
  );
}
export function LoadingState() {
  const { colors } = useTheme();
  return (
    <SectionCard title="演示加载中">
      <ActivityIndicator accessibilityLabel="演示加载中" color={colors.primary} />
      <BodyText muted>本地状态预览，可切回空状态。</BodyText>
    </SectionCard>
  );
}
export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { colors } = useTheme();
  return (
    <SectionCard title="演示读取失败">
      <Text accessibilityRole="alert" style={[tokens.type.body, { color: colors.danger }]}>
        {message}
      </Text>
      <PrimaryButton label="重试" onPress={onRetry} />
    </SectionCard>
  );
}

const styles = StyleSheet.create({
  scroll: { flexGrow: 1, padding: tokens.space.lg },
  content: {
    width: '100%',
    maxWidth: tokens.layout.maxWidth,
    alignSelf: 'center',
    gap: tokens.space.lg,
    paddingBottom: tokens.space.xxl,
  },
  header: { gap: tokens.space.sm, paddingVertical: tokens.space.lg, alignItems: 'flex-start' },
  button: {
    minHeight: tokens.layout.touchTarget,
    minWidth: tokens.layout.touchTarget,
    borderRadius: tokens.radius.sm,
    justifyContent: 'center',
    paddingVertical: tokens.space.md,
    paddingHorizontal: tokens.space.lg,
  },
  card: {
    borderWidth: 1,
    borderRadius: tokens.radius.md,
    padding: tokens.space.xl,
    gap: tokens.space.md,
  },
});
