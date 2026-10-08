import { act, fireEvent, render, screen } from '@testing-library/react-native';
import { renderRouter } from 'expo-router/testing-library';
import { router } from 'expo-router';
import { Text } from 'react-native';
import { app } from './testApp';
import { demoSource } from '../src/data/demoSource';
import { DataSourceProvider } from '../src/data/DataSourceProvider';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import HistoryScreen from '../src/features/HistoryScreen';
import { HistoryList } from '../src/components/HistoryList';
import {
  filterHistory,
  historyKey,
  sortHistory,
  type AgentHistoryItemViewModel,
  type RelationshipHistoryItemViewModel,
} from '../src/contracts/history';

const press = async (name: string) => fireEvent.press(screen.getByRole('button', { name }));
describe('History domains and scope', () => {
  it('renders self/person/system with raw labels and switches to isolated user/assistant examples', async () => {
    await renderRouter(app, { initialUrl: '/history?relationshipId=demo-b' });
    await press('加载历史样例（Demo）');
    expect(screen.getAllByText('self · 我 · Demo · 匿名合成').length).toBeGreaterThan(0);
    expect(screen.getAllByText('person · 匿名同学🌱 · Demo · 匿名合成').length).toBeGreaterThan(0);
    expect(screen.getAllByText('system · 系统通知🔔 · Demo · 匿名合成').length).toBeGreaterThan(0);
    expect(screen.queryByText(/AI 助手示例 · assistant · Demo/)).toBeNull();
    expect(screen.getByText(/当前窗口：30 \/ 1020/)).toBeOnTheScreen();
    await press('AI 对话');
    expect(screen.getByText('用户 · user · Demo · 匿名合成')).toBeOnTheScreen();
    expect(screen.getByText('AI 助手示例 · assistant · Demo · 匿名合成')).toBeOnTheScreen();
    expect(screen.queryByText(/person · 匿名同学/)).toBeNull();
    expect(screen.getByRole('button', { name: '查看更多（Demo）' })).toBeDisabled();
  });
  it('increments a bounded page without duplicates, resets on kind and relationship change', async () => {
    await renderRouter(app, { initialUrl: '/history?relationshipId=demo-a' });
    await press('加载历史样例（Demo）');
    const firstKeys = screen.queryAllByTestId(/^history-row-/).map((row) => row.props.testID);
    expect(screen.getByText(/当前窗口：30 \/ 1020/)).toBeOnTheScreen();
    await press('查看更多（Demo）');
    expect(screen.getByText(/当前窗口：60 \/ 1020/)).toBeOnTheScreen();
    expect(screen.queryAllByTestId(/^history-row-/).map((row) => row.props.testID)).toEqual(
      firstKeys,
    );
    await press('AI 对话');
    await press('关系聊天');
    expect(screen.getByText(/当前窗口：30 \/ 1020/)).toBeOnTheScreen();
    await press('选择关系 B · 待补充');
    expect(screen.getByText(/当前窗口：0 \/ 0/)).toBeOnTheScreen();
    await press('加载历史样例（Demo）');
    expect(screen.getByText(/^B 合成历史 0/)).toBeOnTheScreen();
    expect(screen.queryByText(/^A 合成历史/)).toBeNull();
    for (let page = 2; page <= 34; page++) {
      await press('查看更多（Demo）');
      expect(screen.getByText(new RegExp(`当前窗口：${page * 30} / 1020`))).toBeOnTheScreen();
    }
    expect(screen.getByRole('button', { name: '查看更多（Demo）' })).toBeDisabled();
    expect(screen.queryAllByTestId(/^history-row-/).length).toBeLessThanOrEqual(12);
    await press('重置历史 Demo');
    expect(screen.getByText('还没有历史记录')).toBeOnTheScreen();
  });
  it.each([
    '/history?relationshipId=missing',
    '/chat?relationshipId=missing',
    '/relationship?relationshipId=missing',
  ])('handles an unknown scope at %s', async (path) => {
    await renderRouter(app, { initialUrl: path });
    expect(screen.getByRole('header', { name: '关系不可用' })).toBeOnTheScreen();
    expect(screen.queryByText(/^A 合成历史/)).toBeNull();
    expect(screen.queryByText(/^B 合成历史/)).toBeNull();
  });
  it('requires a relationship for external history and allows a general AI example', async () => {
    await renderRouter(app, { initialUrl: '/history' });
    expect(screen.getByRole('button', { name: '加载历史样例（Demo）' })).toBeDisabled();
    await press('AI 对话');
    await press('加载历史样例（Demo）');
    expect(screen.getByText('用户 · user · Demo · 匿名合成')).toBeOnTheScreen();
  });
  it('keeps local Chat input out of history and clears demo on route removal/recreation', async () => {
    await renderRouter(app, { initialUrl: '/relationship' });
    await press('前往本地对话预览');
    await fireEvent.changeText(screen.getByLabelText('本地预览消息输入'), '唯一匿名本地消息');
    await press('添加到本地预览');
    await press('返回上一级');
    await press('查看关系历史 Demo');
    await press('AI 对话');
    await press('加载历史样例（Demo）');
    expect(screen.queryByText('唯一匿名本地消息')).toBeNull();
    await press('返回上一级');
    await press('查看关系历史 Demo');
    expect(screen.getByText('还没有历史记录')).toBeOnTheScreen();
  });
  it('substitutes an empty DataSource and resets pagination on route params', async () => {
    const Injected = () => (
      <DataSourceProvider
        source={{ ...demoSource, readHistory: () => ({ agent: [], relationship: [] }) }}
      >
        <HistoryScreen />
      </DataSourceProvider>
    );
    await renderRouter(
      { ...app, history: Injected },
      { initialUrl: '/history?relationshipId=demo-a' },
    );
    await press('加载历史样例（Demo）');
    expect(screen.getByText(/当前窗口：0 \/ 0/)).toBeOnTheScreen();
    await act(() => router.setParams({ relationshipId: 'demo-b' }));
    expect(screen.getByText('还没有历史记录')).toBeOnTheScreen();
  });
});
describe('large deterministic history', () => {
  it('keeps every occurrence, stable equal-time order across datasets, and bounded mounting', async () => {
    const model = demoSource.readHistory();
    const items = filterHistory(model, { relationshipId: 'demo-b', kind: 'relationship' });
    expect(items).toHaveLength(1020);
    expect(new Set(items.map(historyKey)).size).toBe(1020);
    expect(items.every((m) => m.relationshipId === 'demo-b')).toBe(true);
    expect(sortHistory([...items].reverse()).map(historyKey)).toEqual(items.map(historyKey));
    const pages = Array.from({ length: 34 }, (_, i) => items.slice(i * 30, (i + 1) * 30)).flat();
    expect(pages.map(historyKey)).toEqual(items.map(historyKey));
    await render(
      <ThemeProvider>
        <HistoryList items={items} header={<Text>匿名列表</Text>} />
      </ThemeProvider>,
    );
    expect(screen.queryAllByTestId(/^history-row-/).length).toBeLessThanOrEqual(12);
    expect(screen.queryByTestId('history-row-demo-b-1019')).toBeNull();
  });
  it('orders equal timestamps using dataset then source index, never content dedup', () => {
    const first = demoSource.readHistory().relationship[0]!;
    const timestamp = first.timestamp;
    const messages = [
      { ...first, id: 'b', datasetId: 'source-b', sourceIndex: 1, timestamp },
      { ...first, id: 'a2', datasetId: 'source-a', sourceIndex: 2, timestamp },
      { ...first, id: 'a1', datasetId: 'source-a', sourceIndex: 1, timestamp },
    ];
    expect(sortHistory(messages).map((m) => m.id)).toEqual(['a1', 'a2', 'b']);
    expect(sortHistory(messages)).toHaveLength(3);
    expect(
      sortHistory([
        { ...messages[0]!, timestamp: '2026-09-01T09:00:00Z' },
        { ...messages[1]!, timestamp: '2026-09-01T10:00:00+08:00' },
      ]).map((m) => m.id),
    ).toEqual(['a2', 'b']);
  });
  it('allocates isolated fixture reads', () => {
    const first = demoSource.readHistory();
    const second = demoSource.readHistory();
    expect(first).toEqual(second);
    expect(first.relationship[0]).not.toBe(second.relationship[0]);
    expect(first.agent[0]).not.toBe(second.agent[0]);
  });
});
// Strict compile-time domain/role rejection.
// @ts-expect-error imported people are not AI assistants.
const agentRole: AgentHistoryItemViewModel['role'] = 'person';
// @ts-expect-error AI assistant is not an external chat sender.
const externalRole: RelationshipHistoryItemViewModel['sender'] = 'assistant';
// @ts-expect-error external history cannot be assigned to Agent history.
const mixed: AgentHistoryItemViewModel = demoSource.readHistory().relationship[0]!;
void agentRole;
void externalRole;
void mixed;
