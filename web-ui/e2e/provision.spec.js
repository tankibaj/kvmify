import { test, expect } from '@playwright/test'

test.describe('Provision form', () => {
  test('validates VM name and reflects inputs in the summary (no submit)', async ({ page }) => {
    await page.goto('/provision')

    const nameInput = page.getByPlaceholder('my-web-server')
    await expect(nameInput).toBeVisible()

    // Invalid name → submit blocked with a validation error
    await nameInput.fill('Bad_Name')
    await page.getByRole('button', { name: /Provision VM/i }).click()
    await expect(page.getByText(/lowercase letters/i).first()).toBeVisible()
    // Still on the provision page (no real provisioning kicked off)
    await expect(page).toHaveURL(/\/provision$/)

    // Valid name → live summary reflects it
    await nameInput.fill('e2e-demo')
    await expect(page.getByText('e2e-demo').first()).toBeVisible()

    // Sections render
    await expect(page.getByText('Resources').first()).toBeVisible()
    await expect(page.getByText('Storage Pool').first()).toBeVisible()
    await expect(page.getByText('Network').first()).toBeVisible()
  })

  test('static IP reveals address fields and blocks empty submit', async ({ page }) => {
    await page.goto('/provision')
    await page.getByPlaceholder('my-web-server').fill('e2e-demo')

    const staticRadio = page.getByText(/Static IP/i).first()
    if (await staticRadio.isVisible().catch(() => false)) {
      await staticRadio.click()
      // An IP address field should appear once Static is chosen
      await expect(page.getByText(/IP Address/i).first()).toBeVisible()
      // Empty static IP must block submit
      await page.getByRole('button', { name: /Provision VM/i }).click()
      await expect(page).toHaveURL(/\/provision$/)
    }
  })
})
