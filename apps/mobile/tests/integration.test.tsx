import { act, fireEvent, screen } from '@testing-library/react-native';
import { renderRouter } from 'expo-router/testing-library';
import { router } from 'expo-router';
import { app } from './testApp';
import { demoSource } from '../src/data/demoSource';
import { DataSourceProvider } from '../src/data/DataSourceProvider';
import HomeScreen from '../src/features/HomeScreen';
import { canAdvanceImport, initialImport } from '../src/contracts/import';
import type { ShellDataSource } from '../src/contracts/shell';

const press = async (name: string) => fireEvent.press(screen.getByRole('button', { name }));
const noRelationships: ShellDataSource = {
  ...demoSource,
  readRelationships: () => [],
  readHistory: () => ({ agent: [], relationship: [] }),
  readImport: () => demoSource.readImport('empty'),
  readSettings: () => ({ ...demoSource.readSettings(), records: [], undo: null }),
};

describe('Phase 7D integration and recovery', () => {
  it.each(['/chat', '/relationship', '/import', '/history'])(
    'fails closed with an empty relationship source on %s',
    async (path) => {
      const Route = app[path.slice(1) as 'chat' | 'relationship' | 'import' | 'history'];
      const Injected = () => (
        <DataSourceProvider source={noRelationships}>
          <Route />
        </DataSourceProvider>
      );
      await renderRouter(
        { ...app, [path.slice(1)]: Injected },
        { initialUrl: `${path}?relationshipId=demo-b` },
      );
      expect(screen.getByRole('header', { name: '关系不可用' })).toBeOnTheScreen();
      expect(screen.queryByText('显示昵称：对象 A（合成）')).toBeNull();
      expect(screen.queryByTestId('message-local-1')).toBeNull();
      await press('返回上一级');
      expect(screen.getByText('狗头军师')).toBeOnTheScreen();
    },
  );
  it('keeps empty Memory inspect/undo usable without fabricating a target', async () => {
    const Injected = () => (
      <DataSourceProvider source={noRelationships}>
        <app.settings />
      </DataSourceProvider>
    );
    await renderRouter({ ...app, settings: Injected }, { initialUrl: '/settings' });
    await press('查看记忆样例（Demo）');
    expect(screen.getByText('没有记忆样例')).toBeOnTheScreen();
    await press('查看撤销预览（Demo）');
    expect(screen.getByText('没有可撤销的样例')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: '正式撤销（尚未开放）' })).toBeDisabled();
    await press('预览删除全部记忆（Demo）');
    expect(screen.getByText('影响数量：0 条匿名样例')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: '正式删除（尚未开放）' })).toBeDisabled();
  });
  it.each(['loading', 'error'] as const)('Home remains visible for source %s', async (status) => {
    const Injected = () => (
      <DataSourceProvider
        source={{
          ...demoSource,
          readSurface: () =>
            status === 'loading' ? { status } : { status, message: '合成读取错误' },
        }}
      >
        <HomeScreen />
      </DataSourceProvider>
    );
    await renderRouter({ ...app, index: Injected });
    expect(screen.getByText('狗头军师')).toBeOnTheScreen();
    expect(screen.getByText('本地演示 · Demo')).toBeOnTheScreen();
    if (status === 'error') {
      expect(screen.getByRole('alert')).toBeOnTheScreen();
      expect(screen.getByRole('button', { name: '重试' })).not.toBeDisabled();
    } else expect(screen.getByText('演示加载中')).toBeOnTheScreen();
  });
  it.each(['/chat', '/relationship', '/import', '/history'])(
    'rejects a duplicated identical route scope on %s',
    async (path) => {
      await renderRouter(app, {
        initialUrl: `${path}?relationshipId=demo-b&relationshipId=demo-b`,
      });
      expect(screen.getByRole('header', { name: '关系不可用' })).toBeOnTheScreen();
    },
  );
  it('clears Chat messages, draft and pending state when A changes to B', async () => {
    await renderRouter(app, { initialUrl: '/chat?relationshipId=demo-a' });
    await fireEvent.changeText(screen.getByLabelText('本地预览消息输入'), 'A 合成预览');
    await press('添加到本地预览');
    await fireEvent.changeText(screen.getByLabelText('本地预览消息输入'), 'A 未提交草稿');
    await press('演示状态预览');
    await press('待确认状态');
    await act(() => router.setParams({ relationshipId: 'demo-b' }));
    expect(screen.getByLabelText('本地预览消息输入')).toHaveDisplayValue('');
    expect(screen.queryByTestId('message-local-1')).toBeNull();
    expect(screen.queryByRole('button', { name: '确认执行（尚未开放）' })).toBeNull();
    expect(screen.getByText('关系 B · 待补充')).toBeOnTheScreen();
  });
  it('cannot advance past incomplete identity, missing Person, or unconfirmed relationship', () => {
    const model = demoSource.readImport('pair');
    const profiles = demoSource.readRelationships();
    const source = { ...initialImport('demo-b'), loaded: true };
    expect(canAdvanceImport(model, source, profiles)).toBe(true);
    expect(canAdvanceImport(model, { ...source, step: 'speakers' }, profiles)).toBe(false);
    const bindings = {
      'speaker-0': { kind: 'self' as const },
      'speaker-1': { kind: 'person' as const, personId: null },
      'speaker-2': { kind: 'ignore' as const },
    };
    expect(canAdvanceImport(model, { ...source, step: 'speakers', bindings }, profiles)).toBe(
      false,
    );
    const completeBindings = {
      ...bindings,
      'speaker-1': { kind: 'person' as const, personId: 'person-b' },
    };
    expect(
      canAdvanceImport(
        model,
        { ...source, step: 'speakers', bindings: completeBindings },
        profiles,
      ),
    ).toBe(true);
    expect(canAdvanceImport(model, { ...source, step: 'relationship', bindings }, profiles)).toBe(
      false,
    );
    expect(
      canAdvanceImport(
        model,
        {
          ...source,
          step: 'readiness',
          bindings,
          relationship: { relationshipId: 'missing', confirmed: true },
        },
        profiles,
      ),
    ).toBe(false);
  });
});
