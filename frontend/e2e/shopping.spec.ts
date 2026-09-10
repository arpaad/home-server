import { expect, test } from '@playwright/test'

import { createItem, createStore, resetList } from './helpers'

test.beforeEach(async ({ request }) => {
  await resetList(request)
})

async function pickFirstMember(page: import('@playwright/test').Page) {
  const picker = page.getByTestId('member-picker')
  await expect(picker.locator('option')).not.toHaveCount(1)
  const value = await picker.locator('option').nth(1).getAttribute('value')
  await picker.selectOption(value!)
  return value!
}

function itemNames(page: import('@playwright/test').Page) {
  return page.getByTestId('item-name-text')
}

test('the ketchup case: one item, written once, appears in exactly the right stores', async ({
  page,
  request,
}) => {
  const lidl = await createStore(request, 'Lidl')
  const spar = await createStore(request, 'Spar')
  const aldi = await createStore(request, 'Aldi')

  await createItem(request, 'ketchup', [lidl.id, spar.id])
  await createItem(request, 'milk')
  await createItem(request, 'cat litter', [aldi.id])

  await page.goto('/')

  // Everywhere: the whole outstanding list.
  await expect(itemNames(page)).toHaveText(['cat litter', 'ketchup', 'milk'])

  // In Lidl: ketchup (assigned) and milk (unassigned, so it is everywhere).
  await page.getByTestId('store-chip-Lidl').click()
  await expect(itemNames(page)).toHaveText(['ketchup', 'milk'])
  await expect(page.getByText('cat litter')).toHaveCount(0)

  // In Spar: the same ketchup row, not a second copy of it.
  await page.getByTestId('store-chip-Spar').click()
  await expect(itemNames(page)).toHaveText(['ketchup', 'milk'])

  // In Aldi: its own item plus the unassigned one, but not ketchup.
  await page.getByTestId('store-chip-Aldi').click()
  await expect(itemNames(page)).toHaveText(['cat litter', 'milk'])
})

test('buying in one store removes the item from the other store immediately', async ({
  page,
  request,
}) => {
  const lidl = await createStore(request, 'Lidl')
  const spar = await createStore(request, 'Spar')
  await createItem(request, 'ketchup', [lidl.id, spar.id])

  await page.goto('/')
  await pickFirstMember(page)

  await page.getByTestId('store-chip-Lidl').click()
  await expect(itemNames(page)).toHaveText(['ketchup'])

  await page.getByTestId('buy-ketchup').click()
  await expect(itemNames(page)).toHaveCount(0)

  // The whole point: it is gone from Spar too, without anyone touching Spar.
  await page.getByTestId('store-chip-Spar').click()
  await expect(itemNames(page)).toHaveCount(0)
})

test('undo brings a mistakenly bought item back', async ({ page, request }) => {
  await createItem(request, 'milk')

  await page.goto('/')
  await pickFirstMember(page)

  await page.getByTestId('buy-milk').click()
  await expect(itemNames(page)).toHaveCount(0)

  await page.getByTestId('undo-banner').getByRole('button', { name: 'Undo' }).click()
  await expect(itemNames(page)).toHaveText(['milk'])
})

test('an item that is not due yet is hidden in a shop and shown when planning', async ({
  page,
  request,
}) => {
  const lidl = await createStore(request, 'Lidl')
  await createItem(request, 'sale coffee', [lidl.id], '2099-01-01')
  await createItem(request, 'bread', [lidl.id])

  await page.goto('/')

  // Standing in Lidl: only what is worth buying today.
  await page.getByTestId('store-chip-Lidl').click()
  await expect(itemNames(page)).toHaveText(['bread'])

  // Planning at home: the postponed item is visible, with its date.
  await page.getByRole('button', { name: 'Everywhere' }).click()
  await page.getByTestId('planning-toggle').check()
  await expect(itemNames(page)).toHaveText(['bread', 'sale coffee'])
  await expect(page.getByText(/from Jan/)).toBeVisible()
})

test('a store is chosen from the ones that exist, never typed', async ({ page, request }) => {
  await createStore(request, 'Lidl')
  await page.goto('/')

  const form = page.getByTestId('item-form')

  // The form offers store chips and a deliberate "new store" action, but no
  // free-text store field — a typo must not be able to invent a store.
  await expect(form.getByTestId('pick-store-Lidl')).toBeVisible()
  await expect(form.locator('input[name*="store" i]')).toHaveCount(0)
  await expect(form.getByRole('button', { name: '+ New store' })).toBeVisible()
})

test('adding an item through the form puts it on the shared list', async ({ page }) => {
  await page.goto('/')

  await page.getByTestId('item-name').fill('paprika')
  await page.getByTestId('item-quantity').fill('3')
  await page.getByTestId('item-submit').click()

  await expect(itemNames(page)).toHaveText(['paprika'])
  await expect(page.getByText('3 piece')).toBeVisible()
})

test('a failed request is reported, never shown as saved', async ({ page }) => {
  await page.goto('/')

  // The server is unreachable for this one call. The pattern matches the
  // path the browser actually requests, which is same-origin, not the API's
  // own host.
  await page.route('**/api/shopping/items', (route) =>
    route.request().method() === 'POST' ? route.abort('failed') : route.continue(),
  )

  await page.getByTestId('item-name').fill('should not appear')
  await page.getByTestId('item-submit').click()

  await expect(page.getByTestId('status-banner')).toContainText('was not saved')
  await expect(page.getByText('should not appear')).toHaveCount(0)
})

test('the app is installable: manifest and icons are served', async ({ page, request }) => {
  await page.goto('/')

  const manifestHref = await page.locator('link[rel="manifest"]').getAttribute('href')
  expect(manifestHref).toBeTruthy()

  const manifest = await request.get(new URL(manifestHref!, page.url()).toString())
  expect(manifest.ok()).toBeTruthy()

  const body = await manifest.json()
  expect(body.display).toBe('standalone')
  expect(body.icons.length).toBeGreaterThan(0)
})
