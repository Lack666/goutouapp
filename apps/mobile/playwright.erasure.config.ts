import { defineConfig } from '@playwright/test';
process.env.GOUTOU_MEMORY_E2E = '1';
process.env.GOUTOU_IMPORT_E2E = '1';
process.env.GOUTOU_ERASURE_E2E = '1';
export default defineConfig({
  testDir: './erasure-connected',
  outputDir: '../../.cache/phase9f-web-results',
  reporter: [['list']],
  workers: 1,
  timeout: 120_000,
  use: {
    baseURL: 'http://localhost:8091',
    browserName: 'chromium',
    viewport: { width: 412, height: 900 },
    trace: 'off',
    screenshot: 'off',
    video: 'off',
    launchOptions: process.env.PLAYWRIGHT_CHROME_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROME_PATH }
      : {},
  },
  webServer: {
    command: 'pnpm exec expo start --web --port 8091 --localhost --clear',
    url: 'http://localhost:8091',
    reuseExistingServer: false,
    timeout: 120_000,
    env: { CI: '1', EXPO_NO_TELEMETRY: '1', EXPO_PUBLIC_API_BASE_URL: 'http://127.0.0.1:8022' },
  },
});
