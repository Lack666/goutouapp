import { render, screen, fireEvent, act } from '@testing-library/react-native';
import { ConnectedImportScreen } from '../src/features/ConnectedImportScreen';
import { ConnectedHistoryScreen } from '../src/features/ConnectedHistoryScreen';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import type { Connection } from '../src/session/ConnectionProvider';
import { setup, prepare, sessions, person, rel, json } from './importSupport';
import { HistoryController } from '../src/data/historyController';
import { ErasureController } from '../src/data/erasureController';
jest.mock('expo-router', () => ({
  useLocalSearchParams: () => ({}),
  useRouter: () => ({ canGoBack: () => false, replace: jest.fn(), push: jest.fn() }),
  useFocusEffect: (callback: () => () => void) =>
    jest.requireActual<typeof import('react')>('react').useEffect(callback, [callback]),
}));
jest.mock('../src/data/filePicker', () => ({ pickImportFile: jest.fn(async () => null) }));
jest.mock('../src/components/DevelopmentSessionControls', () => ({
  DevelopmentSessionControls: () => null,
}));
async function connection() {
  const created = await setup(async (r) =>
    r.url.includes('/messages') ? json({ items: [], next_cursor: null }) : undefined,
  );
  const resources = {
    pages: {
      persons: {
        items: [{ id: person, nickname: '匿名对象' }],
        status: 'ready',
        error: null,
        cursor: null,
      },
      relationships: {
        items: [
          {
            id: rel,
            person: { id: person, nickname: '匿名对象' },
            displayName: '匿名对象',
            source: 'server',
          },
        ],
        status: 'ready',
        error: null,
        cursor: null,
      },
      conversations: { items: [], status: 'ready', error: null, cursor: null },
    },
    details: {},
    creates: {},
  };
  const value = {
    session: created.session,
    imports: created.controller,
    history: new HistoryController(created.transport, created.session),
    erasure: new ErasureController(
      created.transport,
      created.session,
      () => person,
      () => undefined,
      async () => undefined,
    ),
    resources: {
      snapshot: () => resources,
      subscribe: () => () => undefined,
      load: jest.fn(async () => undefined),
    },
  } as unknown as Connection;
  return { ...created, value };
}
afterEach(async () => {
  for (const session of sessions.splice(0)) await session.logout();
});
it('Connected source has real picker and explicit upload, without fabricated analysis or Demo', async () => {
  const { value, requests } = await connection();
  await act(async () => {
    render(
      <ThemeProvider>
        <ConnectedImportScreen connection={value} />
      </ThemeProvider>,
    );
  });
  expect(screen.getByRole('button', { name: '上传并创建任务' })).toBeDisabled();
  expect(value.resources.load).not.toHaveBeenCalled(); // Preserve existing owned selections.
  expect(screen.queryByText('本地演示 · Demo')).toBeNull();
  await act(async () => {
    fireEvent.press(screen.getByRole('button', { name: '选择微信 Markdown 文件' }));
  });
  expect(requests).toHaveLength(0);
  expect(screen.queryByText('聊天记录已成功导入，可在历史记录中查看。')).toBeNull();
});
it('formal receipt renders server IDs/counts and states the analysis boundary', async () => {
  const { value, controller } = await connection();
  await prepare(controller);
  await controller.finalize();
  await act(async () => {
    render(
      <ThemeProvider>
        <ConnectedImportScreen connection={value} />
      </ThemeProvider>,
    );
  });
  expect(screen.getByText('聊天记录已成功导入，可在历史记录中查看。')).toBeOnTheScreen();
  expect(screen.getByText(/没有运行 AI 关系分析/)).toBeOnTheScreen();
  expect(screen.getByText(/Dataset：/)).toBeOnTheScreen();
});
it('History uses the existing virtualized list and starts without fetching another relationship', async () => {
  const { value, requests } = await connection();
  await act(async () => {
    render(
      <ThemeProvider>
        <ConnectedHistoryScreen connection={value} />
      </ThemeProvider>,
    );
  });
  const list = screen.getByTestId('history-list');
  expect(list.props.initialNumToRender).toBe(12);
  expect(list.props.windowSize).toBe(5);
  expect(requests).toHaveLength(0);
  expect(screen.getByRole('button', { name: '加载更多服务器历史' })).toBeDisabled();
});
it('AI domain switch immediately clears imported rows and requires explicit Conversation', async () => {
  const { value } = await connection();
  await act(async () => {
    render(
      <ThemeProvider>
        <ConnectedHistoryScreen connection={value} />
      </ThemeProvider>,
    );
  });
  await act(async () => {
    fireEvent.press(screen.getByRole('button', { name: 'AI 对话' }));
  });
  expect(screen.getByText('明确选择 Conversation')).toBeOnTheScreen();
  expect(value.history.snapshot().kind).toBe('agent');
  expect(value.history.snapshot().items).toEqual([]);
});
