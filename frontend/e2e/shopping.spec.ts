import { expect, test } from '@playwright/test'

import { API, createItem, createStore, itemNames, pickFirstMember, resetList } from './helpers'

test.beforeEach(async ({ request }) => {
  await resetList(request)
})

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

  await expect(itemNames(page)).toHaveText(['cat litter', 'ketchup', 'milk'])

  await page.getByTestId('store-chip-Lidl').click()
  await expect(itemNames(page)).toHaveText(['ketchup', 'milk'])
  await expect(page.getByText('cat litter')).toHaveCount(0)

  await page.getByTestId('store-chip-Spar').click()
  await expect(itemNames(page)).toHaveText(['ketchup', 'milk'])

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
  // Gone from the outstanding items; shown as bought instead.
  await expect(page.locator('[data-bought="false"]')).toHaveCount(0)
  await expect(page.locator('[data-bought="true"]').getByTestId('item-name-text')).toHaveText(['ketchup'])

  // And the same in Spar, without anyone touching Spar.
  await page.getByTestId('store-chip-Spar').click()
  await expect(page.locator('[data-bought="false"]')).toHaveCount(0)
  await expect(page.locator('[data-bought="true"]').getByTestId('item-name-text')).toHaveText(['ketchup'])
})

test('tapping the tick on a bought item undoes it', async ({ page, request }) => {
  await createItem(request, 'milk')

  await page.goto('/')
  await pickFirstMember(page)

  await page.getByTestId('buy-milk').click()
  await expect(page.locator('[data-category="Bought"]').getByTestId('item-name-text')).toHaveText(['milk'])

  await page.getByTestId('undo-milk').click()

  await expect(page.locator('[data-category="Bought"]')).toHaveCount(0)
  await expect(page.locator('[data-category="Uncategorised"]').getByTestId('item-name-text')).toHaveText(['milk'])
})

test('an item that is not due yet is hidden in a shop and shown when planning', async ({
  page,
  request,
}) => {
  const lidl = await createStore(request, 'Lidl')
  await createItem(request, 'sale coffee', [lidl.id], '2099-01-01')
  await createItem(request, 'bread', [lidl.id])

  await page.goto('/')

  await page.getByTestId('store-chip-Lidl').click()
  await expect(itemNames(page)).toHaveText(['bread'])

  await page.getByRole('button', { name: 'Everywhere' }).click()
  await page.getByTestId('planning-toggle').check()
  await expect(itemNames(page)).toHaveText(['bread', 'sale coffee'])
  await expect(page.getByText(/from Jan/)).toBeVisible()
})

test('a change the server never received is shown as pending, never as saved', async ({
  page,
  request,
}) => {
  // Reversed from the first release: the change is saved on this phone and
  // queued, and the app says exactly that — pending, not confirmed.
  await page.goto('/')
  await expect(page.getByTestId('empty')).toBeVisible()
  await page.getByTestId('add-button').click()

  await page.route('**/api/**', (route) =>
    route.request().method() === 'POST' ? route.abort('failed') : route.continue(),
  )
  await page.route('**/health', (route) => route.abort('failed'))

  await page.getByTestId('item-name').fill('not yet on the server')
  await page.getByTestId('item-submit').click()

  await expect(page).toHaveURL(/\/$/)
  const row = page.locator('[data-testid="item"]', { hasText: 'not yet on the server' })
  await expect(row).toBeVisible()
  await expect(row.getByTestId('pending-mark')).toBeVisible()
  await expect(page.getByTestId('offline-banner')).toBeVisible({ timeout: 10_000 })

  const server: { name: string }[] = await (await request.get(`${API}/shopping/items`)).json()
  expect(server.map((i) => i.name)).not.toContain('not yet on the server')
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
