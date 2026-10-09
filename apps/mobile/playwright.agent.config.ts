import { defineConfig } from '@playwright/test';
process.env.GOUTOU_AGENT_E2E = '1';
export default defineConfig({
  testDir: './agent-connected',
  outputDir: '../../.cache/phase8c-agent-results',
  reporter: [['list'], ['json', { outputFile: '../../.cache/phase8c-agent-smoke.json' }]],
  workers: 1,
  timeout: 60_000,
  use: {
    baseURL: 'http://localhost:8089',
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
    command: 'pnpm exec expo start --web --port 8089 --localhost --clear',
    url: 'http://localhost:8089',
    reuseExistingServer: false,
    timeout: 120_000,
    env: { CI: '1', EXPO_NO_TELEMETRY: '1', EXPO_PUBLIC_API_BASE_URL: 'http://127.0.0.1:8019' },
  },
});
