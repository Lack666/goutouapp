import { render, screen, fireEvent, act } from '@testing-library/react-native';
import { ConnectedMemoryPanel } from '../src/features/ConnectedMemoryPanel';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import type { Connection } from '../src/session/ConnectionProvider';
import { setup, sessions, person, rel, other, jobId, json } from './memorySupport';
jest.mock('expo-router', () => ({
  useRouter: () => ({ push: jest.fn() }),
  useFocusEffect: (callback: () => () => void) =>
    jest.requireActual<typeof import('react')>('react').useEffect(callback, [callback]),
}));
afterEach(async () => {
  for (const session of sessions.splice(0))
    await act(async () => {
      await session.logout();
    });
});
async function display(handler?: Parameters<typeof setup>[0]) {
  const created = await setup(handler);
  const resources = {
    pages: {
      persons: {
        items: [{ id: person, nickname: '匿名对象' }],
        status: 'ready',
        error: null,
        cursor: null,
      },
      relationships: {
        items: [{ id: rel, person: { id: person, nickname: '匿名对象' } }],
        status: 'ready',
        error: null,
        cursor: null,
      },
    },
  };
  const value = {
    session: created.session,
    memory: created.controller,
    resources: { snapshot: () => resources, subscribe: () => () => undefined, load: jest.fn() },
  } as unknown as Connection;
  await act(async () => {
    render(
      <ThemeProvider>
        <ConnectedMemoryPanel connection={value} />
      </ThemeProvider>,
    );
  });
  return created;
}
const press = async (name: string) => {
  await act(async () => {
    fireEvent.press(screen.getByRole('button', { name }));
  });
};
it('renders authoritative control, compact facts and actual configured retention with no Demo fallback', async () => {
  await display();
  expect(screen.getByText('Consent：已授权')).toBeOnTheScreen();
  expect(screen.getByText('匿名合成的明确事实')).toBeOnTheScreen();
  expect(screen.getByText(/New memories expire 37 days/)).toBeOnTheScreen();
  expect(screen.queryByText(/Demo/)).toBeNull();
  expect(screen.getByRole('button', { name: '确认撤销该最新操作' })).toBeDisabled();
});
it('Undo requires fresh preview and explicit user confirmation before POST', async () => {
  const { requests } = await display();
  await press('检查最新 Undo 并准备确认');
  expect(screen.getByText(`最新 operation ID：${other}`)).toBeOnTheScreen();
  expect(requests.some((request) => request.url.endsWith('/undo'))).toBe(false);
  await press('确认撤销该最新操作');
  expect(screen.getByText('Action：undo · Status：undone')).toBeOnTheScreen();
});
it('delete one shows server challenge count and receipt only after explicit execution', async () => {
  const { requests } = await display();
  await press(`准备删除记忆 ${jobId}`);
  expect(screen.getByText('服务器待删数量：3')).toBeOnTheScreen();
  expect(requests.some((request) => request.url.endsWith('/execute'))).toBe(false);
  await press('确认执行服务器删除');
  expect(screen.getByText('Action：delete_one · Status：deleted')).toBeOnTheScreen();
});
it('all requires explicit consent choice and invalidates old challenge when it changes', async () => {
  const { requests } = await display();
  expect(screen.getByRole('button', { name: '准备删除全部本人记忆' })).toBeDisabled();
  await press('全部删除后保留授权');
  await press('准备删除全部本人记忆');
  expect(screen.getByText('删除后撤销授权：否')).toBeOnTheScreen();
  await press('全部删除后撤销授权');
  expect(screen.queryByText('服务器待删数量：3')).toBeNull();
  expect(screen.getByRole('button', { name: '确认撤销该最新操作' })).toBeDisabled();
  expect(requests.some((request) => request.url.endsWith('/execute'))).toBe(false);
});
it('Person scope selection and Relationship scope use actual owned IDs and clear known-ID fields', async () => {
  const { controller } = await display();
  await fireEvent.changeText(screen.getByLabelText('已知 Memory ID'), jobId);
  await press(`记忆 Person 匿名对象 · ${person}`);
  expect(screen.getByLabelText('已知 Memory ID')).toHaveProp('value', '');
  await press(`记忆 Relationship ${rel}`);
  expect(controller.snapshot().scope).toEqual({ personId: person, relationshipId: rel });
});
it('server conflict is visible and does not display success', async () => {
  await display(async (request) =>
    request.url.endsWith('/undo')
      ? json({ error: { code: 'stale_undo', message: 'private' } }, 409)
      : undefined,
  );
  await press('检查最新 Undo 并准备确认');
  await press('确认撤销该最新操作');
  expect(screen.getByText('操作目标已发生变化，请重新检查。')).toBeOnTheScreen();
  expect(screen.queryByText('Action：undo · Status：undone')).toBeNull();
});
it('unknown deletion displays safe recovery, disables new destructive preparation and never invents receipt', async () => {
  await display(async (request) => {
    if (request.url.endsWith('/execute')) throw new TypeError('synthetic loss');
  });
  await press(`准备删除记忆 ${jobId}`);
  await press('确认执行服务器删除');
  expect(screen.getByText('Mutation 状态：操作结果未知')).toBeOnTheScreen();
  expect(screen.getByText('尚无已确认的服务器回执。')).toBeOnTheScreen();
  expect(screen.getByRole('button', { name: '安全重试原 Memory 操作' })).toBeEnabled();
  expect(screen.getByRole('button', { name: `准备删除记忆 ${jobId}` })).toBeDisabled();
  expect(screen.getByText(/重启后丢失原操作标识/)).toBeOnTheScreen();
});
it('revoke and regrant preserve pause as separate dimensions', async () => {
  await display();
  await press('撤销长期记忆授权');
  expect(screen.getByText('Consent：未授权')).toBeOnTheScreen();
  expect(screen.getByText('Pause：已暂停')).toBeOnTheScreen();
  await press('授权长期记忆');
  expect(screen.getByText('Consent：已授权')).toBeOnTheScreen();
  expect(screen.getByText('Pause：已暂停')).toBeOnTheScreen();
});
it('logout clears owner data, hidden ID input and retry eligibility', async () => {
  const { session } = await display();
  await fireEvent.changeText(screen.getByLabelText('已知 Mutation ID'), other);
  await act(async () => {
    await session.logout();
  });
  expect(screen.queryByText('匿名合成的明确事实')).toBeNull();
  expect(screen.getByLabelText('已知 Mutation ID')).toHaveProp('value', '');
  expect(screen.getByRole('button', { name: '安全重试原 Memory 操作' })).toBeDisabled();
});
it('read failure presents error and retry without filling a synthetic connected record', async () => {
  await display(async (request) =>
    request.url.endsWith('/control')
      ? json({ error: { code: 'persistence_failure' } }, 503)
      : undefined,
  );
  expect(screen.queryByText('匿名合成的明确事实')).toBeNull();
  expect(screen.getByRole('button', { name: '重新读取 Memory 权威状态' })).toBeEnabled();
  expect(screen.getByText(/服务器暂不可用/)).toBeOnTheScreen();
});
