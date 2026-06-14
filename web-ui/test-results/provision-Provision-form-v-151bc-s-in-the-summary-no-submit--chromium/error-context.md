# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: provision.spec.js >> Provision form >> validates VM name and reflects inputs in the summary (no submit)
- Location: e2e/provision.spec.js:4:3

# Error details

```
Error: page.goto: net::ERR_ADDRESS_UNREACHABLE at http://192.168.178.101/provision
Call log:
  - navigating to "http://192.168.178.101/provision", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | 
  3  | test.describe('Provision form', () => {
  4  |   test('validates VM name and reflects inputs in the summary (no submit)', async ({ page }) => {
> 5  |     await page.goto('/provision')
     |                ^ Error: page.goto: net::ERR_ADDRESS_UNREACHABLE at http://192.168.178.101/provision
  6  | 
  7  |     const nameInput = page.getByPlaceholder('my-web-server')
  8  |     await expect(nameInput).toBeVisible()
  9  | 
  10 |     // Invalid name → submit blocked with a validation error
  11 |     await nameInput.fill('Bad_Name')
  12 |     await page.getByRole('button', { name: /Provision VM/i }).click()
  13 |     await expect(page.getByText(/lowercase letters/i).first()).toBeVisible()
  14 |     // Still on the provision page (no real provisioning kicked off)
  15 |     await expect(page).toHaveURL(/\/provision$/)
  16 | 
  17 |     // Valid name → live summary reflects it
  18 |     await nameInput.fill('e2e-demo')
  19 |     await expect(page.getByText('e2e-demo').first()).toBeVisible()
  20 | 
  21 |     // Sections render
  22 |     await expect(page.getByText('Resources').first()).toBeVisible()
  23 |     await expect(page.getByText('Storage Pool').first()).toBeVisible()
  24 |     await expect(page.getByText('Network').first()).toBeVisible()
  25 |   })
  26 | 
  27 |   test('static IP reveals address fields and blocks empty submit', async ({ page }) => {
  28 |     await page.goto('/provision')
  29 |     await page.getByPlaceholder('my-web-server').fill('e2e-demo')
  30 | 
  31 |     const staticRadio = page.getByText(/Static IP/i).first()
  32 |     if (await staticRadio.isVisible().catch(() => false)) {
  33 |       await staticRadio.click()
  34 |       // An IP address field should appear once Static is chosen
  35 |       await expect(page.getByText(/IP Address/i).first()).toBeVisible()
  36 |       // Empty static IP must block submit
  37 |       await page.getByRole('button', { name: /Provision VM/i }).click()
  38 |       await expect(page).toHaveURL(/\/provision$/)
  39 |     }
  40 |   })
  41 | })
  42 | 
```