import { screen, fireEvent } from '@testing-library/react-native';
import { renderRouter } from 'expo-router/testing-library';
import { app } from './testApp';
import RelationshipScreen from '../src/features/RelationshipScreen';
import { DataSourceProvider } from '../src/data/DataSourceProvider';
import { demoSource } from '../src/data/demoSource';

describe('Relationship public profile', () => {
  it('separates person and relationship and shows known/missing metadata', async () => {
    await renderRouter(app, { initialUrl: '/relationship' });
    expect(screen.getByText('关系 A · 同学')).toBeOnTheScreen();
    expect(screen.getByText('对象资料 · Person')).toBeOnTheScreen();
    expect(screen.getByText('显示昵称：对象 A（合成）')).toBeOnTheScreen();
    expect(screen.getByText('关系类型：同学')).toBeOnTheScreen();
    expect(screen.getByText('合成背景：一起参加过学习活动。')).toBeOnTheScreen();
    expect(screen.getByText('双方对关系的期待')).toBeOnTheScreen();
    expect(screen.getByText('未提供分析结果；没有自动分析任何聊天记录。')).toBeOnTheScreen();
    expect(screen.queryByText('还没有关系资料')).toBeNull();
  });
  it('selects B, removes all A fields, preserves missing values and switches back', async () => {
    await renderRouter(app, { initialUrl: '/relationship' });
    await fireEvent.press(screen.getByRole('button', { name: '选择关系 B · 待补充' }));
    expect(screen.getByRole('button', { name: '选择关系 B · 待补充' })).toBeSelected();
    expect(screen.getByText('关系 B · 待补充')).toBeOnTheScreen();
    expect(screen.getByText('显示昵称：未提供')).toBeOnTheScreen();
    expect(screen.getByText('关系类型：未提供')).toBeOnTheScreen();
    expect(screen.getByText('最近互动：未提供')).toBeOnTheScreen();
    expect(screen.getByText('未提供历史聊天或摘要。')).toBeOnTheScreen();
    expect(screen.queryByText('显示昵称：对象 A（合成）')).toBeNull();
    expect(screen.queryByText('合成背景：一起参加过学习活动。')).toBeNull();
    expect(screen.queryByText(/演示时间 · 周一/)).toBeNull();
    expect(screen.queryByText(/合成摘要：一次/)).toBeNull();
    await fireEvent.press(screen.getByRole('button', { name: '选择关系 A · 同学' }));
    expect(screen.getByText('显示昵称：对象 A（合成）')).toBeOnTheScreen();
    expect(screen.queryByText('显示昵称：未提供')).toBeNull();
  });
  it.each([
    ['前往本地对话预览', '/chat', '关系 B · 待补充'],
    [
      '前往导入与分析（尚未接入）',
      '/import',
      '导入入口和分析展示区已预留。当前不会读取、上传或分析任何聊天文件。',
    ],
    ['查看关系历史（尚未接入）', '/history', '还没有历史记录'],
  ])(
    'navigates using %s and restores the selected relationship on back',
    async (label, path, text) => {
      const navigation = renderRouter(app, { initialUrl: '/relationship' });
      await navigation;
      await fireEvent.press(screen.getByRole('button', { name: '选择关系 B · 待补充' }));
      await fireEvent.press(screen.getByRole('button', { name: label }));
      expect(navigation.getPathname()).toBe(path);
      expect(screen.getByText(text)).toBeOnTheScreen();
      await fireEvent.press(screen.getByRole('button', { name: '返回上一级' }));
      expect(navigation.getPathname()).toBe('/relationship');
      expect(screen.getByRole('button', { name: '选择关系 B · 待补充' })).toBeSelected();
    },
  );
  it('renders an injected empty source without invented profiles', async () => {
    const EmptyProfile = () => (
      <DataSourceProvider source={{ ...demoSource, readRelationships: () => [] }}>
        <RelationshipScreen />
      </DataSourceProvider>
    );
    await renderRouter({ ...app, relationship: EmptyProfile }, { initialUrl: '/relationship' });
    expect(screen.getByText('还没有关系资料')).toBeOnTheScreen();
    expect(screen.queryByRole('button', { name: '前往本地对话预览' })).toBeNull();
    expect(screen.queryByText('显示昵称：对象 A（合成）')).toBeNull();
  });
  it('isolates nested profile fixtures and keeps person IDs distinct from relationship IDs', () => {
    const first = demoSource.readRelationships();
    const second = demoSource.readRelationships();
    expect(first).toEqual(second);
    expect(first).not.toBe(second);
    expect(first[0]?.person).not.toBe(second[0]?.person);
    expect(first[0]?.known).not.toBe(second[0]?.known);
    expect(first[0]?.missing).not.toBe(second[0]?.missing);
    expect(first[0]?.person.id).not.toBe(first[0]?.id);
    expect(first.every((p) => p.source === 'demo' && p.analysisSummary === null)).toBe(true);
  });
});
