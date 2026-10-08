import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './smoke',
  outputDir: '../../.cache/phase7b-web-results',
  reporter: [['list'], ['json', { outputFile: '../../.cache/phase7b-web-smoke.json' }]],
  workers: 1,
  use: {
    baseURL: 'http://localhost:8087',
    browserName: 'chromium',
    viewport: { width: 360, height: 800 },
    launchOptions: process.env.PLAYWRIGHT_CHROME_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROME_PATH }
      : {},
  },
  webServer: {
    command: 'pnpm exec expo start --web --port 8087 --localhost',
    url: 'http://localhost:8087',
    reuseExistingServer: false,
    timeout: 120_000,
    env: { CI: '1', EXPO_NO_TELEMETRY: '1' },
  },
});
