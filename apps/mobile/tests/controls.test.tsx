import { act, fireEvent, screen } from '@testing-library/react-native';
import { renderRouter } from 'expo-router/testing-library';
import { router } from 'expo-router';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { app } from './testApp';

const press = async (name: string) => fireEvent.press(screen.getByRole('button', { name }));
describe('7C shared boundaries', () => {
  it('carries B through Relationship → Import → History → Chat and back without A leftovers', async () => {
    const nav = renderRouter(app, { initialUrl: '/relationship' });
    await nav;
    await press('选择关系 B · 待补充');
    await press('查看关系历史 Demo');
    expect(nav.getSearchParams()).toEqual({ relationshipId: 'demo-b' });
    await press('加载历史样例（Demo）');
    expect(screen.queryByText(/^A 合成历史/)).toBeNull();
    await press('前往导入 Demo');
    expect(nav.getSearchParams()).toEqual({ relationshipId: 'demo-b' });
    await press('返回上一级');
    await press('进入 Chat 本地预览');
    expect(nav.getSearchParams()).toEqual({ relationshipId: 'demo-b' });
    expect(screen.getByText('关系 B · 待补充')).toBeOnTheScreen();
    await press('返回上一级');
    await press('返回上一级');
    expect(screen.getByRole('button', { name: '选择关系 B · 待补充' })).toBeSelected();
    await press('选择关系 A · 同学');
    await press('前往导入与分析 Demo');
    expect(nav.getSearchParams()).toEqual({ relationshipId: 'demo-a' });
    expect(screen.getByRole('button', { name: '下一步' })).toBeDisabled();
  });
  it('replaces the Relationship selection when the explicit route scope changes', async () => {
    await renderRouter(app, { initialUrl: '/relationship?relationshipId=demo-a' });
    await press('选择关系 A · 同学');
    await act(() => router.setParams({ relationshipId: 'demo-b' }));
    expect(screen.getByText('显示昵称：未提供')).toBeOnTheScreen();
    expect(screen.queryByText('显示昵称：对象 A（合成）')).toBeNull();
  });
  it.each(['/import', '/history', '/settings'])(
    'has labeled controls, theme compatibility, loading/error/retry on %s',
    async (path) => {
      await renderRouter(app, { initialUrl: path });
      expect(screen.getByRole('button', { name: '返回上一级' })).not.toBeDisabled();
      expect(screen.getByText('本地演示 · Demo')).toBeOnTheScreen();
      await press('加载状态');
      expect(screen.getByText('演示加载中')).toBeOnTheScreen();
      await press('错误状态');
      expect(screen.getByRole('alert')).toBeOnTheScreen();
      await press('重试');
      expect(screen.queryByRole('alert')).toBeNull();
      expect(screen.getByRole('button', { name: '空状态' })).toBeSelected();
    },
  );
  it('never requests business data or logs local interactions', async () => {
    const fetch = jest
      .spyOn(global, 'fetch')
      .mockRejectedValue(new Error('Business network forbidden'));
    const logging = jest.spyOn(console, 'log').mockImplementation(() => undefined);
    try {
      await renderRouter(app, { initialUrl: '/import?relationshipId=demo-b' });
      await press('体验导入流程（演示数据）');
      await press('下一步');
      await press('我 → self');
      await press('匿名同学🌱 → person');
      await press('匿名同学🌱 → person-b');
      await press('系统通知🔔 → ignore');
      await press('下一步');
      await press('确认关系绑定（Demo）');
      await press('下一步');
      await press('下一步');
      await press('查看关系历史 Demo');
      await press('加载历史样例（Demo）');
      await press('查看更多（Demo）');
      await press('返回上一级');
      await press('返回上一级');
      await renderRouter(app, { initialUrl: '/settings' });
      await press('授权预览（Demo）');
      await press('暂停预览（Demo）');
      await press('查看记忆样例（Demo）');
      await press('预览删除全部记忆（Demo）');
      await press('删除后保留授权（Demo 选择）');
      await press('我已核对范围（仅演示）');
      expect(screen.getByRole('button', { name: '正式删除（尚未开放）' })).toBeDisabled();
      expect(fetch).not.toHaveBeenCalled();
      expect(logging).not.toHaveBeenCalled();
    } finally {
      fetch.mockRestore();
      logging.mockRestore();
    }
  });
  it('has no network/persistence/secret calls, no fixture imports in screens, no fabricated server success', () => {
    const files = (directory: string): string[] =>
      readdirSync(directory, { withFileTypes: true }).flatMap((entry) =>
        entry.isDirectory()
          ? files(join(directory, entry.name))
          : /\.tsx?$/.test(entry.name)
            ? [join(directory, entry.name)]
            : [],
      );
    for (const path of [...files('src'), ...files('app')]) {
      const code = readFileSync(path, 'utf8');
      expect(code).not.toMatch(
        /\b(fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(|\b(AsyncStorage|SecureStore|localStorage|sessionStorage)\b|console\.\w+\s*\(/,
      );
      expect(code).not.toMatch(
        /EXPO_PUBLIC_\w*(KEY|TOKEN|SECRET)|postgres(?:ql)?:\/\/|sk-[A-Za-z0-9_-]{16,}/,
      );
      expect(code).not.toMatch(/上传成功|服务器已关闭记忆|数据库写入成功|AI 分析完成|Memory saved/);
      if (/features|components/.test(path))
        expect(code).not.toMatch(/from\s+['"].*(demoSource|featureFixtures|controlFixtures)['"]/);
    }
    const fixture = readFileSync('src/data/controlFixtures.ts', 'utf8');
    expect(fixture).not.toMatch(/\b1[3-9]\d{9}\b|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|new Date\(/);
    expect(fixture).toContain('synthetic-demo');
  });
});
