/** Bought items stay visible until cleared. */

import { expect, test, type Page } from '@playwright/test'

import {
  API,
  createItem,
  createStore,
  itemNames,
  pickFirstMember,
  resetList,
  seededCategory,
  setEntry,
  starter,
} from './helpers'

test.beforeEach(async ({ request }) => {
  await resetList(request)
})

function bought(page: Page) {
  return page.locator('[data-category="Bought"]')
}

test('ticking an item moves it below every outstanding item, dimmed, in both views', async ({
  page,
  request,
}) => {
  const lidl = await createStore(request, 'Lidl')
  const dairy = await seededCategory(request, starter.dairy)
  await createItem(request, 'apples', [lidl.id])
  await createItem(request, 'milk', [lidl.id])
  await setEntry(request, 'milk', { category_id: dairy.id })

  await page.goto('/')
  await pickFirstMember(page)
  await page.getByTestId('store-chip-Lidl').click()
  await expect(itemNames(page)).toHaveText(['milk', 'apples'])

  await page.getByTestId('buy-milk').click()

  // Order is now: outstanding (apples), then the bought group (milk).
  await expect(itemNames(page)).toHaveText(['apples', 'milk'])
  const groups = await page.getByTestId('group').evaluateAll((els) => els.map((el) => el.getAttribute('data-category')))
  expect(groups).toEqual(['Uncategorised', 'Bought'])
  await expect(bought(page).locator('.item--bought')).toHaveCount(1)

  // Same arrangement on the full list.
  await page.getByRole('button', { name: 'Everywhere' }).click()
  await expect(itemNames(page)).toHaveText(['apples', 'milk'])
  await expect(bought(page).getByTestId('item-name-text')).toHaveText(['milk'])
})

test('clear bought removes every bought item from every store, and says how many', async ({
  page,
  request,
}) => {
  const lidl = await createStore(request, 'Lidl')
  const spar = await createStore(request, 'Spar')
  await createItem(request, 'lidl thing', [lidl.id])
  await createItem(request, 'spar thing', [spar.id])
  await createItem(request, 'still needed')

  await page.goto('/')
  const member = await pickFirstMember(page)
  for (const name of ['lidl thing', 'spar thing']) {
    const items: { id: string; name: string }[] = await (await request.get(`${API}/shopping/items`)).json()
    const item = items.find((i) => i.name === name)!
    await request.post(`${API}/shopping/items/${item.id}/purchase`, { headers: { 'X-Household-Member': member } })
  }
  await page.reload()

  await page.getByTestId('store-chip-Lidl').click()
  await expect(bought(page).getByTestId('item-name-text')).toHaveText(['lidl thing'])
  await expect(page.getByTestId('clear-bought')).toContainText('1 bought item')

  await page.getByTestId('clear-bought').click()

  await expect(bought(page)).toHaveCount(0)
  await expect(page.getByTestId('clear-bought-banner')).toHaveCount(0)
  // Household-wide: Spar's bought item is gone too.
  await page.getByTestId('store-chip-Spar').click()
  await expect(bought(page)).toHaveCount(0)
  await page.getByRole('button', { name: 'Everywhere' }).click()
  await expect(itemNames(page)).toHaveText(['still needed'])
})

test('nothing to clear means no clear control', async ({ page, request }) => {
  await createItem(request, 'milk')

  await page.goto('/')

  await expect(page.getByTestId('clear-bought')).toHaveCount(0)
})

test('the ketchup scenario: bought in Lidl, shown as bought in Spar, outstanding nowhere', async ({
  page,
  request,
}) => {
  const lidl = await createStore(request, 'Lidl')
  const spar = await createStore(request, 'Spar')
  await createItem(request, 'ketchup xxl', [lidl.id, spar.id])

  await page.goto('/')
  await pickFirstMember(page)
  await page.getByTestId('store-chip-Lidl').click()
  await page.getByTestId('buy-ketchup xxl').click()
  await expect(bought(page).getByTestId('item-name-text')).toHaveText(['ketchup xxl'])

  await page.getByTestId('store-chip-Spar').click()
  await expect(bought(page).getByTestId('item-name-text')).toHaveText(['ketchup xxl'])
  await expect(page.locator('[data-bought="false"]')).toHaveCount(0)
})
