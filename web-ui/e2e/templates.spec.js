import { test, expect } from '@playwright/test'

// Snapshot → Template export feature.
// Non-destructive: only reads the Images page templates section and toggles the
// Provision form's image-source selector. No templates are created or deleted,
// and no VM/snapshot is mutated.
test.describe('Templates feature', () => {
  test('Images page renders the VM Templates section', async ({ page }) => {
    await page.goto('/images')
    await expect(page.getByRole('heading', { name: 'VM Templates' })).toBeVisible()
    // The base-images section still renders alongside it.
    await expect(page.getByRole('heading', { name: 'Ubuntu Base Images' })).toBeVisible()
  })

  test('Provision form toggles image source between base image and template', async ({ page }) => {
    await page.goto('/provision')

    // Default source = Ubuntu base image → Ubuntu Version select is shown.
    await expect(page.getByLabel('Ubuntu Version')).toBeVisible()

    // The Image Source selector (located by its option text, since it has no id).
    const sourceSelect = page.locator('select', {
      has: page.locator('option', { hasText: 'From Template' }),
    })
    await expect(sourceSelect).toBeVisible()

    // Switch to "From Template" → Template select replaces Ubuntu Version.
    await sourceSelect.selectOption('template')
    await expect(page.getByLabel('Template', { exact: true })).toBeVisible()
    await expect(page.getByLabel('Ubuntu Version')).toHaveCount(0)

    // Switch back → Ubuntu Version returns.
    await sourceSelect.selectOption('base_image')
    await expect(page.getByLabel('Ubuntu Version')).toBeVisible()
  })
})
