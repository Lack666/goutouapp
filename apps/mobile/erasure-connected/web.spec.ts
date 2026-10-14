import { randomUUID } from 'node:crypto';
import type { Page } from '@playwright/test';
import { test, expect } from '../connected/fixture';
import { connected, bind, selectedFixture } from '../import-connected/support';

const button = (page: Page, name: string) => page.getByRole('button', { name, exact: true });
async function api(base: string, credential: string, path: string, body?: unknown) {
  const response = await fetch(base + '/api/v1' + path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: {
      Authorization: `Bearer ${credential}`,
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  return { status: response.status, value: await response.json() };
}
async function login(page: Page, credential: string) {
  await page.goto('/settings');
  await button(page, '使用 Connected Development Mode').click();
  await page.getByLabel('开发 JWT（隐藏输入）').fill(credential);
  await button(page, '验证并接入开发会话').click();
  await expect(page.getByText('开发会话已连接', { exact: true })).toBeVisible();
}
async function navigate(page: Page, section: 'history' | 'settings' | 'chat') {
  const names = { history: '进入历史记录', settings: '进入设置', chat: '开始 Agent 对话' };
  for (let n = 0; n < 8; n++) {
    if (await button(page, names[section]).isVisible()) {
      await button(page, names[section]).click();
      return;
    }
    await button(page, '返回上一级').click();
  }
  throw new Error('App navigation did not reach Home');
}
async function history(page: Page, relationship?: string) {
  await navigate(page, 'history');
  if (relationship)
    await page.getByRole('button', { name: new RegExp('^选择.* · ' + relationship + '$') }).click();
}
async function imported(base: string, credential: string, tag: string) {
  const c = await connected(base, credential);
  for (const marker of [tag + 'erase', tag + 'keep']) {
    c.imports.clear();
    await c.imports.open(c.relationship);
    await c.imports.select(async () => selectedFixture(4, marker));
    await c.imports.upload();
    await bind(c.imports, c.person);
    await c.imports.finalize();
    expect(c.imports.snapshot().receipt?.count).toBe(4);
    if (marker.endsWith('erase')) c.resources.reserveConversation(c.relationship);
  }
  const response = await api(base, credential, `/relationships/${c.relationship}/datasets`);
  expect(response.status).toBe(200);
  return { ...c, datasets: response.value.items as { dataset_job_id: string }[] };
}
test('actual Dataset and Conversation UI confirmation/receipt, SQL deletion, other scopes, Memory and original-key replay', async ({
  page,
  backend,
}) => {
  const a = await imported(backend.baseURL, backend.a, '9F-closure');
  const other = await imported(backend.baseURL, backend.a, '9F-other');
  try {
    await api(backend.baseURL, backend.a, '/memory/consent', { enabled: true });
    await api(backend.baseURL, backend.a, '/memory/resume', {});
    const run = await api(
      backend.baseURL,
      backend.a,
      `/conversations/${a.conversation}/agent-runs`,
      {
        message: '我们计划第一周见面。请存入长期记忆。',
        operation_key: randomUUID(),
        expected_relationship_id: a.relationship,
      },
    );
    expect(run.status).toBe(200);
    const keep = await api(backend.baseURL, backend.a, '/conversations', {
      id: randomUUID(),
      relationship_id: a.relationship,
    });
    const before = await backend.erasureCommand('erasure_evidence');
    expect(before.memories).toBeGreaterThan(0);
    await login(page, backend.a);
    await history(page, a.relationship);
    await expect(button(page, `选择删除 Dataset ${a.datasets[0]!.dataset_job_id}`)).toBeVisible();
    await button(page, `选择删除 Dataset ${a.datasets[0]!.dataset_job_id}`).click();
    await button(page, '向服务器准备删除').click();
    await expect(
      page.getByText('服务器待删消息：4 · 保留 Run 元数据：0', { exact: true }),
    ).toBeVisible();
    const executes: string[] = [];
    page.on('request', (r) => {
      if (r.url().endsWith('/erasures/execute')) executes.push(r.postData()!);
    });
    await button(page, '取消本次删除确认').click();
    expect(executes).toHaveLength(0);
    await button(page, '向服务器准备删除').click();
    await button(page, '明确确认并执行此范围删除').click();
    await expect(page.getByText('删除状态：completed', { exact: true })).toBeVisible();
    await expect(page.getByText('权威刷新：verified', { exact: true })).toBeVisible();
    await expect(page.getByText(/^Receipt ID：/)).toBeVisible();
    await expect(page.getByText(/服务器状态：已删除 · Tombstone/)).toBeVisible();
    const sql = await backend.erasureCommand('erasure_evidence');
    const rows = sql.datasets as { id: string; messages: number; deleted: boolean }[];
    expect(rows.find((row) => row.id === a.datasets[0]!.dataset_job_id)).toMatchObject({
      deleted: true,
      messages: 0,
    });
    expect(rows.find((row) => row.id === a.datasets[1]!.dataset_job_id)).toMatchObject({
      deleted: false,
      messages: 4,
    });
    expect(rows.find((row) => row.id === other.datasets[0]!.dataset_job_id)).toMatchObject({
      deleted: false,
      messages: 4,
    });
    expect(sql.memories).toBe(before.memories);
    const historyPage = await api(
      backend.baseURL,
      backend.a,
      `/relationships/${a.relationship}/messages`,
    );
    expect(historyPage.value.items).toHaveLength(4);
    expect(
      historyPage.value.items.every(
        (item: { import_job_id: string }) => item.import_job_id === a.datasets[1]!.dataset_job_id,
      ),
    ).toBe(true);
    await button(page, '同 key 安全重放原删除').click();
    await expect(page.getByText('权威刷新：verified', { exact: true })).toBeVisible();
    expect(executes).toHaveLength(2);
    expect(executes[1]).toBe(executes[0]);
    await history(page);
    await button(page, 'AI 对话').click();
    await button(page, `历史 Conversation ${a.conversation}`).click();
    await expect(page.getByText(`删除目标：${a.conversation}`, { exact: true })).toBeVisible();
    await button(page, '向服务器准备删除').click();
    await expect(
      page.getByText('服务器待删消息：2 · 保留 Run 元数据：1', { exact: true }),
    ).toBeVisible();
    await button(page, '明确确认并执行此范围删除').click();
    await expect(page.getByText('删除状态：completed', { exact: true })).toBeVisible();
    await expect(page.getByText('权威刷新：verified', { exact: true })).toBeVisible();
    const final = await backend.erasureCommand('erasure_evidence');
    expect(
      (final.conversations as { id: string; deleted: boolean; messages: number }[]).find(
        (row) => row.id === a.conversation,
      ),
    ).toMatchObject({ deleted: true, messages: 0 });
    expect(final.memories).toBe(before.memories);
    expect((await api(backend.baseURL, backend.a, `/conversations/${keep.value.id}`)).status).toBe(
      200,
    );
    expect(
      (await api(backend.baseURL, backend.a, `/conversations/${a.conversation}/messages`)).status,
    ).toBe(404);
    expect(
      (
        await api(backend.baseURL, backend.a, '/conversations', {
          id: a.conversation,
          relationship_id: a.relationship,
        })
      ).status,
    ).toBe(409);
  } finally {
    await a.session.logout();
    await other.session.logout();
  }
});

test('actual committed response loss / original key replay / A-B denial / expired challenge / busy run / Demo separation', async ({
  page,
  backend,
}) => {
  const a = await imported(backend.baseURL, backend.a, '9F-fault');
  const target = {
    domain: 'dataset',
    target_id: a.datasets[0]!.dataset_job_id,
    relationship_id: a.relationship,
  };
  try {
    const prepare = await api(backend.baseURL, backend.a, '/erasures/prepare', target);
    expect(prepare.status).toBe(200);
    const body = {
      ...target,
      confirmation_id: prepare.value.confirmation_id,
      operation_key: randomUUID(),
    };
    expect((await api(backend.baseURL, backend.b, '/erasures/prepare', target)).status).toBe(404);
    expect((await api(backend.baseURL, backend.b, '/erasures/execute', body)).status).toBe(404);
    expect(
      (
        await api(backend.baseURL, backend.a, '/erasures/prepare', {
          ...target,
          relationship_id: randomUUID(),
        })
      ).status,
    ).toBe(404);
    await login(page, backend.a);
    await history(page, a.relationship);
    await button(page, `选择删除 Dataset ${target.target_id}`).click();
    await button(page, '向服务器准备删除').click();
    const confirmationText = await page.getByText(/^Confirmation ID：/).innerText();
    await backend.erasureCommand(`expire_erasure ${confirmationText.split('：')[1]}`);
    await button(page, '明确确认并执行此范围删除').click();
    await expect(page.getByText('删除状态：expired', { exact: true })).toBeVisible();
    await button(page, '向服务器准备删除').click();
    let lost = false;
    const bodies: string[] = [];
    await page.route('**/api/v1/erasures/execute', async (route) => {
      bodies.push(route.request().postData()!);
      const response = await route.fetch();
      if (!lost) {
        lost = true;
        expect(response.status()).toBe(200);
        await route.abort('failed');
      } else await route.fulfill({ response });
    });
    await button(page, '明确确认并执行此范围删除').click();
    await expect(page.getByText('删除状态：unknown_outcome', { exact: true })).toBeVisible();
    await button(page, '刷新服务器 Dataset').click();
    await expect(page.getByText('删除状态：unknown_outcome', { exact: true })).toBeVisible();
    await button(page, '同 key 安全重放原删除').click();
    await expect(page.getByText('删除状态：completed', { exact: true })).toBeVisible();
    await expect(page.getByText('权威刷新：verified', { exact: true })).toBeVisible();
    expect(bodies[0]).toBe(bodies[1]);
    const receiptId = (await page.getByText(/^Receipt ID：/).innerText()).split('：')[1]!;
    expect((await api(backend.baseURL, backend.b, `/erasures/receipts/${receiptId}`)).status).toBe(
      404,
    );
    expect(
      (await api(backend.baseURL, backend.b, '/erasures/execute', JSON.parse(bodies[0]!))).status,
    ).toBe(404);
    const busyTarget = {
      domain: 'conversation',
      target_id: a.conversation,
      relationship_id: a.relationship,
    };
    expect((await api(backend.baseURL, backend.b, '/erasures/prepare', busyTarget)).status).toBe(
      404,
    );
    const conChallenge = await api(backend.baseURL, backend.a, '/erasures/prepare', busyTarget);
    const conBody = {
      ...busyTarget,
      confirmation_id: conChallenge.value.confirmation_id,
      operation_key: randomUUID(),
    };
    expect((await api(backend.baseURL, backend.b, '/erasures/execute', conBody)).status).toBe(404);
    await backend.erasureCommand(`busy_conversation ${a.conversation}`);
    await navigate(page, 'chat');
    await button(page, `选择 Conversation ${a.conversation}`).click();
    await button(page, '向服务器准备删除').click();
    await expect(page.getByText('删除状态：target_busy', { exact: true })).toBeVisible();
    await button(page, '主动刷新 Busy 状态').click();
    await button(page, '向服务器准备删除').click();
    await expect(page.getByText('删除状态：target_busy', { exact: true })).toBeVisible();
    expect(
      (await api(backend.baseURL, backend.a, '/erasures/execute', conBody)).value.error.code,
    ).toBe('target_busy');
    await navigate(page, 'settings');
    await button(page, '清除当前开发会话').click();
    await expect(page.getByText('未连接：没有开发凭证', { exact: true })).toBeVisible();
    await page.getByLabel('开发 JWT（隐藏输入）').fill(backend.b);
    await button(page, '验证并接入开发会话').click();
    await expect(page.getByText('开发会话已连接', { exact: true })).toBeVisible();
    await history(page);
    await expect(page.getByRole('button', { name: new RegExp(a.relationship + '$') })).toHaveCount(
      0,
    );
    await expect(button(page, `选择删除 Dataset ${target.target_id}`)).toHaveCount(0);
    await expect(page.getByText(/^Receipt ID：/)).toHaveCount(0);
    await navigate(page, 'settings');
    await button(page, '使用 Demo Mode').click();
    const erasures: string[] = [];
    page.on('request', (r) => {
      if (r.url().includes('/erasures/')) erasures.push(r.url());
    });
    await history(page);
    expect(erasures).toEqual([]);
  } finally {
    await a.session.logout();
  }
});
