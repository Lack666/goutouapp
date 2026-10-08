import { test, expect } from '@playwright/test';

test('six surfaces, return navigation, theme, UI states and small screens in real Expo Web', async ({
  page,
}) => {
  const errors: string[] = [];
  const externalRequests: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('request', (request) => {
    if (!request.url().startsWith('http://localhost:8087') && !request.url().startsWith('data:'))
      externalRequests.push(request.url());
  });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: '狗头军师', exact: true })).toBeVisible();
  for (const [label, path, heading] of [
    ['开始对话', '/chat', '对话'],
    ['进入关系资料', '/relationship', '关系资料'],
    ['进入导入与分析', '/import', '导入与分析'],
    ['进入历史记录', '/history', '历史记录'],
    ['进入设置', '/settings', '设置'],
  ]) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`${path}$`));
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: '本地演示 · Demo', exact: true })).toBeVisible();
    await page.getByRole('button', { name: '返回上一级', exact: true }).click();
    await expect(page).toHaveURL(/\/$/);
  }
  await page.getByRole('button', { name: '进入设置' }).click();
  await page.getByRole('button', { name: '深色', exact: true }).click();
  await expect(page.getByText(/当前外观：深色/)).toBeVisible();
  await expect(page.getByRole('heading', { name: '设置', exact: true })).toHaveCSS(
    'color',
    'rgb(239, 244, 237)',
  );
  await page.getByRole('button', { name: '返回上一级' }).click();
  await page.getByRole('button', { name: '开始对话' }).click();
  await expect(page.getByRole('button', { name: '发送（尚未开放）' })).toBeDisabled();
  await expect(page.getByLabel('消息输入（尚未开放）')).not.toBeEditable();
  await page.getByRole('button', { name: '加载状态' }).click();
  await expect(page.getByText('演示加载中', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '错误状态' }).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await page.getByRole('button', { name: '重试', exact: true }).click();
  await expect(page.getByText('还没有对话', { exact: true })).toBeVisible();

  for (const width of [320, 360, 412]) {
    await page.setViewportSize({ width, height: 800 });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true);
    const target = await page.getByRole('button', { name: '返回上一级' }).boundingBox();
    expect(target?.height).toBeGreaterThanOrEqual(48);
  }
  await page.screenshot({ path: '../../.cache/phase7a-chat-dark.png', fullPage: true });
  await page.getByRole('button', { name: '返回上一级' }).click();
  await page.getByRole('button', { name: '进入设置' }).click();
  await expect(page.getByText(/当前外观：深色/)).toBeVisible();
  await page.getByRole('button', { name: '浅色', exact: true }).click();
  await expect(page.getByRole('heading', { name: '设置', exact: true })).toHaveCSS(
    'color',
    'rgb(32, 46, 43)',
  );
  await page.getByRole('button', { name: '跟随系统' }).click();
  await page.emulateMedia({ colorScheme: 'dark' });
  await expect(page.getByText(/当前外观：深色/)).toBeVisible();
  await page.emulateMedia({ colorScheme: 'light' });
  await expect(page.getByText(/当前外观：浅色/)).toBeVisible();
  await page.getByRole('button', { name: '返回上一级' }).click();
  await page.getByRole('heading', { name: '狗头军师', exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: '../../.cache/phase7a-home-light.png', fullPage: true });

  // Direct links have an in-app return even without preceding navigation history.
  for (const path of ['/chat', '/relationship', '/import', '/history', '/settings']) {
    await page.goto(path);
    await expect(page.getByRole('button', { name: '返回上一级' })).toBeVisible();
    await page.getByRole('button', { name: '返回上一级' }).click();
    await expect(page).toHaveURL(/\/$/);
  }
  await page.goto('/unknown');
  await expect(page.getByText('页面不存在', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '回到首页' }).click();
  await expect(page).toHaveURL(/\/$/);
  expect(errors).toEqual([]);
  expect(externalRequests).toEqual([]);
});
