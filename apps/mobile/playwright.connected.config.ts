import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './connected',
  outputDir: '../../.cache/phase8b-connected-results',
  reporter: [['list'], ['json', { outputFile: '../../.cache/phase8b-connected-smoke.json' }]],
  workers: 1,
  timeout: 60_000,
  use: {
    baseURL: 'http://localhost:8088',
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
    command: 'pnpm exec expo start --web --port 8088 --localhost --clear',
    url: 'http://localhost:8088',
    reuseExistingServer: false,
    timeout: 120_000,
    env: { CI: '1', EXPO_NO_TELEMETRY: '1', EXPO_PUBLIC_API_BASE_URL: 'http://127.0.0.1:8018' },
  },
});
