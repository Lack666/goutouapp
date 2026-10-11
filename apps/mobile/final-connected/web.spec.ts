import type { Page } from '@playwright/test';
import { test, expect } from '../connected/fixture';
import { connected } from '../memory-connected/support';
import { syntheticTranscript } from '../import-connected/support';
const button = (page: Page, name: string) => page.getByRole('button', { name, exact: true });

test('8F six real Connected surfaces retain one owned scope and separate data domains through deletion and owner switch', async ({
  page,
  backend,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.name));
  await page.goto('/settings');
  await button(page, '使用 Connected Development Mode').click();
  await page.getByLabel('开发 JWT（隐藏输入）').fill(backend.a);
  await button(page, '验证并接入开发会话').click();
  await expect(page.getByText('开发会话已连接', { exact: true })).toBeVisible();
  await button(page, '授权长期记忆').click();
  await expect(page.getByText('Consent：已授权', { exact: true })).toBeVisible();
  await button(page, '恢复记忆').click();
  await button(page, '返回上一级').click();
  await button(page, '进入关系资料').click();
  await page.getByLabel('Person 显示名称').fill('8F synthetic');
  await button(page, '创建新 Person').click();
  await expect(page.getByText('服务器已确认保存 persons', { exact: true })).toBeVisible();
  await button(page, '使用 Person 8F synthetic').click();
  await page.getByLabel('关系类型（必填）').fill('unknown');
  await page.getByLabel('关系状态（必填）').fill('unknown');
  await button(page, '创建新 Relationship').click();
  await expect(page.getByText('服务器已确认保存 relationships', { exact: true })).toBeVisible();
  const binding = await page
    .getByRole('button', { name: /^绑定 Relationship / })
    .last()
    .getAttribute('aria-label');
  const relationship = binding!.replace('绑定 Relationship ', '');
  await button(page, binding!).click();
  await button(page, '创建新 Conversation').click();
  await expect(page.getByText(`绑定关系：${relationship}`, { exact: true })).toBeVisible();
  const value = await connected(backend.baseURL, backend.a);
  try {
    await value.resources.load('persons');
    const person = value.resources
      .snapshot()
      .pages.persons.items.find((item) => item.nickname === '8F synthetic')!.id;
    await button(page, '前往对话').click();
    await expect(page).toHaveURL(new RegExp(`relationshipId=${relationship}`));
    await page.getByLabel('Agent 消息输入').fill('我们计划第一周见面。请存入长期记忆。');
    await button(page, '发送 Agent 消息').click();
    await expect(page.getByText('Agent 状态：运行完成', { exact: true })).toBeVisible();
    const first = await backend.agentEvidence();
    expect(first.runs).toHaveLength(1);
    expect(first.messages).toHaveLength(2);
    expect(first.memories).toBe(1);
    await button(page, '重试原操作（REST）').click();
    await expect(page.getByText('Agent 状态：运行完成', { exact: true })).toBeVisible();
    const replay = await backend.agentEvidence();
    expect(replay.runs).toEqual(first.runs);
    expect(replay.messages).toEqual(first.messages);
    expect(replay.calls).toEqual(first.calls);
    await button(page, '返回上一级').click();
    await button(page, '前往导入').click();
    const chooser = page.waitForEvent('filechooser');
    await button(page, '选择微信 Markdown 文件').click();
    await (
      await chooser
    ).setFiles({
      name: 'phase8f-synthetic.md',
      mimeType: 'text/markdown',
      buffer: Buffer.from(syntheticTranscript(301, '8F')),
    });
    await button(page, '上传并创建任务').click();
    await expect(page.getByText(/服务器状态：awaiting_binding/)).toBeVisible();
    await button(page, '我 → self').click();
    await button(page, '提交 我 绑定').click();
    await button(page, '匿名同学🥰 → person').click();
    await button(page, `匿名同学🥰 → ${person}`).click();
    await button(page, '提交 匿名同学🥰 绑定').click();
    await button(page, '下一步：选择关系').click();
    await button(page, '确认并提交关系绑定').click();
    await expect(button(page, '正式导入聊天记录')).toBeDisabled();
    await button(page, '请求服务器预检').click();
    await expect(page.getByText(/服务器状态：ready/)).toBeVisible();
    await button(page, '正式导入聊天记录').click();
    await expect(
      page.getByText('聊天记录已成功导入，可在历史记录中查看。', { exact: true }),
    ).toBeVisible();
    await button(page, '查看真实关系聊天历史').click();
    for (const count of [100, 200, 300, 301]) {
      await expect(page.getByText(new RegExp(`已读取 ${count} 条`))).toBeVisible();
      if (count < 301) await button(page, '加载更多服务器历史').click();
    }
    const imported = await backend.importEvidence();
    expect(imported.messages).toBe(301);
    expect(imported.agent_messages).toBe(2);
    expect(imported.active_artifacts).toBe(0);
    await button(page, '刷新服务器历史').click();
    await expect(page.getByText(/已读取 100 条/)).toBeVisible();
    await button(page, 'AI 对话').click();
    await button(page, `历史 Conversation ${first.runs[0]!.conversation}`).click();
    await expect(page.getByText(/已读取 2 条/)).toBeVisible();
    await button(page, '返回上一级').click();
    await button(page, '返回上一级').click();
    await button(page, '返回上一级').click();
    await button(page, '进入设置').click();
    await button(page, '暂停记忆').click();
    await expect(page.getByText('Pause：已暂停', { exact: true })).toBeVisible();
    await button(page, '恢复记忆').click();
    await expect(page.getByText('Pause：未暂停', { exact: true })).toBeVisible();
    await button(page, '全部删除后保留授权').click();
    await button(page, '准备删除全部本人记忆').click();
    await expect(page.getByText('服务器待删数量：1', { exact: true })).toBeVisible();
    expect((await backend.memoryEvidence()).memories).toBe(1);
    await button(page, '确认执行服务器删除').click();
    await expect(
      page.getByText('Action：delete_all · Status：deleted', { exact: true }),
    ).toBeVisible();
    const deleted = await backend.memoryEvidence();
    expect(deleted.memories).toBe(0);
    expect(deleted.agent_messages).toBe(2);
    expect(deleted.relationship_messages).toBe(301);
    await button(page, '清除当前开发会话').click();
    await expect(page.getByText('未连接：没有开发凭证', { exact: true })).toBeVisible();
    await page.getByLabel('开发 JWT（隐藏输入）').fill(backend.b);
    await button(page, '验证并接入开发会话').click();
    await expect(page.getByText('当前范围没有有效记忆。', { exact: true })).toBeVisible();
    await expect(button(page, '安全重试原 Memory 操作')).toBeDisabled();
    await button(page, '返回上一级').click();
    await button(page, '进入关系资料').click();
    for (const kind of ['persons', 'relationships', 'conversations'])
      await expect(page.getByText(`当前用户没有 ${kind}`, { exact: true })).toBeVisible();
    await button(page, '返回上一级').click();
    await button(page, '进入历史记录').click();
    await expect(page.getByText(/已读取 0 条/)).toBeVisible();
    const foreign = await value.transport.client.GET('/api/v1/relationships/{relationship_id}', {
      params: {
        path: {
          relationship_id: relationship as `${string}-${string}-${string}-${string}-${string}`,
        },
      },
    });
    expect(foreign.response.status).toBe(200); // A still owns its resource.
    await value.session.connect(backend.b, value.resources.probe);
    await expect(
      value.transport.client.GET('/api/v1/relationships/{relationship_id}', {
        params: {
          path: {
            relationship_id: relationship as `${string}-${string}-${string}-${string}-${string}`,
          },
        },
      }),
    ).rejects.toMatchObject({ kind: 'not_found' });
    expect(errors).toEqual([]);
  } finally {
    await value.session.logout();
  }
});
