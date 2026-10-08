import { render, screen, fireEvent } from '@testing-library/react-native';
import { renderRouter } from 'expo-router/testing-library';
import { Text } from 'react-native';
import RootLayout from '../app/_layout';
import Home from '../app/index';
import Chat from '../app/chat';
import Relationship from '../app/relationship';
import Import from '../app/import';
import History from '../app/history';
import Settings from '../app/settings';
import NotFound from '../app/+not-found';
import { DataSourceProvider } from '../src/data/DataSourceProvider';
import { demoSource } from '../src/data/demoSource';
import { ThemeProvider, resolveTheme, useTheme } from '../src/theme/ThemeProvider';
import { routes } from '../src/navigation/routes';
import { palettes } from '../src/theme/tokens';
import type { ShellDataSource, SurfaceState } from '../src/contracts/shell';
import { PrimaryButton } from '../src/components/ui';

const app = {
  _layout: RootLayout,
  index: Home,
  chat: Chat,
  relationship: Relationship,
  import: Import,
  history: History,
  settings: Settings,
  '+not-found': NotFound,
};

describe('actual Expo Router shell', () => {
  it.each(routes)('opens $path from Home and returns', async (route) => {
    const navigation = renderRouter(app, { initialUrl: '/' });
    await navigation;
    await fireEvent.press(
      screen.getByRole('button', {
        name: route.id === 'chat' ? route.label : `进入${route.label}`,
      }),
    );
    expect(navigation.getPathname()).toBe(route.path);
    expect(screen.getByText('本地演示 · Demo')).toBeOnTheScreen();
    await fireEvent.press(screen.getByRole('button', { name: '返回上一级' }));
    expect(navigation.getPathname()).toBe('/');
    expect(screen.getByText('狗头军师')).toBeOnTheScreen();
  });

  it.each(routes)('supports a direct link to $path with a Home fallback', async (route) => {
    const navigation = renderRouter(app, { initialUrl: route.path });
    await navigation;
    expect(navigation.getPathname()).toBe(route.path);
    await fireEvent.press(screen.getByRole('button', { name: '返回上一级' }));
    expect(navigation.getPathname()).toBe('/');
  });

  it('recovers an unknown route', async () => {
    const navigation = renderRouter(app, { initialUrl: '/unknown' });
    await navigation;
    expect(screen.getByText('页面不存在')).toBeOnTheScreen();
    await fireEvent.press(screen.getByRole('button', { name: '回到首页' }));
    expect(navigation.getPathname()).toBe('/');
  });

  it.each(['/chat', '/relationship', '/import', '/history'])(
    'controls local states and retry on %s',
    async (path) => {
      await renderRouter(app, { initialUrl: path });
      if (path === '/chat')
        await fireEvent.press(screen.getByRole('button', { name: '演示状态预览' }));
      await fireEvent.press(screen.getByRole('button', { name: '加载状态' }));
      expect(screen.getByText('演示加载中')).toBeOnTheScreen();
      await fireEvent.press(screen.getByRole('button', { name: '错误状态' }));
      expect(screen.getByRole('alert')).toBeOnTheScreen();
      await fireEvent.press(screen.getByRole('button', { name: '重试' }));
      expect(screen.queryByRole('alert')).toBeNull();
      expect(screen.getByRole('button', { name: '空状态' })).toBeSelected();
    },
  );

  it('keeps server sending unavailable and enables only local input', async () => {
    await renderRouter(app, { initialUrl: '/chat' });
    expect(screen.getByRole('button', { name: '发送（尚未开放）' })).toBeDisabled();
    expect(screen.getByLabelText('本地预览消息输入')).toHaveProp('editable', true);
    expect(screen.getByRole('button', { name: '添加到本地预览' })).toBeDisabled();
  });

  it.each([
    ['/relationship', '编辑资料（尚未开放）'],
    ['/import', '选择文件（尚未开放）'],
  ])('marks the business action unavailable on %s', async (path, label) => {
    await renderRouter(app, { initialUrl: path });
    expect(screen.getByRole('button', { name: label })).toBeDisabled();
  });

  it('changes theme and keeps the preference across navigation', async () => {
    await renderRouter(app, { initialUrl: '/' });
    await fireEvent.press(screen.getByRole('button', { name: '进入设置' }));
    await fireEvent.press(screen.getByRole('button', { name: '深色' }));
    expect(screen.getByText(/当前外观：深色/)).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: '深色' })).toBeSelected();
    await fireEvent.press(screen.getByRole('button', { name: '返回上一级' }));
    await fireEvent.press(screen.getByRole('button', { name: '进入设置' }));
    expect(screen.getByText(/当前外观：深色/)).toBeOnTheScreen();
    await fireEvent.press(screen.getByRole('button', { name: '浅色' }));
    expect(screen.getByText(/当前外观：浅色/)).toBeOnTheScreen();
  });
});

describe('provider and ViewModel boundary', () => {
  it('uses an injected source without importing fixtures into the screen', async () => {
    const source: ShellDataSource = {
      ...demoSource,
      readSurface: () => ({
        status: 'empty',
        view: {
          id: 'home',
          title: '替代数据源',
          description: '由替代数据源提供',
          emptyTitle: '空',
          emptyDescription: '空',
        },
      }),
    };
    const InjectedHome = () => (
      <ThemeProvider>
        <DataSourceProvider source={source}>
          <Home />
        </DataSourceProvider>
      </ThemeProvider>
    );
    await renderRouter({ index: InjectedHome });
    expect(screen.getByText('由替代数据源提供')).toBeOnTheScreen();
    expect(screen.queryByText('从这里开始，给关系留一点思考的空间。')).toBeNull();
  });

  it('returns isolated read values rather than shared mutable fixture objects', () => {
    const first = demoSource.readSurface('chat', 'empty');
    const second = demoSource.readSurface('chat', 'empty');
    expect(first).toEqual(second);
    expect(first).not.toBe(second);
    if (first.status === 'empty' && second.status === 'empty')
      expect(first.view).not.toBe(second.view);
  });

  it('applies palette colors when the local preference changes', async () => {
    function Probe() {
      const { colors, setPreference } = useTheme();
      return (
        <>
          <Text testID="color" style={{ color: colors.text }}>
            palette
          </Text>
          <PrimaryButton label="dark" onPress={() => setPreference('dark')} />
        </>
      );
    }
    await render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );
    await fireEvent.press(screen.getByRole('button', { name: 'dark' }));
    expect(screen.getByTestId('color')).toHaveStyle({ color: palettes.dark.text });
  });

  it('resolves system, explicit and unknown OS schemes', () => {
    expect(resolveTheme('system', 'dark')).toBe('dark');
    expect(resolveTheme('system', null)).toBe('light');
    expect(resolveTheme('light', 'dark')).toBe('light');
    expect(resolveTheme('dark', 'light')).toBe('dark');
  });
});

// Checked by strict tsc as well as runtime tests; invalid UI states cannot compile.
const valid: SurfaceState = { status: 'loading' };
// @ts-expect-error Empty requires a ViewModel.
const missingView: SurfaceState = { status: 'empty' };
void valid;
void missingView;
