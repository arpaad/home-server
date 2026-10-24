/**
 * Must-buy items, adding several in a row, and the Anywhere chip.
 */

import { expect, test, type APIRequestContext } from '@playwright/test'

import { API, createItem, createStore, itemNames, pickFirstMember, resetList } from './helpers'

test.beforeEach(async ({ request }) => {
  await resetList(request)
})

async function createImportant(request: APIRequestContext, name: string, storeIds: string[] = []) {
  const response = await request.post(`${API}/shopping/items`, {
    data: { name, store_ids: storeIds, important: true },
  })
  if (!response.ok()) throw new Error(`could not create item ${name}: ${await response.text()}`)
}

test('Anywhere is the last store chip, and selected to begin with', async ({ page, request }) => {
  await createStore(request, 'Lidl')
  await createStore(request, 'Spar')

  await page.goto('/')

  const chips = page.getByTestId('store-filter').getByRole('button')
  await expect(chips).toHaveText(['Lidl', 'Spar', 'Anywhere'])
  await expect(chips.last()).toHaveAttribute('aria-pressed', 'true')
})

test('an important item is listed first, once, and keeps its mark when bought', async ({
  page,
  request,
}) => {
  await createItem(request, 'bread')
  await createItem(request, 'milk')
  await createImportant(request, 'nappies')

  await page.goto('/')
  await pickFirstMember(page)

  const groups = page.getByTestId('group')
  await expect(groups.first()).toHaveAttribute('data-category', 'Must buy')
  await expect(groups.first().getByTestId('item-name-text')).toHaveText(['nappies'])
  await expect(groups.first().getByTestId('important-mark')).toHaveText('!')
  // Moved, not copied: it is not also in its category group.
  await expect(itemNames(page)).toHaveText(['nappies', 'bread', 'milk'])

  await page.getByTestId('buy-nappies').click()

  await expect(page.locator('[data-category="Must buy"]')).toHaveCount(0)
  const bought = page.locator('[data-category="Bought"]')
  await expect(bought.getByTestId('item-name-text')).toHaveText(['nappies'])
  await expect(bought.getByTestId('important-mark')).toBeVisible()
})

test('an important item for Lidl does not appear in Spar', async ({ page, request }) => {
  const lidl = await createStore(request, 'Lidl')
  await createStore(request, 'Spar')
  await createImportant(request, 'nappies', [lidl.id])
  await createItem(request, 'milk')

  await page.goto('/')
  await page.getByTestId('store-chip-Spar').click()
  await expect(itemNames(page)).toHaveText(['milk'])
  await expect(page.locator('[data-category="Must buy"]')).toHaveCount(0)

  await page.getByTestId('store-chip-Lidl').click()
  await expect(itemNames(page)).toHaveText(['nappies', 'milk'])
})

test('flagging and unflagging an item from the form moves it', async ({ page, request }) => {
  await createItem(request, 'bread')
  await createItem(request, 'milk')

  await page.goto('/')
  await expect(itemNames(page)).toHaveText(['bread', 'milk'])

  await page.getByRole('button', { name: 'Edit milk' }).click()
  await page.getByTestId('item-important').check()
  await page.getByTestId('item-submit').click()

  await expect(page.locator('[data-category="Must buy"]').getByTestId('item-name-text')).toHaveText(['milk'])
  await expect(itemNames(page)).toHaveText(['milk', 'bread'])

  await page.getByRole('button', { name: 'Edit milk' }).click()
  await expect(page.getByTestId('item-important')).toBeChecked()
  await page.getByTestId('item-important').uncheck()
  await page.getByTestId('item-submit').click()

  await expect(page.locator('[data-category="Must buy"]')).toHaveCount(0)
  await expect(itemNames(page)).toHaveText(['bread', 'milk'])
})

test('Add (again) adds, empties the form, and says the item was added', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('add-button').click()

  await page.getByTestId('item-name').fill('milk')
  await page.getByTestId('item-important').check()
  await page.getByTestId('item-submit-again').click()

  // Still on the form, and it is empty — nothing carried over.
  await expect(page.getByTestId('add-page')).toBeVisible()
  await expect(page.getByTestId('item-name')).toHaveValue('')
  await expect(page.getByTestId('item-name')).toBeFocused()
  await expect(page.getByTestId('item-important')).not.toBeChecked()
  await expect(page.getByTestId('added-bar')).toHaveText('“milk” added')

  // Gone by itself.
  await expect(page.getByTestId('added-bar')).toHaveCount(0, { timeout: 6_000 })

  await page.getByTestId('item-name').fill('bread')
  await page.getByTestId('item-submit').click()

  await expect(itemNames(page)).toHaveText(['milk', 'bread'])
  await expect(page.locator('[data-category="Must buy"]').getByTestId('item-name-text')).toHaveText(['milk'])
})

test('offline, Add (again) says pending, not added', async ({ page, context, request }) => {
  await createItem(request, 'bread')
  await page.goto('/')
  await expect(itemNames(page)).toHaveText(['bread'])
  // Let the persister flush, as the offline suite does.
  await page.waitForTimeout(600)

  await context.setOffline(true)
  await page.getByRole('button', { name: 'Anywhere' }).click()
  await expect(page.getByTestId('offline-banner')).toBeVisible({ timeout: 10_000 })

  await page.getByTestId('add-button').click()
  await page.getByTestId('item-name').fill('milk')
  await page.getByTestId('item-submit-again').click()

  await expect(page.getByTestId('item-name')).toHaveValue('')
  const bar = page.getByTestId('added-bar')
  await expect(bar).toHaveAttribute('data-phase', 'paused')
  await expect(bar).toContainText('pending')
  await expect(bar).not.toContainText('added')

  // Back online, the queued add lands and the bar says so.
  await context.setOffline(false)
  await expect(bar).toHaveText('“milk” added', { timeout: 15_000 })
})
