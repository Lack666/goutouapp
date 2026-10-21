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
  await button(page, '返回上一级').click();
  await button(page, '进入关系资料').click();
}
for (const domain of ['person', 'relationship'] as const) {
  test(`actual ${domain} UI explicit full erasure, cancel, memory, SQL, survivor and same-key receipt`, async ({
    page,
    backend,
  }) => {
    const label = '9H Synthetic ' + domain;
    const a = await connected(backend.baseURL, backend.a, fetch, label);
    const b = await connected(backend.baseURL, backend.b, fetch, '9H Other Owner');
    try {
      await a.imports.select(async () => selectedFixture(4, label));
      await a.imports.upload();
      await bind(a.imports, a.person);
      await a.imports.finalize();
      await api(backend.baseURL, backend.a, '/memory/consent', { enabled: true });
      await api(backend.baseURL, backend.a, '/memory/resume', {});
      expect(
        (
          await api(backend.baseURL, backend.a, `/conversations/${a.conversation}/agent-runs`, {
            message: '我们计划第一周见面。请存入长期记忆。',
            operation_key: randomUUID(),
            expected_relationship_id: a.relationship,
          })
        ).status,
      ).toBe(200);
      const keep = await api(backend.baseURL, backend.a, '/relationships', {
        id: randomUUID(),
        person_id: a.person,
        relationship_type: 'unknown',
        status: 'unknown',
      });
      expect(keep.status).toBe(201);
      const before = await backend.erasureCommand('erasure_evidence');
      await login(page, backend.a);
      if (domain === 'person') await button(page, `查看 persons ${label}`).click();
      else await page.getByTestId(`resource-${a.relationship}`).getByRole('button').click();
      const id = domain === 'person' ? a.person : a.relationship;
      await button(
        page,
        `准备删除 ${domain === 'person' ? 'Person' : 'Relationship'} ${id}`,
      ).click();
      await expect(
        page.getByText('完整删除状态：awaiting_confirmation', { exact: true }),
      ).toBeVisible();
      await expect(page.getByText('长期记忆及关联 Undo：1', { exact: true })).toBeVisible();
      const executes: string[] = [];
      page.on('request', (r) => {
        if (r.url().endsWith('/lifecycle-erasures/execute')) executes.push(r.postData()!);
      });
      await button(page, '取消完整范围删除').click();
      expect(executes).toHaveLength(0);
      await button(page, '重新准备完整范围删除').click();
      await button(page, '明确确认并执行完整范围删除').click();
      await expect(page.getByText('完整删除状态：completed', { exact: true })).toBeVisible();
      await expect(page.getByText('完整删除权威刷新：verified', { exact: true })).toBeVisible();
      const evidence = await backend.erasureCommand('erasure_evidence');
      expect(
        (evidence.relationships as { id: string; deleted: boolean }[]).find(
          (r) => r.id === a.relationship,
        )?.deleted,
      ).toBe(true);
      expect(
        (evidence.relationships as { id: string; deleted: boolean }[]).find(
          (r) => r.id === b.relationship,
        )?.deleted,
      ).toBe(false);
      expect(evidence.memories).toBe((before.memories as number) - 1);
      expect(
        (await api(backend.baseURL, backend.a, `/relationships/${keep.value.id}`)).status,
      ).toBe(domain === 'person' ? 404 : 200);
      expect((await api(backend.baseURL, backend.a, `/persons/${a.person}`)).status).toBe(
        domain === 'person' ? 404 : 200,
      );
      expect(
        (await api(backend.baseURL, backend.b, `/relationships/${b.relationship}`)).status,
      ).toBe(200);
      await button(page, '同 key 重放完整范围删除').click();
      await expect(page.getByText('完整删除权威刷新：verified', { exact: true })).toBeVisible();
      expect(executes).toHaveLength(2);
      expect(executes[1]).toBe(executes[0]);
      expect(
        (
          (await backend.erasureCommand('erasure_evidence')).lifecycle_receipts as {
            target: string;
          }[]
        ).filter((r) => r.target === id),
      ).toHaveLength(1);
    } finally {
      await a.session.logout();
      await b.session.logout();
    }
  });
}
