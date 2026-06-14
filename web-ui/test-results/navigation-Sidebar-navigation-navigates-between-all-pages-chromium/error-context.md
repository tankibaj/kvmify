# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: navigation.spec.js >> Sidebar navigation >> navigates between all pages
- Location: e2e/navigation.spec.js:4:3

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
  3  | test.describe('Sidebar navigation', () => {
  4  |   test('navigates between all pages', async ({ page }) => {
> 5  |     await page.goto('/')
     |                ^ Error: page.goto: net::ERR_ADDRESS_UNREACHABLE at http://192.168.178.101/
  6  | 
  7  |     await page.getByRole('link', { name: 'Images' }).click()
  8  |     await expect(page).toHaveURL(/\/images$/)
  9  |     await expect(page.getByText('Ubuntu Base Images').first()).toBeVisible()
  10 | 
  11 |     await page.getByRole('link', { name: 'Pools' }).click()
  12 |     await expect(page).toHaveURL(/\/pools$/)
  13 |     await expect(page.getByText('Storage Pools').first()).toBeVisible()
  14 | 
  15 |     await page.getByRole('link', { name: 'Provision' }).click()
  16 |     await expect(page).toHaveURL(/\/provision$/)
  17 |     await expect(page.getByRole('button', { name: /Provision VM/i }).first()).toBeVisible()
  18 | 
  19 |     await page.getByRole('link', { name: 'Dashboard' }).click()
  20 |     await expect(page).toHaveURL(/\/$/)
  21 |     await expect(page.getByText('Virtual Machines').first()).toBeVisible()
  22 |   })
  23 | })
  24 | 
```