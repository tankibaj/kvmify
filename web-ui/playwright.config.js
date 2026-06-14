import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  retries: 0,
  reporter: 'list',
  // These specs are stateful and run against ONE shared backend/host (they
  // provision VMs, create pools, toggle the default pool). Run serially so they
  // never race each other or overload the host.
  workers: 1,
  fullyParallel: false,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://192.168.178.101',
    headless: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
