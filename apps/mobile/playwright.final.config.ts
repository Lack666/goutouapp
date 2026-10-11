import { defineConfig } from '@playwright/test';
process.env.GOUTOU_FINAL_E2E = '1';
export default defineConfig({
  testDir: './final-connected',
  outputDir: '../../.cache/phase8f-web-results',
  reporter: [['list'], ['json', { outputFile: '../../.cache/phase8f-web-smoke.json' }]],
  workers: 1,
  timeout: 180_000,
  use: {
    baseURL: 'http://localhost:8094',
    browserName: 'chromium',
    viewport: { width: 360, height: 800 },
    trace: 'off',
    screenshot: 'off',
    video: 'off',
    launchOptions: process.env.PLAYWRIGHT_CHROME_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROME_PATH }
      : {},
  },
  webServer: {
    command: 'pnpm exec expo start --web --port 8094 --localhost --clear',
    url: 'http://localhost:8094',
    reuseExistingServer: false,
    timeout: 120_000,
    env: { CI: '1', EXPO_NO_TELEMETRY: '1', EXPO_PUBLIC_API_BASE_URL: 'http://127.0.0.1:8023' },
  },
});
