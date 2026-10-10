import { defineConfig } from '@playwright/test';
process.env.GOUTOU_IMPORT_E2E = '1';
export default defineConfig({
  testDir: './import-connected',
  outputDir: '../../.cache/phase8d-import-results',
  reporter: [['list'], ['json', { outputFile: '../../.cache/phase8d-import-smoke.json' }]],
  workers: 1,
  timeout: 90_000,
  use: {
    baseURL: 'http://localhost:8090',
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
    command: 'pnpm exec expo start --web --port 8090 --localhost --clear',
    url: 'http://localhost:8090',
    reuseExistingServer: false,
    timeout: 120_000,
    env: { CI: '1', EXPO_NO_TELEMETRY: '1', EXPO_PUBLIC_API_BASE_URL: 'http://127.0.0.1:8020' },
  },
});
