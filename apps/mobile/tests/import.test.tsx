import { act, fireEvent, screen } from '@testing-library/react-native';
import { renderRouter } from 'expo-router/testing-library';
import { router } from 'expo-router';
import { app } from './testApp';
import { demoSource } from '../src/data/demoSource';
import { DataSourceProvider } from '../src/data/DataSourceProvider';
import ImportScreen from '../src/features/ImportScreen';
import {
  initialImport,
  moveImport,
  previewReadiness,
  type ImportPresentationState,
} from '../src/contracts/import';

const press = async (name: string) => fireEvent.press(screen.getByRole('button', { name }));
export async function bindPair(personId = 'person-b') {
  await press('我 → self');
  await press('匿名同学🌱 → person');
  await press(`匿名同学🌱 → ${personId}`);
  await press('系统通知🔔 → system');
}
describe('Import local wizard', () => {
  it('requires explicit identities and relationship confirmation, preserves labels and shows only precheck completion', async () => {
    const nav = renderRouter(app, { initialUrl: '/import?relationshipId=demo-b' });
    await nav;
    expect(screen.getByRole('button', { name: '下一步' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '选择文件（尚未开放）' })).toBeDisabled();
    await press('体验导入流程（演示数据）');
    expect(screen.getByText('消息：12 · 说话人：3')).toBeOnTheScreen();
    expect(screen.getByText('来源时区：Asia/Shanghai')).toBeOnTheScreen();
    expect(screen.getByText(/起始：2026-09-01/)).toBeOnTheScreen();
    expect(screen.getByText(/示例警告/)).toBeOnTheScreen();
    await press('下一步');
    expect(screen.getAllByText('绑定：unbound')).toHaveLength(3);
    expect(screen.getByText('匿名同学🌱')).toBeOnTheScreen();
    expect(screen.getByText('合成导出标签 1 · 5 条消息')).toBeOnTheScreen();
    await press('下一步');
    await press('下一步');
    expect(screen.getByText('存在未处理说话人')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: '下一步' })).toBeDisabled();
    await press('返回修改说话人');
    await bindPair();
    await press('下一步');
    await press('确认关系绑定（Demo）');
    await press('下一步');
    expect(screen.getByText('演示预检通过')).toBeOnTheScreen();
    await press('上一步');
    expect(screen.getByText('3 / 5 · 关系绑定')).toBeOnTheScreen();
    await press('下一步');
    await press('下一步');
    expect(screen.getByText('演示预检已完成，真实导入将在连接服务器后启用。')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: '正式导入（尚未开放）' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '运行 AI 分析（尚未开放）' })).toBeDisabled();
    await press('查看关系历史 Demo');
    expect(nav.getPathname()).toBe('/history');
    expect(nav.getSearchParams()).toEqual({ relationshipId: 'demo-b' });
    await press('返回上一级');
    await press('进入 Chat 本地预览');
    expect(nav.getSearchParams()).toEqual({ relationshipId: 'demo-b' });
  });
  it('blocks mismatched person and resets binding on a changed relationship', async () => {
    await renderRouter(app, { initialUrl: '/import?relationshipId=demo-b' });
    await press('体验导入流程（演示数据）');
    await press('下一步');
    await bindPair('person-a');
    await press('下一步');
    await press('确认关系绑定（Demo）');
    await press('下一步');
    expect(screen.getByText('speaker/relationship 不兼容')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: '下一步' })).toBeDisabled();
    await press('返回修改关系');
    await press('选择关系 A · 同学');
    expect(screen.getByText('2 / 5 · 说话人绑定')).toBeOnTheScreen();
    expect(screen.getAllByText('绑定：unbound')).toHaveLength(3);
    await bindPair('person-a');
    await press('下一步');
    await press('确认关系绑定（Demo）');
    await press('下一步');
    expect(screen.getByText('演示预检通过')).toBeOnTheScreen();
  });
  it('rejects a third human and never merges the extra participant', async () => {
    await renderRouter(app, { initialUrl: '/import?relationshipId=demo-b' });
    await press('体验群聊样例（演示数据）');
    await press('下一步');
    await bindPair();
    await press('匿名参与者🌿 → person');
    await press('匿名参与者🌿 → person-a');
    await press('下一步');
    await press('确认关系绑定（Demo）');
    await press('下一步');
    expect(screen.getByText('当前版本的一对一关系导入不支持多人群聊')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: '下一步' })).toBeDisabled();
  });
  it.each(['missing', 'demo-a&relationshipId=demo-b'])(
    'fails closed for invalid scope %s',
    async (scope) => {
      await renderRouter(app, { initialUrl: `/import?relationshipId=${scope}` });
      expect(screen.getByText('关系不可用')).toBeOnTheScreen();
      expect(screen.queryByRole('button', { name: '体验导入流程（演示数据）' })).toBeNull();
    },
  );
  it('resets Demo, empty source and changed route scope', async () => {
    await renderRouter(app, { initialUrl: '/import?relationshipId=demo-a' });
    await press('体验空来源（演示数据）');
    expect(screen.getByRole('button', { name: '下一步' })).toBeDisabled();
    await press('体验导入流程（演示数据）');
    await press('下一步');
    await bindPair('person-a');
    await act(() => router.setParams({ relationshipId: 'demo-b' }));
    expect(screen.getByText('1 / 5 · 演示来源')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: '下一步' })).toBeDisabled();
    await press('体验导入流程（演示数据）');
    await press('下一步');
    expect(screen.getAllByText('绑定：unbound')).toHaveLength(3);
    await press('重置 Demo');
    expect(screen.getByRole('button', { name: '下一步' })).toBeDisabled();
  });
  it('consumes a substituted summary, not an embedded fixture', async () => {
    const Injected = () => (
      <DataSourceProvider
        source={{
          ...demoSource,
          readImport: (kind) => ({
            ...demoSource.readImport(kind),
            summary: { ...demoSource.readImport(kind).summary, sourceTimezone: 'UTC' },
          }),
        }}
      >
        <ImportScreen />
      </DataSourceProvider>
    );
    await renderRouter({ ...app, import: Injected }, { initialUrl: '/import' });
    await press('体验导入流程（演示数据）');
    expect(screen.getByText('来源时区：UTC')).toBeOnTheScreen();
  });
  it('drops source/bindings on unmount and recreation of the wizard', async () => {
    await renderRouter(app, { initialUrl: '/relationship?relationshipId=demo-b' });
    await press('前往导入与分析 Demo');
    await press('体验导入流程（演示数据）');
    await press('下一步');
    await bindPair();
    await press('返回上一级');
    await press('前往导入与分析 Demo');
    expect(screen.getByRole('button', { name: '下一步' })).toBeDisabled();
    await press('体验导入流程（演示数据）');
    await press('下一步');
    expect(screen.getAllByText('绑定：unbound')).toHaveLength(3);
  });
});
describe('readiness contract', () => {
  const model = demoSource.readImport('pair');
  const profiles = demoSource.readRelationships();
  const ready: ImportPresentationState = {
    ...initialImport('demo-b'),
    loaded: true,
    step: 'readiness',
    bindings: {
      'speaker-0': { kind: 'self' },
      'speaker-1': { kind: 'person', personId: 'person-b' },
      'speaker-2': { kind: 'system' },
    },
    relationship: { relationshipId: 'demo-b', confirmed: true },
  };
  it('requires exactly one self and Person, unbound blocks, no relation blocks', () => {
    expect(previewReadiness(model, ready, profiles)).toMatchObject({
      ready: true,
      authority: 'local-preview',
    });
    for (const bad of [
      initialImport(null),
      { ...ready, bindings: {} },
      { ...ready, relationship: { relationshipId: 'missing', confirmed: true } },
      { ...ready, bindings: { ...ready.bindings, 'speaker-2': { kind: 'self' as const } } },
    ]) {
      expect(previewReadiness(model, bad, profiles).ready).toBe(false);
    }
    expect(moveImport({ ...ready, loaded: false }, 'next', false).step).toBe('readiness');
    expect(moveImport(ready, 'next', false).step).toBe('readiness');
    expect(moveImport(ready, 'next', true).step).toBe('result');
  });
  it('isolates summary/inventory and never supplies default bindings', () => {
    const other = demoSource.readImport('pair');
    expect(model).toEqual(other);
    expect(model.summary).not.toBe(other.summary);
    expect(model.speakers[0]).not.toBe(other.speakers[0]);
    expect(initialImport('demo-a').bindings).toEqual({});
  });
});
