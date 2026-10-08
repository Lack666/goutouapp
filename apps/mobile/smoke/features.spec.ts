import { test, expect } from '@playwright/test';

for (const mode of ['浅色', '深色']) {
  for (const width of [320, 360, 412]) {
    test(`Chat and Relationship local flow ${mode} ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 });
      const errors: string[] = [];
      const businessRequests: string[] = [];
      page.on('pageerror', (error) => errors.push(error.message));
      page.on('request', (request) => {
        const url = request.url();
        if (
          (!url.startsWith('http://localhost:8087') && !url.startsWith('data:')) ||
          /\/api\/|\/agent\/|\/auth\/|\/memory\//.test(url)
        )
          businessRequests.push(url);
      });
      const noOverflow = async () => {
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
          true,
        );
        const composer = await page.getByLabel('本地预览消息输入').boundingBox();
        if (composer) expect(composer.x + composer.width).toBeLessThanOrEqual(width);
      };
      await page.goto('/');
      await page.getByRole('button', { name: '进入设置' }).click();
      await page.getByRole('button', { name: mode, exact: true }).click();
      await page.getByRole('button', { name: '返回上一级' }).click();
      await page.getByRole('button', { name: '开始对话', exact: true }).click();
      const input = page.getByLabel('本地预览消息输入');
      const add = page.getByRole('button', { name: '添加到本地预览', exact: true });
      await expect(add).toBeDisabled();
      await input.fill('合成清空检查');
      await page.getByRole('button', { name: '清空', exact: true }).click();
      await expect(input).toHaveValue('');
      const text = '匿名合成问题🌱\n\n' + '长中文文本，应该安全显示并可以滚动。'.repeat(28);
      await input.fill(text);
      await noOverflow();
      await add.click();
      await expect(input).toHaveValue('');
      await expect(page.getByText('仅在本地预览，尚未发送给 AI', { exact: true })).toBeVisible();
      await expect(page.getByLabel(/^助手（预置示例）：/)).toHaveCount(0);
      await input.fill('最后一条合成消息 🌱');
      await add.click();
      const last = page.getByLabel('你：最后一条合成消息 🌱', { exact: true });
      await expect(last).toBeVisible();
      await expect
        .poll(async () => {
          const bubble = await last.boundingBox();
          const composer = await input.boundingBox();
          return bubble !== null && composer !== null && bubble.y + bubble.height <= composer.y;
        })
        .toBe(true);
      await noOverflow();
      await page.screenshot({
        path: `../../.cache/phase7b-chat-${mode === '浅色' ? 'light' : 'dark'}-${width}.png`,
      });
      await page.getByLabel(`你：${text}`, { exact: true }).scrollIntoViewIfNeeded();
      await expect(page.getByLabel(`你：${text}`, { exact: true })).toBeVisible();
      await page.getByRole('button', { name: '演示状态预览', exact: true }).click();
      for (const label of [
        '加载状态',
        '进度状态',
        '未连接状态',
        '待确认状态',
        '错误状态',
        '结果状态',
      ]) {
        await page.getByRole('button', { name: label, exact: true }).click();
        if (label === '加载状态') await expect(input).not.toBeEditable();
        if (label === '待确认状态')
          await expect(page.getByRole('button', { name: '确认执行（尚未开放）' })).toBeDisabled();
        if (label === '错误状态') {
          await page.getByRole('alert').scrollIntoViewIfNeeded();
          await expect(page.getByRole('alert')).toBeVisible();
          await page.getByRole('button', { name: '重试', exact: true }).click();
          await expect(page.getByRole('alert')).toHaveCount(0);
        }
        if (label === '结果状态') {
          await page
            .getByRole('heading', { name: '如何区分信息 · 合成示例' })
            .scrollIntoViewIfNeeded();
          await expect(page.getByText(/事实：合成场景/)).toBeVisible();
          await expect(page.getByText(/推测：双方可能/)).toBeVisible();
          await expect(page.getByText(/尚不确定：对方/)).toBeVisible();
        }
      }
      await page.getByRole('button', { name: '空状态', exact: true }).click();
      await page.getByRole('button', { name: '替换为合成对话示例', exact: true }).click();
      await page.getByLabel(/^助手（预置示例）：/).scrollIntoViewIfNeeded();
      await expect(page.getByLabel(/^助手（预置示例）：/)).toBeVisible();
      await page.getByRole('button', { name: '返回上一级' }).click();
      await page.getByRole('button', { name: '进入关系资料' }).click();
      await expect(page.getByText('显示昵称：对象 A（合成）', { exact: true })).toBeVisible();
      await page.getByRole('button', { name: '选择关系 B · 待补充' }).click();
      await expect(page.getByText('显示昵称：未提供', { exact: true })).toBeVisible();
      await expect(page.getByText('显示昵称：对象 A（合成）', { exact: true })).toHaveCount(0);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      );
      await page.screenshot({
        path: `../../.cache/phase7b-relationship-${mode === '浅色' ? 'light' : 'dark'}-${width}.png`,
      });
      await page.getByRole('button', { name: '前往本地对话预览' }).click();
      await expect(page).toHaveURL(/chat\?relationshipId=demo-b$/);
      await expect(page.getByText('关系 B · 待补充', { exact: true }).last()).toBeVisible();
      await expect(page.getByRole('heading', { name: '还没有对话', exact: true })).toBeVisible();
      await page.getByRole('button', { name: '返回上一级' }).click();
      await expect(page).toHaveURL(/relationship$/);
      await expect(page.getByRole('button', { name: '选择关系 B · 待补充' })).toHaveAttribute(
        'aria-pressed',
        'true',
      );
      await page.getByRole('button', { name: '前往导入与分析（尚未接入）' }).click();
      await expect(page.getByRole('button', { name: '选择文件（尚未开放）' })).toBeDisabled();
      await page.getByRole('button', { name: '返回上一级' }).click();
      await page.reload();
      await expect(page.getByRole('button', { name: '选择关系 A · 同学' })).toHaveAttribute(
        'aria-pressed',
        'true',
      );
      expect(errors).toEqual([]);
      expect(businessRequests).toEqual([]);
    });
  }
}
