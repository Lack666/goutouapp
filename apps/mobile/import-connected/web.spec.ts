import { writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { test, expect } from '../connected/fixture';
import { connected, syntheticTranscript } from './support';
test('Chrome Expo real file picker, explicit bindings/ready/finalize, formal History pages/refresh/logout', async ({
  page,
  backend,
}) => {
  const seeded = await connected(backend.baseURL, backend.a);
  const fixture = resolve('../../.cache/phase8d-anonymous-wechat.md');
  await writeFile(fixture, syntheticTranscript(1001, 'browser'), 'utf8');
  const paths: string[] = [];
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.name));
  page.on('request', (request) => {
    if (request.url().startsWith(backend.baseURL))
      paths.push(`${request.method()} ${new URL(request.url()).pathname}`);
  });
  try {
    await page.goto('/settings');
    await page
      .getByRole('button', { name: '使用 Connected Development Mode', exact: true })
      .click();
    await page.getByLabel('开发 JWT（隐藏输入）').fill(backend.a);
    await page.getByRole('button', { name: '验证并接入开发会话', exact: true }).click();
    await expect(page.getByText('开发会话已连接', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: '返回上一级' }).click();
    await page.getByRole('button', { name: '进入导入与分析' }).click();
    const chooser = page.waitForEvent('filechooser');
    await page.getByRole('button', { name: '选择微信 Markdown 文件', exact: true }).click();
    await (await chooser).setFiles(fixture);
    await expect(page.getByText(/文件：phase8d-anonymous-wechat.md/)).toBeVisible();
    expect(paths.some((path) => path === 'POST /api/v1/chat-imports')).toBe(false);
    await page.getByRole('button', { name: '上传并创建任务', exact: true }).click();
    await expect(page.getByText(/服务器状态：awaiting_binding/)).toBeVisible();
    await page.getByRole('button', { name: '我 → self', exact: true }).click();
    await page.getByRole('button', { name: '提交 我 绑定', exact: true }).click();
    await page.getByRole('button', { name: '匿名同学🥰 → person', exact: true }).click();
    await page.getByRole('button', { name: `匿名同学🥰 → ${seeded.person}`, exact: true }).click();
    await page.getByRole('button', { name: '提交 匿名同学🥰 绑定', exact: true }).click();
    await page.getByRole('button', { name: '下一步：选择关系', exact: true }).click();
    await page
      .getByRole('button', {
        name: `选择8D anonymous synthetic · ${seeded.relationship}`,
        exact: true,
      })
      .click();
    // Choosing the relationship invalidates all previous confirmations.
    await page.getByRole('button', { name: '提交 我 绑定', exact: true }).click();
    await page.getByRole('button', { name: '提交 匿名同学🥰 绑定', exact: true }).click();
    await page.getByRole('button', { name: '下一步：选择关系', exact: true }).click();
    await page.getByRole('button', { name: '确认并提交关系绑定', exact: true }).click();
    await expect(
      page.getByRole('button', { name: '正式导入聊天记录', exact: true }),
    ).toBeDisabled();
    await page.getByRole('button', { name: '请求服务器预检', exact: true }).click();
    await expect(page.getByText(/服务器状态：ready/)).toBeVisible();
    await page.getByRole('button', { name: '正式导入聊天记录', exact: true }).click();
    await expect(
      page.getByText('聊天记录已成功导入，可在历史记录中查看。', { exact: true }),
    ).toBeVisible();
    await page.getByRole('button', { name: '查看真实关系聊天历史', exact: true }).click();
    await expect(page.getByText(/已读取 100 条/)).toBeVisible();
    await page.getByRole('button', { name: '加载更多服务器历史', exact: true }).click();
    await expect(page.getByText(/已读取 200 条/)).toBeVisible();
    await page.getByRole('button', { name: '刷新服务器历史', exact: true }).click();
    await expect(page.getByText(/已读取 100 条/)).toBeVisible();
    await page.getByRole('button', { name: 'AI 对话', exact: true }).click();
    await expect(page.getByText(/已读取 0 条/)).toBeVisible();
    await page
      .getByRole('button', { name: `历史 Conversation ${seeded.conversation}`, exact: true })
      .click();
    await expect(page.getByText('还没有历史记录', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: '清除当前开发会话', exact: true }).click();
    await expect(page).toHaveURL(/\/settings$/);
    await expect(page.getByText('未连接：没有开发凭证', { exact: true })).toBeVisible();
    await page.getByLabel('开发 JWT（隐藏输入）').fill(backend.b);
    await page.getByRole('button', { name: '验证并接入开发会话', exact: true }).click();
    await expect(page.getByText('开发会话已连接', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: '返回上一级' }).click();
    await page.getByRole('button', { name: '进入历史记录' }).click();
    await expect(page.getByText(/已读取 0 条/)).toBeVisible();
    expect(paths.some((path) => path.startsWith('POST /api/v1/memory'))).toBe(false);
    expect(paths.some((path) => path.includes('/agent-runs'))).toBe(false);
    expect(errors).toEqual([]);
  } finally {
    await seeded.session.logout();
  }
});
