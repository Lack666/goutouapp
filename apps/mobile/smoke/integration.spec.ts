import { test, expect, type Page } from '@playwright/test';

test.setTimeout(120_000);
function audit(page: Page) {
  const errors: string[] = [];
  const businessRequests: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (url.protocol === 'data:') return;
    if (
      url.origin !== 'http://localhost:8087' ||
      /\/api\/|\/auth\/|\/memory\/|\/agent\//.test(url.pathname)
    )
      businessRequests.push(url.pathname);
  });
  return () => {
    expect(errors).toEqual([]);
    expect(businessRequests).toEqual([]);
  };
}
const button = (page: Page, name: string) => page.getByRole('button', { name, exact: true });
const click = async (page: Page, name: string) => button(page, name).click();
const visible = async (page: Page, text: string | RegExp) => {
  const target = page.getByText(text, { exact: true });
  await target.scrollIntoViewIfNeeded();
  await expect(target).toBeVisible();
};
const noOverflow = async (page: Page) =>
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

for (const mode of ['浅色', '深色'])
  for (const width of [320, 360, 412]) {
    test(`Phase 7 final six-surface journey ${mode} ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 });
      const verified = audit(page);
      await page.goto('/');
      await click(page, '进入设置');
      await click(page, mode);
      await click(page, '返回上一级');
      await click(page, '进入关系资料');
      await click(page, '选择关系 B · 待补充');
      await expect(page.getByText('显示昵称：对象 A（合成）', { exact: true })).toHaveCount(0);
      await click(page, '前往导入与分析 Demo');
      await expect(page).toHaveURL(/import\?relationshipId=demo-b$/);
      await expect(button(page, '下一步')).toBeDisabled();
      await click(page, '体验导入流程（演示数据）');
      await click(page, '下一步');
      await expect(button(page, '下一步')).toBeDisabled();
      await expect(page.getByText('绑定：unbound', { exact: true })).toHaveCount(3);
      await click(page, '我 → self');
      await click(page, '匿名同学🌱 → person');
      await expect(button(page, '匿名同学🌱 → person-b')).toHaveAttribute('aria-pressed', 'false');
      await click(page, '匿名同学🌱 → person-b');
      await click(page, '系统通知🔔 → ignore');
      await click(page, '下一步');
      await expect(button(page, '下一步')).toBeDisabled();
      await expect(button(page, '选择关系 B · 待补充')).toHaveAttribute('aria-pressed', 'true');
      await click(page, '确认关系绑定（Demo）');
      await click(page, '下一步');
      await visible(page, '演示预检通过');
      await noOverflow(page);
      await click(page, '下一步');
      await expect(button(page, '正式导入（尚未开放）')).toBeDisabled();
      await click(page, '查看关系历史 Demo');
      await expect(page).toHaveURL(/history\?relationshipId=demo-b$/);
      await expect(button(page, '选择关系 B · 待补充')).toHaveAttribute('aria-pressed', 'true');
      await click(page, '加载历史样例（Demo）');
      await visible(page, /当前窗口：30 \/ 1020.*/);
      await click(page, '查看更多（Demo）');
      await visible(page, /当前窗口：60 \/ 1020.*/);
      await click(page, '查看更多（Demo）');
      await visible(page, /当前窗口：90 \/ 1020.*/);
      await expect(page.getByLabel(/^person · 匿名同学🌱：A /)).toHaveCount(0);
      await expect(page.getByText(/^A 合成历史/)).toHaveCount(0);
      await click(page, '进入 Chat 本地预览');
      await expect(page).toHaveURL(/chat\?relationshipId=demo-b$/);
      const input = page.getByLabel('本地预览消息输入');
      await input.fill('  \n  ');
      await expect(button(page, '添加到本地预览')).toBeDisabled();
      const message = '匿名合成 B 问题🌱\n第二行中文\n第三行中文\n第四行中文';
      await input.fill(message);
      await click(page, '添加到本地预览');
      const bubble = page.getByLabel(`你：${message}`, { exact: true });
      await expect(bubble).toBeVisible();
      await expect(input).toHaveValue('');
      await expect(page.getByLabel(/^助手（预置示例）：/)).toHaveCount(0);
      await page.screenshot({ path: `../../.cache/phase7d-chat-layout-${width}.png` });
      await expect
        .poll(async () => {
          const row = await bubble.boundingBox();
          const composer = await input.boundingBox();
          return row && composer ? row.y + row.height - composer.y : Infinity;
        })
        .toBeLessThanOrEqual(0);
      await noOverflow(page);
      await page.screenshot({
        path: `../../.cache/phase7d-chat-${mode === '浅色' ? 'light' : 'dark'}-${width}.png`,
      });
      // Pop the real Stack back through History, result and the selected B profile.
      for (const path of ['/history', '/import', '/relationship', '/']) {
        await click(page, '返回上一级');
        await expect(page).toHaveURL(new RegExp(path === '/' ? '/$' : `${path}(\\?|$)`));
        if (path === '/import') await expect(button(page, '正式导入（尚未开放）')).toBeDisabled();
        if (path === '/relationship')
          await expect(button(page, '选择关系 B · 待补充')).toHaveAttribute('aria-pressed', 'true');
      }
      await click(page, '进入设置');
      await visible(page, new RegExp(`当前外观：${mode}.*`));
      await click(page, '授权预览（Demo）');
      await click(page, '暂停预览（Demo）');
      await click(page, '查看记忆样例（Demo）');
      await visible(page, '合成摘要：关系 A 曾讨论学习活动。');
      await click(page, '撤销授权预览（Demo）');
      await click(page, '恢复预览（Demo）');
      await visible(page, 'Consent：未授权（演示）');
      await visible(page, 'Pause：已暂停（演示）');
      await visible(page, '合成摘要：关系 A 曾讨论学习活动。');
      await click(page, '查看撤销预览（Demo）');
      await expect(button(page, '正式撤销（尚未开放）')).toBeDisabled();
      await click(page, '预览删除全部记忆（Demo）');
      await expect(button(page, '我已核对范围（仅演示）')).toBeDisabled();
      await click(page, '删除后保留授权（Demo 选择）');
      await click(page, '我已核对范围（仅演示）');
      await expect(button(page, '正式删除（尚未开放）')).toBeDisabled();
      await click(page, '删除后撤销授权（Demo 选择）');
      await expect(button(page, '我已核对范围（仅演示）')).toHaveAttribute('aria-pressed', 'false');
      await click(page, '我已核对范围（仅演示）');
      await noOverflow(page);
      await page.screenshot({
        path: `../../.cache/phase7d-confirmation-${mode === '浅色' ? 'light' : 'dark'}-${width}.png`,
      });
      await click(page, '取消删除预览');
      await click(page, '重置 Memory Demo');
      await expect(button(page, '查看记忆样例（Demo）')).toHaveAttribute('aria-pressed', 'false');
      await visible(page, new RegExp(`当前外观：${mode}.*`));
      await page.reload();
      await visible(page, /当前外观：浅色.*/);
      await expect(button(page, '查看撤销预览（Demo）')).toHaveAttribute('aria-pressed', 'false');
      await click(page, '返回上一级');
      await expect(page.getByRole('heading', { name: '狗头军师', exact: true })).toBeVisible();
      verified();
    });
  }

test('direct routes reject missing, blank, duplicate and malformed scopes; unknown path recovers', async ({
  page,
}) => {
  const verified = audit(page);
  for (const path of ['/chat', '/relationship', '/import', '/history']) {
    for (const query of [
      'missing',
      '',
      'demo-a&relationshipId=demo-b',
      'demo-b&relationshipId=demo-b',
      '%20demo-b%20',
      'demo-b%5B%5D',
    ]) {
      await page.goto(`${path}?relationshipId=${query}`);
      await expect(page.getByRole('heading', { name: '关系不可用', exact: true })).toBeVisible();
      await expect(page.getByText('显示昵称：对象 A（合成）', { exact: true })).toHaveCount(0);
      await expect(page.getByTestId('message-local-1')).toHaveCount(0);
      await click(page, '返回上一级');
      await expect(page).toHaveURL(/\/$/);
    }
  }
  await page.goto('/does-not-exist');
  await click(page, '回到首页');
  await expect(page).toHaveURL(/\/$/);
  verified();
});

test('History A/B scope switches reset domain, window and old previews; Chat remount/reload clears draft', async ({
  page,
}) => {
  const verified = audit(page);
  await page.goto('/relationship');
  await click(page, '查看关系历史 Demo');
  await click(page, '加载历史样例（Demo）');
  await click(page, '查看更多（Demo）');
  await click(page, 'AI 对话');
  await click(page, '选择关系 B · 待补充');
  await visible(page, /当前窗口：0 \/ 0.*/);
  await expect(button(page, '关系聊天')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText(/^A 合成历史/)).toHaveCount(0);
  await click(page, '加载历史样例（Demo）');
  await visible(page, /当前窗口：30 \/ 1020.*/);
  await click(page, '错误状态');
  await page.getByRole('alert').scrollIntoViewIfNeeded();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByTestId(/^history-row-/)).toHaveCount(0);
  await click(page, '重试');
  await visible(page, /当前窗口：30 \/ 1020.*/);
  await click(page, '重置历史 Demo');
  await visible(page, /当前窗口：0 \/ 0.*/);
  await click(page, '选择关系 A · 同学');
  await click(page, '进入 Chat 本地预览');
  await page.getByLabel('本地预览消息输入').fill('A 合成未提交草稿');
  await page.reload();
  await expect(page.getByLabel('本地预览消息输入')).toHaveValue('');
  await click(page, '返回上一级');
  await expect(page).toHaveURL(/\/$/);
  await click(page, '开始对话');
  await page.getByLabel('本地预览消息输入').fill('合成临时预览');
  await click(page, '添加到本地预览');
  await click(page, '返回上一级');
  await click(page, '开始对话');
  await expect(page.getByTestId('message-local-1')).toHaveCount(0);
  verified();
});

test('Import empty/incompatible/group drafts cannot skip gates; change relationship and reset invalidate binding', async ({
  page,
}) => {
  const verified = audit(page);
  await page.goto('/import?relationshipId=demo-b');
  await click(page, '体验空来源（演示数据）');
  await expect(button(page, '下一步')).toBeDisabled();
  await click(page, '体验群聊样例（演示数据）');
  await click(page, '下一步');
  for (const name of [
    '我 → self',
    '匿名同学🌱 → person',
    '匿名同学🌱 → person-b',
    '系统通知🔔 → system',
    '匿名参与者🌿 → person',
    '匿名参与者🌿 → person-a',
  ])
    await click(page, name);
  await visible(page, '当前版本的一对一关系导入不支持多人群聊');
  await expect(button(page, '下一步')).toBeDisabled();
  await click(page, '匿名参与者🌿 → ignore');
  await click(page, '匿名同学🌱 → person-a');
  await click(page, '下一步');
  await expect(button(page, '下一步')).toBeDisabled();
  await click(page, '确认关系绑定（Demo）');
  await click(page, '下一步');
  await visible(page, 'speaker/relationship 不兼容');
  await expect(button(page, '下一步')).toBeDisabled();
  await click(page, '返回修改关系');
  await click(page, '选择关系 A · 同学');
  await expect(page.getByText('绑定：unbound', { exact: true })).toHaveCount(4);
  await expect(button(page, '下一步')).toBeDisabled();
  await click(page, '重置 Demo');
  await expect(button(page, '下一步')).toBeDisabled();
  await click(page, '体验导入流程（演示数据）');
  await click(page, '下一步');
  await expect(page.getByText('绑定：unbound', { exact: true })).toHaveCount(3);
  await page.reload();
  await expect(button(page, '下一步')).toBeDisabled();
  verified();
});
