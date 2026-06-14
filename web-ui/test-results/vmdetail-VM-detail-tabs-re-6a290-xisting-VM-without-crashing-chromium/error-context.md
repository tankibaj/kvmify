# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: vmdetail.spec.js >> VM detail tabs >> renders all tabs for an existing VM without crashing
- Location: e2e/vmdetail.spec.js:6:3

# Error details

```
Error: page.goto: net::ERR_ADDRESS_UNREACHABLE at http://192.168.178.101/vms/sandbox
Call log:
  - navigating to "http://192.168.178.101/vms/sandbox", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | 
  3  | // Uses the pre-existing 'sandbox' VM on the host. Read-only: no lifecycle,
  4  | // snapshot, resize, or network mutations are submitted.
  5  | test.describe('VM detail tabs', () => {
  6  |   test('renders all tabs for an existing VM without crashing', async ({ page }) => {
> 7  |     await page.goto('/vms/sandbox')
     |                ^ Error: page.goto: net::ERR_ADDRESS_UNREACHABLE at http://192.168.178.101/vms/sandbox
  8  | 
  9  |     // Tab bar
  10 |     for (const tab of ['Overview', 'Console', 'Snapshots', 'Network', 'Resize']) {
  11 |       await expect(page.getByText(tab, { exact: true }).first()).toBeVisible()
  12 |     }
  13 | 
  14 |     // Snapshots tab → Take Snapshot affordance
  15 |     await page.getByText('Snapshots', { exact: true }).first().click()
  16 |     await expect(page.getByRole('button', { name: /Take Snapshot/i }).first()).toBeVisible()
  17 | 
  18 |     // Network tab → restart warning banner
  19 |     await page.getByText('Network', { exact: true }).first().click()
  20 |     await expect(page.getByText(/restart/i).first()).toBeVisible()
  21 | 
  22 |     // Resize tab → stop-required warning
  23 |     await page.getByText('Resize', { exact: true }).first().click()
  24 |     await expect(page.getByText(/stopped/i).first()).toBeVisible()
  25 | 
  26 |     // Console tab renders (may be "connecting"/"unavailable" — must not crash)
  27 |     await page.getByText('Console', { exact: true }).first().click()
  28 |     await expect(page).toHaveURL(/\/vms\/sandbox/)
  29 |   })
  30 | })
  31 | 
```