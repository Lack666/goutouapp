import { test, expect } from './fixture';
import type { Page } from '@playwright/test';
async function connect(page: Page, credential: string) {
  const statuses: number[] = [];
  const failures: string[] = [];
  page.on('requestfailed', (request) => {
    failures.push(`${new URL(request.url()).origin}: ${request.failure()?.errorText}`);
  });
  page.on('response', (response) => {
    if (response.url().includes('/api/v1/persons')) statuses.push(response.status());
  });
  await page.getByRole('button', { name: '使用 Connected Development Mode', exact: true }).click();
  await page.getByLabel('开发 JWT（隐藏输入）').fill(credential);
  await page.getByRole('button', { name: '验证并接入开发会话', exact: true }).click();
  try {
    await expect(page.getByText('开发会话已连接', { exact: true })).toBeVisible();
  } catch {
    throw new Error(
      `Resource HTTP statuses: ${statuses.join(',')}; failures: ${failures.join(',')}`,
    );
  }
}
test('real Expo Web owned resource creation, lost response retry, contexts and A to B isolation', async ({
  page,
  backend,
}) => {
  const errors: string[] = [];
  const requests: string[] = [];
  const memoryRequests: { method: string; path: string }[] = [];
  page.on('pageerror', (error) => errors.push(error.name));
  page.on('request', (request) => {
    if (request.url().startsWith(backend.baseURL)) {
      const path = new URL(request.url()).pathname;
      requests.push(path);
      if (/^\/api\/v1\/(memory\/|memories)/.test(path))
        memoryRequests.push({ method: request.method(), path });
    }
  });
  await page.goto('/settings');
  await connect(page, backend.a);
  await page.getByRole('button', { name: '返回上一级' }).click();
  await page.getByRole('button', { name: '进入关系资料' }).click();
  await expect(
    page.getByRole('button', { name: '查看 persons Mobile HTTP synthetic A', exact: true }),
  ).toBeVisible();
  let lost = false;
  await page.route(`${backend.baseURL}/api/v1/persons`, async (route) => {
    if (route.request().method() === 'POST' && !lost) {
      lost = true;
      await route.fetch();
      await route.abort('failed');
    } else await route.continue();
  });
  await page.getByLabel('Person 显示名称').fill('Web synthetic person');
  await page.getByRole('button', { name: '创建新 Person', exact: true }).click();
  await expect(page.getByRole('button', { name: '重试原创建 persons' })).toBeVisible();
  await page.getByLabel('Person 显示名称').fill('edited after failure');
  await page.getByRole('button', { name: '重试原创建 persons' }).click();
  await expect(page.getByText('服务器已确认保存 persons', { exact: true })).toBeVisible();
  await expect(
    page.getByRole('button', { name: '查看 persons Web synthetic person' }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: '查看 persons edited after failure' })).toHaveCount(
    0,
  );
  await page.getByRole('button', { name: '使用 Person Web synthetic person' }).click();
  await page.getByLabel('关系类型（必填）').fill('unknown');
  await page.getByLabel('关系状态（必填）').fill('unknown');
  await page.getByRole('button', { name: '创建新 Relationship', exact: true }).click();
  await expect(page.getByText('服务器已确认保存 relationships', { exact: true })).toBeVisible();
  const relationship = await page
    .getByRole('button', { name: /^绑定 Relationship / })
    .last()
    .getAttribute('aria-label');
  const relationshipId = relationship!.replace('绑定 Relationship ', '');
  await page.getByRole('button', { name: relationship!, exact: true }).click();
  await page.getByRole('button', { name: '创建新 Conversation', exact: true }).click();
  await expect(page.getByText('服务器已确认保存 conversations', { exact: true })).toBeVisible();
  // The saved response precedes the formal list/detail selection. Navigation
  // needs that owned detail, so await it rather than racing the async selection.
  await expect(page.getByText(`绑定关系：${relationshipId}`, { exact: true })).toBeVisible();
  for (const [label, path] of [
    ['前往对话', 'chat'],
    ['前往导入', 'import'],
    ['前往历史', 'history'],
  ]) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`/${path}\\?.*relationshipId=${relationshipId}`));
    if (path === 'chat') {
      await expect(page.getByText(`关系范围：${relationshipId}`, { exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: '发送 Agent 消息' })).toBeDisabled(); // Empty composer; no Agent request in 8B regression.
    } else if (path === 'import') {
      await expect(
        page.getByRole('button', { name: '上传并创建任务', exact: true }),
      ).toBeDisabled();
      await expect(
        page.getByRole('button', { name: '选择微信 Markdown 文件', exact: true }),
      ).toBeEnabled();
    } else {
      await expect(page.getByText(new RegExp(`范围：${relationshipId}`))).toBeVisible();
      await expect(page.getByText(/已读取 0 条/)).toBeVisible();
    }
    await page.getByRole('button', { name: '返回上一级' }).click();
  }
  await page.getByRole('button', { name: '清除当前开发会话' }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByText('未连接：没有开发凭证', { exact: true })).toBeVisible();
  await expect(page.getByText('Web synthetic person', { exact: true })).toHaveCount(0);
  await connect(page, backend.b);
  await page.getByRole('button', { name: '返回上一级' }).click();
  await page.getByRole('button', { name: '进入关系资料' }).click();
  await expect(page.getByText('当前用户没有 persons', { exact: true })).toBeVisible();
  await expect(page.getByText('当前用户没有 relationships', { exact: true })).toBeVisible();
  await expect(page.getByText('当前用户没有 conversations', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: '本地演示 · Demo', exact: true })).toBeVisible();
  expect(
    await page.evaluate(() =>
      Object.keys(localStorage).filter((key) => /jwt|token|session/i.test(key)),
    ),
  ).toEqual([]);
  expect(
    requests.every(
      (path) =>
        /^\/api\/v1\/(persons|relationships|conversations)(\/[a-f0-9-]{36})?$/.test(path) ||
        /^\/api\/v1\/(conversations|relationships)\/[a-f0-9-]{36}\/messages$/.test(path) ||
        ['/api/v1/memory/control', '/api/v1/memories', '/api/v1/memory/undo/preview'].includes(
          path,
        ), // 8E Settings inspects Memory; all mutations remain forbidden in this resource regression.
    ),
  ).toBe(true);
  expect(memoryRequests.every((request) => request.method === 'GET')).toBe(true);
  expect(errors).toEqual([]);
  expect(await backend.counts()).toEqual({ persons: 3, relationships: 2, conversations: 2 });
});
test('real browser rejects expired/invalid credentials, normalizes offline and clears on server 401', async ({
  page,
  backend,
  context,
}) => {
  await page.goto('/settings');
  await page.getByRole('button', { name: '使用 Connected Development Mode' }).click();
  await page.getByLabel('开发 JWT（隐藏输入）').fill(backend.expired);
  await page.getByRole('button', { name: '验证并接入开发会话' }).click();
  await expect(page.getByText('开发凭证已过期，请重新获取', { exact: true })).toBeVisible();
  await page.getByLabel('开发 JWT（隐藏输入）').fill('invalid');
  await page.getByRole('button', { name: '验证并接入开发会话' }).click();
  await expect(page.getByText('开发凭证无效，请重新获取', { exact: true })).toBeVisible();
  await connect(page, backend.a);
  await page.getByRole('button', { name: '返回上一级' }).click();
  await page.getByRole('button', { name: '进入关系资料' }).click();
  // This credential test must also work if Playwright recreated its worker DB.
  await page.getByLabel('Person 显示名称').fill('Credential synthetic person');
  await page.getByRole('button', { name: '创建新 Person', exact: true }).click();
  await expect(
    page.getByRole('button', { name: '查看 persons Credential synthetic person', exact: true }),
  ).toBeVisible();
  await context.setOffline(true);
  await page.getByRole('button', { name: '刷新 persons', exact: true }).click();
  await expect(page.getByText(/网络不可用，提交结果可能未知/)).toBeVisible();
  await context.setOffline(false);
  await page.getByRole('button', { name: '重试读取 persons' }).click();
  await expect(
    page.getByRole('button', { name: '查看 persons Credential synthetic person', exact: true }),
  ).toBeVisible();
  await page.route(`${backend.baseURL}/api/v1/persons*`, (route) =>
    route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: '{"error":{"code":"invalid_credential","message":"private"}}',
    }),
  );
  await page.getByRole('button', { name: '刷新 persons', exact: true }).click();
  await expect(page.getByText('开发凭证无效，请重新获取', { exact: true })).toBeVisible();
  await expect(
    page.getByRole('button', { name: '查看 persons Mobile HTTP synthetic A', exact: true }),
  ).toHaveCount(0);
});
