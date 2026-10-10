import { useState } from 'react';
import { Platform, TextInput } from 'react-native';
import { useConnection, useSessionView, type Connection } from '../session/ConnectionProvider';
import { BodyText, PrimaryButton, SectionCard } from './ui';
import { useTheme } from '../theme/ThemeProvider';

const labels = {
  no_token: '未连接：没有开发凭证',
  clearing: '正在清除设备开发凭证，请保持应用打开',
  checking: '正在验证开发凭证',
  authenticated: '开发会话已连接',
  expired: '开发凭证已过期，请重新获取',
  invalid: '开发凭证无效，请重新获取',
  network_unavailable: '网络或服务器不可用，请检查连接后重新接入',
  storage_error: '安全存储不可用，请重试清除会话',
};
export function ResourceInput({
  label,
  value,
  onChange,
  secret = false,
  maxLength = 120,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  secret?: boolean;
  maxLength?: number;
}) {
  const { colors } = useTheme();
  return (
    <TextInput
      accessibilityLabel={label}
      placeholder={label}
      placeholderTextColor={colors.muted}
      value={value}
      onChangeText={onChange}
      secureTextEntry={secret}
      autoCapitalize="none"
      autoCorrect={false}
      maxLength={maxLength}
      style={{
        color: colors.text,
        borderColor: colors.border,
        borderWidth: 1,
        borderRadius: 8,
        padding: 12,
        minHeight: 48,
      }}
    />
  );
}
export function DevelopmentSessionControls() {
  const connection = useConnection();
  return connection ? <Controls connection={connection} /> : null;
}
function Controls({ connection }: { connection: Connection }) {
  const view = useSessionView(connection);
  const [token, setToken] = useState('');
  return (
    <SectionCard title="Development Session">
      <BodyText>
        {view.mode === 'demo' ? 'Demo Mode · 匿名合成数据' : 'Connected Development Mode'}
      </BodyText>
      <BodyText live>{labels[view.status]}</BodyText>
      <BodyText muted>
        仅供开发联调。由开发者主动录入后端 CLI 的短期凭证，15 分钟后重新获取。
      </BodyText>
      <PrimaryButton
        label="使用 Demo Mode"
        variant="quiet"
        selected={view.mode === 'demo'}
        onPress={() => {
          setToken('');
          connection.session.demo();
        }}
      />
      <PrimaryButton
        label="使用 Connected Development Mode"
        variant="quiet"
        selected={view.mode === 'connected'}
        onPress={() => {
          setToken('');
          connection.session.connected();
        }}
      />
      {view.mode === 'connected' && view.status !== 'authenticated' && (
        <>
          <ResourceInput
            label="开发 JWT（隐藏输入）"
            value={token}
            onChange={setToken}
            secret
            maxLength={4096}
          />
          <PrimaryButton
            label="验证并接入开发会话"
            disabled={!token.trim() || view.status === 'checking'}
            onPress={() => {
              const input = token;
              setToken('');
              void connection.session.connect(input, connection.resources.probe);
            }}
          />
        </>
      )}
      <BodyText muted>
        {Platform.OS === 'web'
          ? 'Web 凭证只存内存，刷新后需重新录入。'
          : '设备凭证使用系统安全存储；恢复时重新验证。'}
      </BodyText>
      <PrimaryButton
        label="清除当前开发会话"
        variant="quiet"
        onPress={() => {
          setToken('');
          connection.session.logout();
        }}
      />
    </SectionCard>
  );
}
