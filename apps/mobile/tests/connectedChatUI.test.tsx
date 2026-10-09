import { render, screen } from '@testing-library/react-native';
import { ConnectedChatScreen } from '../src/features/ConnectedChatScreen';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import type { Connection } from '../src/session/ConnectionProvider';
import type { ConnectedChatView } from '../src/data/agentChatController';
import { asUUID } from '../src/api/uuid';
jest.mock('expo-router', () => ({
  useFocusEffect: () => undefined,
  useLocalSearchParams: () => ({ conversationId: '11111111-1111-4111-8111-111111111111' }),
  useRouter: () => ({ canGoBack: () => false, replace: jest.fn() }),
}));
jest.mock('../src/components/DevelopmentSessionControls', () => ({
  DevelopmentSessionControls: () => null,
}));
const conv = asUUID('11111111-1111-4111-8111-111111111111');
const base: ConnectedChatView = {
  conversationId: conv,
  relationshipId: null,
  scope: 'ready',
  messages: [],
  history: 'ready',
  cursor: null,
  historyError: null,
  phase: 'idle',
  progress: null,
  runId: null,
  operationKey: null,
  memoryStatus: null,
  warnings: [],
  error: null,
  errorKind: null,
};
function show(view: Partial<ConnectedChatView>) {
  const current = { ...base, ...view };
  const session = { mode: 'connected', status: 'authenticated', epoch: 1 };
  const resources = { pages: { conversations: { items: [], error: null } } };
  const connection = {
    session: { snapshot: () => session, subscribe: () => () => undefined },
    resources: { snapshot: () => resources, subscribe: () => () => undefined },
    chat: {
      snapshot: () => current,
      subscribe: () => () => undefined,
      leave: jest.fn(),
      pause: jest.fn(),
    },
  } as unknown as Connection;
  return render(
    <ThemeProvider>
      <ConnectedChatScreen connection={connection} />
    </ThemeProvider>,
  );
}
it('pending/running disables send, allows stopping wait and displays progress apart from messages', async () => {
  await show({
    phase: 'running',
    progress: 'checking_safety',
    operationKey: 'synthetic-operation',
  });
  expect(screen.getByText('Agent 状态：运行中')).toBeOnTheScreen();
  expect(screen.getByText('检查安全')).toBeOnTheScreen();
  expect(screen.getByRole('button', { name: '发送 Agent 消息' })).toBeDisabled();
  expect(screen.getByRole('button', { name: '停止等待' })).toBeOnTheScreen();
  expect(screen.queryAllByLabelText(/^助手：/)).toHaveLength(0);
});
it('failed shows safe error and same-operation recovery without a synthetic assistant', async () => {
  await show({
    phase: 'failed',
    error: '服务器运行失败，未确认新的回答。',
    operationKey: 'synthetic-operation',
  });
  expect(screen.getByText('Agent 状态：运行失败')).toBeOnTheScreen();
  expect(screen.getByRole('button', { name: '重试原操作（REST）' })).toBeOnTheScreen();
  expect(screen.queryAllByLabelText(/^助手/)).toHaveLength(0);
  expect(screen.queryByText('演示状态预览')).toBeNull();
});
it('outcome unknown prevents a new send and never claims server rollback', async () => {
  await show({ phase: 'running_unknown', operationKey: 'synthetic-operation' });
  expect(screen.getByText('Agent 状态：无法确认该请求是否已完成。')).toBeOnTheScreen();
  expect(screen.getByLabelText('Agent 消息输入')).toHaveProp('editable', false);
  expect(screen.getByRole('button', { name: '重试原操作（SSE）' })).toBeOnTheScreen();
});
it('completed displays committed server text and read-only pending confirmation without FIU claims', async () => {
  await show({
    phase: 'completed',
    memoryStatus: 'pending_confirmation',
    runId: conv,
    messages: [
      {
        id: conv,
        role: 'assistant',
        text: '服务端文本回答',
        source: 'server',
        timeLabel: '已提交',
      },
    ],
  });
  expect(screen.getByText('Agent 状态：运行完成')).toBeOnTheScreen();
  expect(screen.getByLabelText('助手：服务端文本回答')).toBeOnTheScreen();
  expect(screen.getByText(/需要通过正式 Memory 确认服务/)).toBeOnTheScreen();
  expect(screen.queryByText('助手（预置示例）')).toBeNull();
});
