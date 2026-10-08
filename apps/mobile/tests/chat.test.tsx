import { render, screen, fireEvent, act } from '@testing-library/react-native';
import { renderRouter } from 'expo-router/testing-library';
import { router } from 'expo-router';
import { app } from './testApp';
import ChatScreen from '../src/features/ChatScreen';
import { ChatMessageList, messageKey } from '../src/components/ChatMessageList';
import { ChatComposer } from '../src/components/ChatComposer';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import { DataSourceProvider } from '../src/data/DataSourceProvider';
import { demoSource } from '../src/data/demoSource';
import { appendLocalPreview, COMPOSER_LIMIT } from '../src/contracts/chat';
import type { AgentChatMessageViewModel } from '../src/contracts/chat';
import { runPreviews } from '../src/components/ChatRunPreview';

const input = () => screen.getByLabelText('本地预览消息输入');
const preview = () => screen.getByRole('button', { name: '添加到本地预览' });
describe('Chat local interaction and public presentation', () => {
  it('starts empty, truthfully labels Demo and has an accessible composer', async () => {
    await renderRouter(app, { initialUrl: '/chat' });
    expect(screen.getByText('还没有对话')).toBeOnTheScreen();
    expect(screen.getByText('本地演示 · Demo')).toBeOnTheScreen();
    expect(preview()).toBeDisabled();
    expect(input()).toHaveProp('multiline', true);
    expect(screen.getByRole('button', { name: '发送（尚未开放）' })).toBeDisabled();
    await fireEvent.changeText(input(), '  \n ');
    expect(preview()).toBeDisabled();
  });
  it('types, clears and appends only user bubbles in order without persistence', async () => {
    const navigation = renderRouter(app, { initialUrl: '/' });
    await navigation;
    await fireEvent.press(screen.getByRole('button', { name: '开始对话' }));
    await fireEvent.changeText(input(), '先清空');
    await fireEvent.press(screen.getByRole('button', { name: '清空' }));
    expect(input()).toHaveProp('value', '');
    const text = '合成问题🌱\n\n' + '很长的中文正文，应该自动换行。'.repeat(35);
    await fireEvent.changeText(input(), text);
    await fireEvent.press(preview());
    expect(screen.getByLabelText(`你：${text}`)).toBeOnTheScreen();
    expect(screen.getByText('仅在本地预览，尚未发送给 AI')).toBeOnTheScreen();
    expect(input()).toHaveProp('value', '');
    await fireEvent.changeText(input(), '第二条合成问题');
    await fireEvent.press(preview());
    expect(screen.getAllByLabelText(/^你：/).map((node) => node.props.children)).toEqual([
      text,
      '第二条合成问题',
    ]);
    expect(screen.queryAllByLabelText(/^助手（预置示例）：/)).toHaveLength(0);
    await fireEvent.press(screen.getByRole('button', { name: '返回上一级' }));
    await fireEvent.press(screen.getByRole('button', { name: '开始对话' }));
    expect(screen.queryByText('第二条合成问题')).toBeNull();
    expect(screen.getByText('还没有对话')).toBeOnTheScreen();
  });
  it('limits input even when onChangeText receives an oversized value', async () => {
    await renderRouter(app, { initialUrl: '/chat' });
    await fireEvent.changeText(input(), '合'.repeat(COMPOSER_LIMIT + 50));
    expect(input()).toHaveProp('value', '合'.repeat(COMPOSER_LIMIT));
    expect(input()).toHaveProp('maxLength', COMPOSER_LIMIT);
    expect(
      screen.getByText(`Demo · ${COMPOSER_LIMIT}/${COMPOSER_LIMIT} · 不发送、不保存`),
    ).toBeOnTheScreen();
  });
  it('loads assistant content only through the explicit synthetic example action', async () => {
    await renderRouter(app, { initialUrl: '/chat' });
    expect(screen.queryByText(/预置示例：可以先/)).toBeNull();
    await fireEvent.press(screen.getByRole('button', { name: '替换为合成对话示例' }));
    expect(screen.getAllByLabelText(/^你：|^助手（预置示例）：/)).toHaveLength(2);
    expect(screen.getByText(/助手（预置示例） · Demo · 合成示例/)).toBeOnTheScreen();
    expect(screen.getByLabelText(/助手（预置示例）：预置示例/)).toBeOnTheScreen();
    await fireEvent.changeText(input(), '合成新增问题');
    await fireEvent.press(preview());
    expect(screen.getAllByLabelText(/^你：/)).toHaveLength(2);
    expect(screen.getAllByLabelText(/^助手（预置示例）：/)).toHaveLength(1);
  });
  it.each(runPreviews)(
    'holds $state only as a user-controlled Demo preview',
    async ({ state, label, description }) => {
      await renderRouter(app, { initialUrl: '/chat' });
      await fireEvent.press(screen.getByRole('button', { name: '演示状态预览' }));
      await fireEvent.press(screen.getByRole('button', { name: label }));
      expect(screen.getByRole('button', { name: label })).toBeSelected();
      expect(screen.getByText(`Demo · ${description}`)).toBeOnTheScreen();
      const blocked = ['starting', 'progressing', 'pending_confirmation'].includes(state);
      expect(input()).toHaveProp('editable', !blocked);
      if (state === 'starting') expect(screen.getByText('演示加载中')).toBeOnTheScreen();
      if (state === 'failed') {
        expect(screen.getByRole('alert')).toBeOnTheScreen();
        await fireEvent.press(screen.getByRole('button', { name: '重试' }));
        expect(screen.queryByRole('alert')).toBeNull();
        expect(screen.getByRole('button', { name: '空状态' })).toBeSelected();
      }
      if (state === 'pending_confirmation')
        expect(screen.getByRole('button', { name: '确认执行（尚未开放）' })).toBeDisabled();
      if (state === 'completed') {
        expect(screen.getByText(/事实：合成场景/)).toBeOnTheScreen();
        expect(screen.getByText(/来源：预置合成场景/)).toBeOnTheScreen();
        expect(screen.getByText(/推测：双方可能/)).toBeOnTheScreen();
        expect(screen.getByText(/也可能只是讨论/)).toBeOnTheScreen();
        expect(screen.getByText(/尚不确定：对方/)).toBeOnTheScreen();
        expect(screen.queryAllByTestId(/^message-/)).toHaveLength(0);
      }
    },
  );
  it('rejects disabled composer actions', async () => {
    const onChange = jest.fn();
    const onPreview = jest.fn();
    await render(
      <ThemeProvider>
        <ChatComposer
          state={{ text: '合成输入', disabled: true }}
          onChange={onChange}
          onPreview={onPreview}
        />
      </ThemeProvider>,
    );
    expect(input()).toBeDisabled();
    await fireEvent.press(preview());
    await fireEvent.press(screen.getByRole('button', { name: '清空' }));
    expect(onChange).not.toHaveBeenCalled();
    expect(onPreview).not.toHaveBeenCalled();
  });
  it('consumes an injected Chat ViewModel and resets when relationship scope changes', async () => {
    const source = {
      ...demoSource,
      readChat: (id: string | null) => ({
        ...demoSource.readChat(id),
        thread: { ...demoSource.readChat(id).thread, title: `注入范围 ${id}` },
      }),
    };
    const InjectedChat = () => (
      <DataSourceProvider source={source}>
        <ChatScreen />
      </DataSourceProvider>
    );
    const navigation = renderRouter(
      { ...app, chat: InjectedChat },
      { initialUrl: '/chat?relationshipId=demo-a' },
    );
    await navigation;
    expect(screen.getByText('注入范围 demo-a')).toBeOnTheScreen();
    await fireEvent.changeText(input(), '范围 A 合成输入');
    await fireEvent.press(preview());
    await act(() => router.setParams({ relationshipId: 'demo-b' }));
    expect(screen.getByText('注入范围 demo-b')).toBeOnTheScreen();
    expect(screen.queryByText('范围 A 合成输入')).toBeNull();
    expect(input()).toHaveProp('value', '');
  });
  it('does not request or log local input', async () => {
    const network = jest.spyOn(global, 'fetch');
    const logging = jest.spyOn(console, 'log');
    try {
      await renderRouter(app, { initialUrl: '/chat' });
      await fireEvent.changeText(input(), '纯合成隐私测试文本');
      await fireEvent.press(preview());
      expect(network).not.toHaveBeenCalled();
      expect(logging.mock.calls.flat().join(' ')).not.toContain('纯合成隐私测试文本');
    } finally {
      network.mockRestore();
      logging.mockRestore();
    }
  });
  it('shows unsupported relationship scope as unknown without falling back to A', async () => {
    await renderRouter(app, { initialUrl: '/chat?relationshipId=unknown-demo' });
    expect(screen.getByText('关系不可用')).toBeOnTheScreen();
    expect(screen.queryByText('关系 A · 同学')).toBeNull();
    expect(screen.queryAllByTestId(/^message-/)).toHaveLength(0);
  });
});

describe('virtualized message list', () => {
  it('keeps 1,000 equal-time messages and appends in linear order with bounded mounting', async () => {
    const messages: AgentChatMessageViewModel[] = Array.from({ length: 1000 }, (_, i) => ({
      id: `synthetic-${i}`,
      role: i % 2 ? 'assistant' : 'user',
      text: `匿名合成消息 ${i} 🌱\n第二段`,
      timeLabel: '演示时间 · 10:00',
      source: 'synthetic-demo',
    }));
    expect(new Set(messages.map(messageKey)).size).toBe(1000);
    const result = await render(
      <ThemeProvider>
        <ChatMessageList messages={messages} />
      </ThemeProvider>,
    );
    expect(screen.getByLabelText('你：匿名合成消息 0 🌱\n第二段')).toBeOnTheScreen();
    expect(screen.queryByTestId('message-synthetic-999')).toBeNull();
    expect(screen.queryAllByTestId(/^message-/).length).toBeLessThanOrEqual(12);
    const next = appendLocalPreview(messages, {
      id: 'local-1',
      role: 'user',
      text: '最后一条',
      timeLabel: '演示时间 · 10:00',
      source: 'local-preview',
    });
    await result.rerender(
      <ThemeProvider>
        <ChatMessageList messages={next} />
      </ThemeProvider>,
    );
    expect(next).toHaveLength(1001);
    expect(next.map(messageKey)).toEqual([...messages.map(messageKey), 'local-1']);
    expect(screen.queryAllByTestId(/^message-/).length).toBeLessThanOrEqual(12);
    expect(messages).toHaveLength(1000);
    expect(next[0]).toBe(messages[0]);
  });
  it('returns fully isolated nested fixture reads', () => {
    const first = demoSource.readChat(null);
    const second = demoSource.readChat(null);
    expect(first).toEqual(second);
    expect(first.thread.messages).not.toBe(second.thread.messages);
    expect(first.thread.messages[0]).not.toBe(second.thread.messages[0]);
    expect(first.fiu).not.toBe(second.fiu);
  });
});
// A RelationshipMessage sender or internal tool role cannot compile here.
// @ts-expect-error tool is not a public chat role.
const internalRole: AgentChatMessageViewModel['role'] = 'tool';
// @ts-expect-error imported speaker is not an Agent conversation role.
const importedRole: AgentChatMessageViewModel['role'] = 'person';
void internalRole;
void importedRole;
