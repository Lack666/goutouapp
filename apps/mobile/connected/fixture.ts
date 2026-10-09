import { test as base } from '@playwright/test';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { resolve } from 'node:path';
interface Backend {
  baseURL: string;
  a: string;
  b: string;
  expired: string;
  counts(): Promise<Record<string, number>>;
}
export const test = base.extend<object, { backend: Backend }>({
  backend: [
    async ({ playwright }, useBackend) => {
      void playwright;
      const child = spawn(
        'uv',
        [
          '--cache-dir',
          '.cache/uv',
          '--no-managed-python',
          'run',
          '--locked',
          'python',
          'apps/server/mobile_connected_fixture.py',
        ],
        {
          cwd: resolve('../..'),
          stdio: ['pipe', 'pipe', 'pipe'],
          env: { ...process.env, PYTHONUTF8: '1', PYTHONUNBUFFERED: '1' },
        },
      );
      // Tokens are read only through this process pipe. Never write fixtures/traces/screenshots.
      child.stderr.resume();
      const lines = createInterface({ input: child.stdout });
      const iterator = lines[Symbol.asyncIterator]();
      const first = await iterator.next();
      if (first.done)
        throw new Error('Real PostgreSQL fixture failed to start; check TEST_DATABASE_URL.');
      const credentials = JSON.parse(first.value) as Omit<Backend, 'counts'>;
      try {
        await useBackend({
          ...credentials,
          counts: async () => {
            child.stdin.write('counts\n');
            const row = await iterator.next();
            if (row.done) throw new Error('Database evidence unavailable');
            return JSON.parse(row.value) as Record<string, number>;
          },
        });
      } finally {
        child.stdin.end('stop\n');
        await new Promise<void>((done, reject) => {
          const timer = setTimeout(() => {
            child.kill();
            reject(new Error('Fixture cleanup timed out'));
          }, 10_000);
          child.once('exit', (code) => {
            clearTimeout(timer);
            if (code === 0) done();
            else reject(new Error('Fixture cleanup failed'));
          });
        });
        lines.close();
      }
    },
    { scope: 'worker', timeout: 60_000 },
  ],
});
export { expect } from '@playwright/test';
