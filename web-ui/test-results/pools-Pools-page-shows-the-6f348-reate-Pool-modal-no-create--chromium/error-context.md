# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: pools.spec.js >> Pools page >> shows the default pool and a Create Pool modal (no create)
- Location: e2e/pools.spec.js:4:3

# Error details

```
Error: page.goto: net::ERR_ADDRESS_UNREACHABLE at http://192.168.178.101/pools
Call log:
  - navigating to "http://192.168.178.101/pools", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | 
  3  | test.describe('Pools page', () => {
  4  |   test('shows the default pool and a Create Pool modal (no create)', async ({ page }) => {
> 5  |     await page.goto('/pools')
     |                ^ Error: page.goto: net::ERR_ADDRESS_UNREACHABLE at http://192.168.178.101/pools
  6  | 
  7  |     await expect(page.getByText('Storage Pools').first()).toBeVisible()
  8  |     // The seed pool named "default" renders
  9  |     await expect(page.getByText('default').first()).toBeVisible()
  10 | 
  11 |     // Create Pool opens a modal; close it without submitting
  12 |     const createBtn = page.getByRole('button', { name: /Create Pool/i }).first()
  13 |     await expect(createBtn).toBeVisible()
  14 |     await createBtn.click()
  15 | 
  16 |     // Modal fields render
  17 |     await expect(page.getByText(/Path/i).first()).toBeVisible()
  18 | 
  19 |     // Close without creating (Escape, then ensure no pool was added)
  20 |     await page.keyboard.press('Escape')
  21 |   })
  22 | })
  23 | 
```