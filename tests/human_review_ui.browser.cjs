// Fixture scores are written only to a disposable copy, never to the user's review packet.
const { chromium, expect } = require('../apps/mobile/node_modules/@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const source = path.join(root, 'evals/agent/results/human-review-15.json');
const hash = () => crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex');
const before = hash();
const fixture = fs.mkdtempSync(path.join(root, '.cache/human-review-browser-'));
const results = path.join(fixture, 'evals/agent/results');
fs.mkdirSync(results, { recursive: true });
for (const name of ['human-review-15.json', 'final-live-safety.json', 'final-live-communication.json', 'final-live-grounding.json']) {
  fs.copyFileSync(path.join(root, 'evals/agent/results', name), path.join(results, name));
}
fs.copyFileSync(path.join(root, 'evals/agent/cases.v1.jsonl'), path.join(fixture, 'evals/agent/cases.v1.jsonl'));
const packet = JSON.parse(fs.readFileSync(source, 'utf8'));
for (const item of packet.items) {
  item.scores = Object.fromEntries(Object.keys(item.scores).map(k => [k, null]));
  item.reviewer = item.reviewed_at = item.reason = null;
}
fs.writeFileSync(path.join(results, 'human-review-15.json'), JSON.stringify(packet));
const code = 'from pathlib import Path; import sys; from scripts.human_review_ui import ReviewStore,make_server; s=make_server(ReviewStore(Path(sys.argv[1])),0); print(s.server_port,flush=True); s.serve_forever()';
const server = spawn(path.join(root, '.venv/Scripts/python.exe'), ['-c', code, fixture], { cwd: root, windowsHide: true });
let browser;
(async () => {
  const port = await new Promise((resolve, reject) => {
    server.stdout.once('data', data => resolve(Number(String(data).trim())));
    server.stderr.once('data', data => reject(Error(String(data))));
    server.once('exit', code => reject(Error('Fixture server exited: ' + code)));
  });
  browser = await chromium.launch(process.env.PLAYWRIGHT_CHROME_PATH
    ? { executablePath: process.env.PLAYWRIGHT_CHROME_PATH, headless: true }
    : { channel: 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 950 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(`http://127.0.0.1:${port}`);
  await expect(page.locator('#caseTitle')).toContainText('communication-01');
  await expect(page.locator('select')).toHaveCount(6);
  for (const select of await page.locator('select').all()) await expect(select).toHaveValue('');
  await expect(page.locator('.dimension li')).toHaveCount(30);
  const action = async selector => {
    const [response] = await Promise.all([
      page.waitForResponse(r => r.request().method() === 'POST'), page.locator(selector).click(),
    ]);
    if (!response.ok()) throw Error(await response.text());
  };
  await page.locator('#reviewer').fill('SYNTHETIC BROWSER TEST ONLY');
  await page.locator('select').first().selectOption('2');
  await action('#draft');
  await page.reload();
  await expect(page.locator('select').first()).toHaveValue('2');
  await expect(page.locator('select').nth(1)).toHaveValue('');
  await action('#next');
  await expect(page.locator('#runStatus')).toContainText('failed');
  await expect(page.locator('#runStatus')).toContainText('structured_output_failure');
  await expect(page.locator('#answer')).toContainText('没有成功的 Agent 回答');
  await action('#previous');
  await expect(page.locator('select').first()).toHaveValue('2');
  await page.screenshot({ path: path.join(root, '.cache/human-review-desktop.png'), fullPage: true });
  for (let i = 0; i < 15; i++) {
    await action(`#caseList button:nth-child(${i + 1})`);
    for (const select of await page.locator('select').all()) await select.selectOption('4');
    await page.locator('#reason').fill('Synthetic browser fixture; not a real human evaluation.');
    await action('#submit');
  }
  await expect(page.locator('#progressLabel')).toContainText('15 / 15');
  await action('#finish');
  await expect(page.locator('#notice')).toContainText('已生成并保存');
  const output = JSON.parse(fs.readFileSync(path.join(results, 'human-review-15.json'), 'utf8'));
  for (let i = 0; i < 15; i++) {
    expect(output.items[i].result).toEqual(packet.items[i].result);
    expect(output.items[i].reviewer).toBe('SYNTHETIC BROWSER TEST ONLY');
    expect(output.items[i].reviewed_at).toBeTruthy();
  }
  expect(fs.readFileSync(path.join(results, 'human-review-summary.md'), 'utf8')).toContain('15/15');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(root, '.cache/human-review-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  expect(errors).toEqual([]);
  expect(hash()).toBe(before);
  console.log('PASS: six empty scores, 30 anchors, failure display, draft/reload/back, 15-case export, reviewer/time, mobile layout; actual review packet unchanged.');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close();
  server.kill();
});
