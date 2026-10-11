import type { Page } from '@playwright/test';
import { test, expect } from '../connected/fixture';
import { connected, scope } from './support';
const button = (page: Page, name: string) => page.getByRole('button', { name, exact: true });
async function login(page: Page, credential: string) {
  await page.goto('/settings');
  await button(page, '使用 Connected Development Mode').click();
  await page.getByLabel('开发 JWT（隐藏输入）').fill(credential);
  await button(page, '验证并接入开发会话').click();
  await expect(page.getByText('开发会话已连接', { exact: true })).toBeVisible();
  await expect(button(page, '重新读取 Memory 权威状态')).toBeEnabled();
}
async function send(page: Page, week: string) {
  await page.getByLabel('Agent 消息输入').fill(`我们计划第${week}周见面。请存入长期记忆。`);
  await button(page, '发送 Agent 消息').click();
  await expect(page.getByText('Agent 状态：运行完成', { exact: true })).toBeVisible();
  await button(page, '前往 Memory 控制与确认').click();
  await expect(button(page, '重新读取 Memory 权威状态')).toBeEnabled();
}
test('Chrome actual Settings / Agent SSE / Undo / one-person-all confirmation / durable receipt replay / owner isolation', async ({
  page,
  backend,
}) => {
  const value = await connected(backend.baseURL, backend.a);
  const target = await scope(value, '8E Chrome');
  const errors: string[] = [];
  const writes: string[] = [];
  page.on('pageerror', (error) => errors.push(error.name));
  page.on('request', (request) => {
    if (request.url().startsWith(backend.baseURL) && request.method() === 'POST')
      writes.push(new URL(request.url()).pathname);
  });
  try {
    await login(page, backend.a);
    await expect(page.getByText('Consent：未授权', { exact: true })).toBeVisible();
    await expect(button(page, '准备删除全部本人记忆')).toBeDisabled();
    await button(page, '授权长期记忆').click();
    await expect(page.getByText('Consent：已授权', { exact: true })).toBeVisible();
    await button(page, '恢复记忆').click();
    await expect(page.getByText('Pause：未暂停', { exact: true })).toBeVisible();
    await button(page, '返回上一级').click();
    await button(page, '开始 Agent 对话').click();
    await button(page, `选择 Conversation ${target.conversation}`).click();
    await send(page, '一');
    await expect(page.getByText('我们计划第一周见面', { exact: true })).toBeVisible();
    await expect(page.getByText(/New memories expire 37 days/).first()).toBeVisible();
    await button(page, '暂停记忆').click();
    await expect(page.getByText('Pause：已暂停', { exact: true })).toBeVisible();
    const beforePause = await backend.memoryEvidence();
    await button(page, '返回上一级').click();
    await send(page, '二');
    const paused = await backend.memoryEvidence();
    expect(paused.memories).toBe(beforePause.memories);
    expect(paused.recall_counts.at(-1)).toBe(0);
    await button(page, '恢复记忆').click();
    await expect(page.getByText('Pause：未暂停', { exact: true })).toBeVisible();
    await button(page, '检查最新 Undo 并准备确认').click();
    await expect(page.getByText('Mutation 状态：等待你明确确认', { exact: true })).toBeVisible();
    await button(page, '确认撤销该最新操作').click();
    await expect(page.getByText('Action：undo · Status：undone', { exact: true })).toBeVisible();
    await expect(page.getByText('当前范围没有有效记忆。', { exact: true })).toBeVisible();
    await button(page, '返回上一级').click();
    await send(page, '二');
    await value.memory.open();
    const one = value.memory.snapshot().items[0]!.id;
    await button(page, `准备删除记忆 ${one}`).click();
    await expect(page.getByText('服务器待删数量：1', { exact: true })).toBeVisible();
    await button(page, '确认执行服务器删除').click();
    await expect(
      page.getByText('Action：delete_one · Status：deleted', { exact: true }),
    ).toBeVisible();
    await button(page, '返回上一级').click();
    await send(page, '三');
    await button(page, `记忆 Person 8E Chrome · ${target.person}`).click();
    await button(page, '准备删除当前 Person 的记忆').click();
    await expect(page.getByText('服务器待删数量：1', { exact: true })).toBeVisible();
    await button(page, '确认执行服务器删除').click();
    await expect(
      page.getByText('Action：delete_person · Status：deleted', { exact: true }),
    ).toBeVisible();
    await button(page, '选择全部本人记忆').click();
    await button(page, '返回上一级').click();
    await send(page, '四');
    await button(page, '全部删除后撤销授权').click();
    await button(page, '准备删除全部本人记忆').click();
    await expect(page.getByText('服务器待删数量：1', { exact: true })).toBeVisible();
    await button(page, '全部删除后保留授权').click();
    await expect(button(page, '确认执行服务器删除')).toHaveCount(0);
    await button(page, '准备删除全部本人记忆').click();
    await button(page, '确认执行服务器删除').click();
    await expect(
      page.getByText('Action：delete_all · Status：deleted', { exact: true }),
    ).toBeVisible();
    await expect(page.getByText('Consent：已授权', { exact: true })).toBeVisible();
    await button(page, '查询服务器持久化回执').click();
    await expect(
      page.getByText('本次响应 replayed：否 · primary_store_only：是', { exact: true }),
    ).toBeVisible();
    await button(page, '返回上一级').click();
    await send(page, '五');
    await button(page, '安全重试原 Memory 操作').click();
    await expect(
      page.getByText('本次响应 replayed：是 · primary_store_only：是', { exact: true }),
    ).toBeVisible();
    await expect(page.getByText('我们计划第五周见面', { exact: true })).toBeVisible();
    expect((await backend.memoryEvidence()).memories).toBe(1);
    await button(page, '全部删除后撤销授权').click();
    await button(page, '准备删除全部本人记忆').click();
    await button(page, '确认执行服务器删除').click();
    await expect(page.getByText('Consent：未授权', { exact: true })).toBeVisible();
    await expect(page.getByText('Pause：已暂停', { exact: true })).toBeVisible();
    await button(page, '清除当前开发会话').click();
    await expect(page.getByText('未连接：没有开发凭证', { exact: true })).toBeVisible();
    await page.getByLabel('开发 JWT（隐藏输入）').fill(backend.b);
    await button(page, '验证并接入开发会话').click();
    await expect(page.getByText('当前范围没有有效记忆。', { exact: true })).toBeVisible();
    await expect(
      page.getByText('Action：delete_all · Status：deleted', { exact: true }),
    ).toHaveCount(0);
    await expect(button(page, '安全重试原 Memory 操作')).toBeDisabled();
    expect(errors).toEqual([]);
    expect(writes.some((path) => path.endsWith('/undo'))).toBe(true);
    expect(writes.some((path) => path.endsWith('/person/prepare'))).toBe(true);
  } finally {
    await value.session.logout();
  }
});
test('Chrome real committed response lost: unknown deletion never reports success or automatically re-prepares', async ({
  page,
  backend,
}) => {
  const value = await connected(backend.baseURL, backend.a);
  const target = await scope(value, '8E recovery');
  await value.memory.changeControl('grant');
  await value.memory.changeControl('resume');
  await value.chat.open(target.conversation, target.relationship);
  await value.chat.send('我们计划第一周见面。请存入长期记忆。', 'rest');
  await value.memory.open();
  const record = value.memory.snapshot().items[0]!.id;
  let loss = true;
  let executes = 0;
  let prepares = 0;
  await page.route('**/api/v1/memory/deletions/**', async (route) => {
    if (route.request().url().endsWith('/prepare')) prepares++;
    if (route.request().url().endsWith('/execute')) {
      executes++;
      if (loss) {
        loss = false;
        const response = await route.fetch();
        if (response.ok()) {
          await route.abort('failed');
          return;
        }
        await route.fulfill({ response });
        return;
      }
    }
    await route.continue();
  });
  try {
    await login(page, backend.a);
    await button(page, `准备删除记忆 ${record}`).click();
    await button(page, '确认执行服务器删除').click();
    await expect(page.getByText('Mutation 状态：操作结果未知', { exact: true })).toBeVisible();
    await expect(page.getByText('尚无已确认的服务器回执。', { exact: true })).toBeVisible();
    await button(page, '重新读取 Memory 权威状态').click();
    await expect(page.getByText('当前范围没有有效记忆。', { exact: true })).toBeVisible();
    await expect(page.getByText('Mutation 状态：操作结果未知', { exact: true })).toBeVisible();
    expect(executes).toBe(1);
    expect(prepares).toBe(1);
    await button(page, '安全重试原 Memory 操作').click();
    await expect(
      page.getByText('Action：delete_one · Status：deleted', { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText('本次响应 replayed：是 · primary_store_only：是', { exact: true }),
    ).toBeVisible();
    expect(executes).toBe(2);
    expect(prepares).toBe(1);
  } finally {
    await value.session.logout();
  }
});
