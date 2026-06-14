# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: images.spec.js >> Images page >> lists the three Ubuntu base images with a Sync All action
- Location: e2e/images.spec.js:4:3

# Error details

```
Error: page.goto: net::ERR_ADDRESS_UNREACHABLE at http://192.168.178.101/images
Call log:
  - navigating to "http://192.168.178.101/images", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | 
  3  | test.describe('Images page', () => {
  4  |   test('lists the three Ubuntu base images with a Sync All action', async ({ page }) => {
> 5  |     await page.goto('/images')
     |                ^ Error: page.goto: net::ERR_ADDRESS_UNREACHABLE at http://192.168.178.101/images
  6  | 
  7  |     await expect(page.getByText('Ubuntu Base Images').first()).toBeVisible()
  8  | 
  9  |     // The three LTS versions render
  10 |     await expect(page.getByText(/20\.04/).first()).toBeVisible()
  11 |     await expect(page.getByText(/22\.04/).first()).toBeVisible()
  12 |     await expect(page.getByText(/24\.04/).first()).toBeVisible()
  13 | 
  14 |     // Sync All exists (do NOT click — no real downloads in E2E)
  15 |     await expect(page.getByRole('button', { name: /Sync All/i }).first()).toBeVisible()
  16 |   })
  17 | })
  18 | 
```