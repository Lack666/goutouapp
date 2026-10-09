import { test, expect } from '../connected/fixture';
import type { Page } from '@playwright/test';
async function connect(page: Page, credential: string) {
  await page.goto('/settings');
  await page.getByRole('button', { name: '使用 Connected Development Mode', exact: true }).click();
  await page.getByLabel('开发 JWT（隐藏输入）').fill(credential);
  await page.getByRole('button', { name: '验证并接入开发会话', exact: true }).click();
  await expect(page.getByText('开发会话已连接', { exact: true })).toBeVisible();
}
test('Phase 8C Agent Chat Connected Demo: real POST SSE, history, safe replay, logout and B isolation', async ({
  page,
  backend,
}) => {
  const errors: string[] = [];
  const methods: string[] = [];
  page.on('pageerror', (error) => errors.push(error.name));
  page.on('request', (request) => {
    if (request.url().endsWith('/agent-runs/stream')) methods.push(request.method());
  });
  await connect(page, backend.a);
  await page.getByRole('button', { name: '返回上一级' }).click();
  await page.getByRole('button', { name: '进入关系资料' }).click();
  await page.getByRole('button', { name: '选择通用会话（无关系绑定）', exact: true }).click();
  await page.getByRole('button', { name: '创建新 Conversation', exact: true }).click();
  await expect(page.getByText('服务器已确认保存 conversations', { exact: true })).toBeVisible();
  const idText = await page
    .getByText(/^UUID：/)
    .last()
    .textContent();
  const id = idText!.replace('UUID：', '');
  await page.getByRole('button', { name: '前往对话', exact: true }).click();
  await expect(page.getByText(`当前 Conversation：${id}`, { exact: true })).toBeVisible();
  const phases: string[] = [];
  page.on('response', (response) => {
    if (response.url().endsWith('/agent-runs/stream')) phases.push(`${response.status()}`);
  });
  await page.getByLabel('Agent 消息输入').fill('有人正在伤害我');
  await page.getByRole('button', { name: '发送 Agent 消息', exact: true }).click();
  await expect(page.getByText('Agent 状态：运行完成', { exact: true })).toBeVisible();
  expect(methods).toEqual(['POST']);
  expect(phases).toEqual(['200']);
  await expect(page.getByLabel(/^助手：/)).toHaveCount(1);
  await expect(page.getByLabel(/^你：/)).toHaveCount(1);
  await expect(page.getByText(/^run_id：/)).toBeVisible();
  await expect(page.getByText(/^operation_key：/)).toBeVisible();
  const before = await backend.agentEvidence();
  const run = before.runs.find((r) => r.conversation === id)!;
  expect(run.status).toBe('completed');
  expect(
    before.messages
      .filter((m) => m.conversation === id)
      .map((m) => m.role)
      .sort(),
  ).toEqual(['assistant', 'user']);
  await page.getByRole('button', { name: '重试原操作（REST）' }).click();
  await expect(page.getByText('Agent 状态：运行完成', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '刷新 Agent 历史' }).click();
  await expect(page.getByLabel(/^助手：/)).toHaveCount(1);
  expect((await backend.agentEvidence()).calls).toBe(before.calls);
  // Web credential is intentionally volatile; reload requires manual credential re-entry.
  await page.reload();
  await connect(page, backend.a);
  await page.getByRole('button', { name: '返回上一级' }).click();
  await page.getByRole('button', { name: '开始 Agent 对话' }).click();
  await page.getByRole('button', { name: `选择 Conversation ${id}`, exact: true }).click();
  await expect(page.getByLabel(/^助手：/)).toHaveCount(1);
  await expect(page.getByLabel(/^你：/)).toHaveCount(1);
  await page.getByRole('button', { name: '清除当前开发会话' }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await connect(page, backend.b);
  await page.getByRole('button', { name: '返回上一级' }).click();
  await page.getByRole('button', { name: '开始 Agent 对话' }).click();
  await expect(
    page.getByText('请在关系资料中创建或选择真实会话。没有会话时不会发送。', { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: `选择 Conversation ${id}`, exact: true }),
  ).toHaveCount(0);
  await expect(page.getByLabel(/^助手：/)).toHaveCount(0);
  await expect(page.getByRole('button', { name: '发送 Agent 消息' })).toBeDisabled();
  expect(errors).toEqual([]);
});
