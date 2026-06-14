# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: dashboard.spec.js >> Dashboard >> renders header, stat cards, host stats, and VM table
- Location: e2e/dashboard.spec.js:4:3

# Error details

```
Error: page.goto: net::ERR_ADDRESS_UNREACHABLE at http://192.168.178.101/
Call log:
  - navigating to "http://192.168.178.101/", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | 
  3  | test.describe('Dashboard', () => {
  4  |   test('renders header, stat cards, host stats, and VM table', async ({ page }) => {
> 5  |     await page.goto('/')
     |                ^ Error: page.goto: net::ERR_ADDRESS_UNREACHABLE at http://192.168.178.101/
  6  | 
  7  |     // Page header + New VM affordance
  8  |     await expect(page.getByText('Virtual Machines').first()).toBeVisible()
  9  |     await expect(page.getByRole('button', { name: /New VM/i }).first()).toBeVisible()
  10 | 
  11 |     // Sidebar live host stats
  12 |     await expect(page.getByText('CPU').first()).toBeVisible()
  13 |     await expect(page.getByText('RAM').first()).toBeVisible()
  14 |     await expect(page.getByText('Disk').first()).toBeVisible()
  15 | 
  16 |     // VM table renders rows for the real VMs (sandbox exists on the host),
  17 |     // or an empty state — accept either, but the page must not be blank.
  18 |     const hasSandbox = await page.getByText('sandbox').first().isVisible().catch(() => false)
  19 |     const hasEmpty = await page.getByText(/no virtual machines/i).first().isVisible().catch(() => false)
  20 |     expect(hasSandbox || hasEmpty).toBeTruthy()
  21 |   })
  22 | })
  23 | 
```