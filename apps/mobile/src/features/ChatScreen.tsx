import { useMemo, useRef, useState } from 'react';
import { useConnection } from '../session/ConnectionProvider';
import { ConnectedChatScreen } from './ConnectedChatScreen';
import { useRouter } from 'expo-router';
import { KeyboardAvoidingView, Platform, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type {
  AgentChatMessageViewModel,
  ChatRunPresentationState,
  ChatScreenViewModel,
} from '../contracts/chat';
import { appendLocalPreview, COMPOSER_LIMIT } from '../contracts/chat';
import { useDataSource } from '../data/DataSourceProvider';
import { useTheme } from '../theme/ThemeProvider';
import {
  AppHeader,
  BodyText,
  DemoNotice,
  PrimaryButton,
  ScreenContainer,
  EmptyState,
} from '../components/ui';
import { useRelationshipScope, useLocalNavigation } from '../navigation/scope';
import { ChatMessageList } from '../components/ChatMessageList';
import { ChatComposer } from '../components/ChatComposer';
import { ChatRunStatus, FiuPreview, runPreviews } from '../components/ChatRunPreview';

export default function ChatScreen() {
  const connection = useConnection();
  return connection?.session.snapshot().mode === 'connected' ? (
    <ConnectedChatScreen connection={connection} />
  ) : (
    <DemoChatScreen />
  );
}
function DemoChatScreen() {
  const source = useDataSource();
  const scope = useRelationshipScope();
  const nav = useLocalNavigation();
  const profiles = useMemo(() => source.readRelationships(), [source]);
  const model = useMemo(() => source.readChat(scope), [source, scope]);
  if (scope !== null && !profiles.some((p) => p.id === scope))
    return (
      <ScreenContainer>
        <AppHeader title="对话" subtitle="关系范围未提供" onBack={nav.back} />
        <DemoNotice />
        <EmptyState title="关系不可用" description="不会显示另一段关系的对话，请返回修改。" />
      </ScreenContainer>
    );
  return <ChatSession key={`${model.thread.id}:${scope}`} model={model} />;
}
export function ChatSession({ model }: { model: ChatScreenViewModel }) {
  const router = useRouter();
  const { colors } = useTheme();
  const [messages, setMessages] = useState<readonly AgentChatMessageViewModel[]>([]);
  const [text, setText] = useState('');
  const [state, setState] = useState<ChatRunPresentationState>('idle');
  const [controls, setControls] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [scrollRevision, setScrollRevision] = useState(0);
  const sequence = useRef(0);
  const disabled =
    state === 'starting' || state === 'progressing' || state === 'pending_confirmation';
  const preview = () => {
    const value = text.trim();
    if (disabled || !value || text.length > COMPOSER_LIMIT) return;
    sequence.current += 1;
    setScrollRevision(sequence.current);
    const id = `local-${sequence.current}`;
    const timeLabel = new Date().toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    });
    setMessages((current) =>
      appendLocalPreview(current, {
        id,
        role: 'user',
        text: value,
        timeLabel,
        source: 'local-preview',
      }),
    );
    setText('');
    setFeedback('仅在本地预览，尚未发送给 AI');
  };
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ChatMessageList
          messages={messages}
          scrollToLatest={scrollRevision}
          header={
            <>
              <AppHeader
                title="对话"
                subtitle={model.thread.title}
                onBack={() => (router.canGoBack() ? router.back() : router.replace('/'))}
              />
              <DemoNotice />
              <ChatRunStatus state={state} onReset={() => setState('idle')} />
              <View style={{ gap: 12, marginBottom: 16 }}>
                <PrimaryButton
                  label="替换为合成对话示例"
                  variant="quiet"
                  onPress={() => {
                    setMessages(model.thread.messages);
                    setFeedback('预置合成示例 · 未分析输入');
                  }}
                />
                <PrimaryButton
                  label="演示状态预览"
                  variant="quiet"
                  selected={controls}
                  onPress={() => setControls(!controls)}
                />
                {controls && (
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                    {runPreviews.map((p) => (
                      <PrimaryButton
                        key={p.state}
                        label={p.label}
                        variant="quiet"
                        selected={state === p.state}
                        onPress={() => setState(p.state)}
                      />
                    ))}
                  </View>
                )}
                {state === 'completed' && <FiuPreview items={model.fiu} />}
                <BodyText muted>
                  安全提醒 · Demo：尚无安全评估结果。演示内容不判断他人心理或关系结局。
                </BodyText>
                <PrimaryButton label="发送（尚未开放）" disabled />
              </View>
            </>
          }
        />
        <ChatComposer
          state={{ text, disabled }}
          feedback={feedback}
          onChange={setText}
          onPreview={preview}
        />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
