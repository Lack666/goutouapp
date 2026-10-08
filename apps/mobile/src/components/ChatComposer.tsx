import { Text, TextInput, View } from 'react-native';
import type { ChatComposerState } from '../contracts/chat';
import { COMPOSER_LIMIT } from '../contracts/chat';
import { useTheme } from '../theme/ThemeProvider';
import { tokens } from '../theme/tokens';
import { PrimaryButton } from './ui';

export function ChatComposer({
  state,
  onChange,
  onPreview,
  feedback = '',
}: {
  state: ChatComposerState;
  onChange: (text: string) => void;
  onPreview: () => void;
  feedback?: string;
}) {
  const { colors } = useTheme();
  return (
    <View
      style={{
        backgroundColor: colors.surface,
        borderTopWidth: 1,
        borderColor: colors.border,
        padding: 12,
        gap: 8,
        width: '100%',
        maxWidth: tokens.layout.maxWidth,
        alignSelf: 'center',
      }}
    >
      <TextInput
        accessibilityLabel="本地预览消息输入"
        accessibilityState={{ disabled: state.disabled }}
        editable={!state.disabled}
        multiline
        maxLength={COMPOSER_LIMIT}
        value={state.text}
        onChangeText={(text) => onChange(text.slice(0, COMPOSER_LIMIT))}
        placeholder="写下想梳理的内容，仅在本地预览"
        placeholderTextColor={colors.muted}
        style={{
          ...tokens.type.body,
          color: colors.text,
          backgroundColor: colors.tint,
          borderRadius: 12,
          padding: 12,
          minHeight: 60,
          maxHeight: 120,
          textAlignVertical: 'top',
        }}
      />
      <Text style={[tokens.type.caption, { color: colors.muted }]}>
        Demo · {state.text.length}/{COMPOSER_LIMIT} · 不发送、不保存
      </Text>
      {!!feedback && (
        <Text
          accessibilityLiveRegion="polite"
          style={[tokens.type.caption, { color: colors.primary }]}
        >
          {feedback}
        </Text>
      )}
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <View style={{ flex: 1 }}>
          <PrimaryButton
            label="添加到本地预览"
            disabled={state.disabled || !state.text.trim() || state.text.length > COMPOSER_LIMIT}
            onPress={onPreview}
          />
        </View>
        <PrimaryButton
          label="清空"
          variant="quiet"
          disabled={state.disabled || !state.text}
          onPress={() => onChange('')}
        />
      </View>
    </View>
  );
}
