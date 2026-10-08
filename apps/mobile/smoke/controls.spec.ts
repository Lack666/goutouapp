import { test, expect } from '@playwright/test';

test.setTimeout(90_000);
for (const mode of ['浅色', '深色']) {
  for (const width of [320, 360, 412]) {
    test(`Import History Settings ${mode} ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 });
      const errors: string[] = [];
      const requests: string[] = [];
      page.on('pageerror', (error) => errors.push(error.message));
      page.on('console', (message) => {
        if (message.type() === 'error') errors.push(message.text());
      });
      page.on('request', (request) => {
        const url = request.url();
        if (
          (!url.startsWith('http://localhost:8087') && !url.startsWith('data:')) ||
          /\/api\/|\/auth\/|\/memory\/|\/agent\//.test(url)
        )
          requests.push(url);
      });
      const click = async (name: string) => page.getByRole('button', { name, exact: true }).click();
      const noOverflow = async () =>
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
          true,
        );
      const shot = async (name: string) => {
        await noOverflow();
        await page.screenshot({
          path: `../../.cache/phase7c-${name}-${mode === '浅色' ? 'light' : 'dark'}-${width}.png`,
        });
      };
      await page.goto('/');
      await click('进入设置');
      await click(mode);
      await click('返回上一级');
      await click('进入关系资料');
      await click('选择关系 B · 待补充');
      await click('前往导入与分析 Demo');
      await expect(page).toHaveURL(/import\?relationshipId=demo-b$/);
      await expect(
        page.getByText('本地演示 · 未连接服务器。真实文件上传将在后续版本接入。'),
      ).toBeVisible();
      await expect(page.getByRole('button', { name: '下一步', exact: true })).toBeDisabled();
      await click('体验导入流程（演示数据）');
      await expect(page.getByText('消息：12 · 说话人：3')).toBeVisible();
      await click('下一步');
      await expect(page.getByText('绑定：unbound', { exact: true })).toHaveCount(3);
      await shot('speakers');
      await click('我 → self');
      await click('匿名同学🌱 → person');
      await click('匿名同学🌱 → person-b');
      await click('系统通知🔔 → system');
      await click('下一步');
      await expect(page.getByRole('button', { name: '选择关系 B · 待补充' })).toHaveAttribute(
        'aria-pressed',
        'true',
      );
      await click('确认关系绑定（Demo）');
      await click('下一步');
      await page.getByText('演示预检通过', { exact: true }).scrollIntoViewIfNeeded();
      await expect(page.getByText('演示预检通过', { exact: true })).toBeVisible();
      await shot('readiness');
      await click('下一步');
      await expect(page.getByRole('button', { name: '正式导入（尚未开放）' })).toBeDisabled();
      await click('返回上一级');
      await expect(page.getByRole('button', { name: '选择关系 B · 待补充' })).toHaveAttribute(
        'aria-pressed',
        'true',
      );
      await click('查看关系历史 Demo');
      await expect(page).toHaveURL(/history\?relationshipId=demo-b$/);
      await click('加载历史样例（Demo）');
      await page
        .getByLabel('self · 我：B 合成历史 0 🌱\n\n讨论学习活动的安排。', { exact: true })
        .scrollIntoViewIfNeeded();
      await expect(
        page.getByLabel('self · 我：B 合成历史 0 🌱\n\n讨论学习活动的安排。', { exact: true }),
      ).toBeVisible();
      await expect(page.getByText(/^A 合成历史/)).toHaveCount(0);
      await expect(page.getByText(/^AI 助手示例 · assistant/)).toHaveCount(0);
      await shot('history');
      await click('查看更多（Demo）');
      await page.getByText(/当前窗口：60 \/ 1020/).scrollIntoViewIfNeeded();
      await expect(page.getByText(/当前窗口：60 \/ 1020/)).toBeVisible();
      await click('AI 对话');
      await page.getByText(/^AI 助手示例 · assistant/).scrollIntoViewIfNeeded();
      await expect(page.getByText(/^AI 助手示例 · assistant/)).toBeVisible();
      await expect(page.getByText(/^person · 匿名同学/)).toHaveCount(0);
      await click('进入 Chat 本地预览');
      await expect(page).toHaveURL(/chat\?relationshipId=demo-b$/);
      await expect(page.getByLabel('本地预览消息输入')).toHaveValue('');
      await click('返回上一级');
      await click('返回上一级');
      await click('返回上一级');
      await click('进入设置');
      await click('授权预览（Demo）');
      await click('暂停预览（Demo）');
      await page.getByText('Pause：已暂停（演示）', { exact: true }).scrollIntoViewIfNeeded();
      await expect(page.getByText('Pause：已暂停（演示）', { exact: true })).toBeVisible();
      await click('恢复预览（Demo）');
      await page.getByText('Pause：未暂停（演示）', { exact: true }).scrollIntoViewIfNeeded();
      await expect(page.getByText('Pause：未暂停（演示）', { exact: true })).toBeVisible();
      await click('查看记忆样例（Demo）');
      await page
        .getByText('合成摘要：关系 A 曾讨论学习活动。', { exact: true })
        .scrollIntoViewIfNeeded();
      await expect(
        page.getByText('合成摘要：关系 A 曾讨论学习活动。', { exact: true }),
      ).toBeVisible();
      await shot('memory');
      await click('查看撤销预览（Demo）');
      await expect(page.getByRole('button', { name: '正式撤销（尚未开放）' })).toBeDisabled();
      await click('预览删除全部记忆（Demo）');
      await expect(page.getByRole('button', { name: '我已核对范围（仅演示）' })).toBeDisabled();
      await click('删除后保留授权（Demo 选择）');
      await click('我已核对范围（仅演示）');
      await page.getByText(/真实 Challenge、Receipt、operation_key/).scrollIntoViewIfNeeded();
      await expect(page.getByText(/真实 Challenge、Receipt、operation_key/)).toBeVisible();
      await expect(page.getByRole('button', { name: '正式删除（尚未开放）' })).toBeDisabled();
      await shot('delete');
      await click('取消删除预览');
      await click('撤销授权预览（Demo）');
      await click('恢复预览（Demo）');
      await page.getByText('Consent：未授权（演示）', { exact: true }).scrollIntoViewIfNeeded();
      await expect(page.getByText('Consent：未授权（演示）', { exact: true })).toBeVisible();
      await expect(page.getByText('Pause：已暂停（演示）', { exact: true })).toBeVisible();
      await click('返回上一级');
      await expect(page.getByRole('heading', { name: '狗头军师', exact: true })).toBeVisible();
      await noOverflow();
      await page.goto('/import?relationshipId=demo-b');
      await click('体验导入流程（演示数据）');
      await click('下一步');
      await click('我 → self');
      await page.reload();
      await expect(page.getByRole('button', { name: '下一步', exact: true })).toBeDisabled();
      await click('体验导入流程（演示数据）');
      await click('下一步');
      await expect(page.getByText('绑定：unbound', { exact: true })).toHaveCount(3);
      await page.goto('/history?relationshipId=missing');
      await expect(page.getByRole('heading', { name: '关系不可用', exact: true })).toBeVisible();
      await expect(page.getByLabel(/^self · 我：/)).toHaveCount(0);
      expect(errors).toEqual([]);
      expect(requests).toEqual([]);
    });
  }
}
