import { defineConfig, devices } from '@playwright/test';

// Chrome's Local Network Access (LNA) feature blocks automated navigation to
// LAN/private IPs (it manifests as net::ERR_ADDRESS_UNREACHABLE because there's
// no human to approve the prompt). Tell Chromium to treat our target host as a
// public address space so the headless browser can reach the deployed UI.
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://192.168.178.101';
const TARGET_HOST = (() => {
  try { return new URL(BASE_URL).hostname; } catch { return ''; }
})();
const LNA_ARGS = TARGET_HOST
  ? [
      `--ip-address-space-overrides=${TARGET_HOST}:80=public,${TARGET_HOST}:443=public`,
      '--disable-features=LocalNetworkAccessChecks,BlockInsecurePrivateNetworkRequests,PrivateNetworkAccessChecks',
    ]
  : [];

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
    // Grant Chromium's Local Network Access permission so the browser can reach
    // the LAN-hosted UI under automation (otherwise net::ERR_ADDRESS_UNREACHABLE).
    permissions: ['local-network-access'],
    launchOptions: { args: LNA_ARGS },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
