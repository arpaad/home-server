/**
 * The list works without the server, and is honest about it.
 *
 * Every scenario here drives a real browser with the network cut
 * (`context.setOffline`) against the real API, because "reachable" is
 * decided by trying — and the queue draining on reconnect is the whole
 * point.
 */

import { expect, test, type BrowserContext, type Page } from '@playwright/test'

import {
  API,
  createItem,
  createStore,
  itemNames,
  pickFirstMember,
  resetList,
  seededCategory,
  starter,
} from './helpers'

test.beforeEach(async ({ request }) => {
  await resetList(request)
})

/** Wait until the app itself has noticed the server is back. */
async function untilSynced(page: Page) {
  await expect(page.getByTestId('offline-banner')).toHaveCount(0, { timeout: 15_000 })
  await expect(page.getByTestId('pending-mark')).toHaveCount(0, { timeout: 15_000 })
}

/** Let the persister flush before anything destructive like a reload. */
async function settle(page: Page) {
  await page.waitForTimeout(600)
}

async function goOffline(context: BrowserContext, page: Page) {
  await context.setOffline(true)
  // The app notices on its next request; provoke one.
  await page.getByRole('button', { name: 'Everywhere' }).click()
  await expect(page.getByTestId('offline-banner')).toBeVisible({ timeout: 10_000 })
}

// ---- 2: the local copy ----

test('the list is still there after going offline and reloading', async ({ page, context, request }) => {
  await createItem(request, 'milk')
  await createItem(request, 'bread')
  await page.goto('/')
  await expect(itemNames(page)).toHaveText(['bread', 'milk'])
  await settle(page)

  await context.setOffline(true)
  await page.reload()

  await expect(itemNames(page)).toHaveText(['bread', 'milk'])
  await expect(page.getByTestId('offline-banner')).toBeVisible()
  await expect(page.getByTestId('last-confirmed')).not.toBeEmpty()
})

test('a phone with no copy of the list says so, rather than showing an empty list', async ({
  page,
  context,
  request,
}) => {
  // The app shell has been installed (a previous visit), but the copy of
  // the data is gone — expired, or cleared. Not an empty list: an absent one.
  await createItem(request, 'milk')
  await page.goto('/')
  await expect(itemNames(page)).toHaveText(['milk'])
  await page.waitForFunction(() => navigator.serviceWorker?.controller !== null, null, { timeout: 15_000 }).catch(() => undefined)
  await page.evaluate(() => new Promise<void>((done) => { const r = indexedDB.deleteDatabase('keyval-store'); r.onsuccess = () => done(); r.onerror = () => done(); r.onblocked = () => done() }))

  await context.setOffline(true)
  await page.reload()

  await expect(page.getByTestId('nothing-yet')).toBeVisible({ timeout: 15_000 })
  await expect(page.getByTestId('empty')).toHaveCount(0)
  await expect(itemNames(page)).toHaveCount(0)
})

test('offline is decided by a failed request, and online by a successful one — no browser event', async ({
  page,
  request,
}) => {
  await createItem(request, 'milk')
  await page.goto('/')
  await expect(itemNames(page)).toHaveText(['milk'])

  // Block the API without touching navigator.onLine.
  await page.route('**/api/**', (route) => route.abort('failed'))
  await page.route('**/health', (route) => route.abort('failed'))
  // Provoke a request: a new query key, so the app has to try. That view has
  // no copy, so it says "nothing to show yet"; back on the cached view the
  // offline banner shows with the last-confirmed time.
  await page.getByTestId('planning-toggle').check()
  await expect(page.getByTestId('nothing-yet')).toBeVisible({ timeout: 10_000 })
  await page.getByTestId('planning-toggle').uncheck()
  await expect(page.getByTestId('offline-banner')).toBeVisible({ timeout: 10_000 })
  await expect(itemNames(page)).toHaveText(['milk'])

  await page.unroute('**/api/**')
  await page.unroute('**/health')
  // The probe brings it back within its interval, with no online event.
  await expect(page.getByTestId('offline-banner')).toHaveCount(0, { timeout: 15_000 })
})

test('suggestions, stores and categories still work offline', async ({ page, context, request }) => {
  await createStore(request, 'Lidl')
  await createItem(request, 'milk')
  // The list page keeps the catalogue, stores and categories warm; no need
  // to have visited the catalogue page.
  await page.goto('/')
  await expect(itemNames(page)).toHaveText(['milk'])
  await settle(page)

  await goOffline(context, page)
  await page.getByTestId('add-button').click()
  await page.getByTestId('item-name').fill('mi')

  await expect(page.getByTestId('suggest-milk')).toBeVisible()
  await expect(page.getByTestId('pick-store-Lidl')).toBeVisible()
  await expect(page.getByTestId('item-category').locator('option')).not.toHaveCount(1)
})

// ---- 3: local-first writes ----

test('buying offline moves the item at once, and is sent after reconnecting', async ({
  page,
  context,
  request,
}) => {
  await createItem(request, 'milk')
  await page.goto('/')
  await pickFirstMember(page)
  await expect(itemNames(page)).toHaveText(['milk'])

  await goOffline(context, page)
  await page.getByTestId('buy-milk').click()

  await expect(page.locator('[data-category="Bought"]').getByTestId('item-name-text')).toHaveText(['milk'])
  await expect(page.getByTestId('pending-mark')).toHaveCount(1)
  const before: { purchase: unknown }[] = await (await request.get(`${API}/shopping/items`)).json()
  expect(before[0]?.purchase).toBeNull()

  await context.setOffline(false)
  await untilSynced(page)

  const after: { purchase: unknown }[] = await (await request.get(`${API}/shopping/items`)).json()
  expect(after[0]?.purchase).not.toBeNull()
})

test('an item added offline can be bought offline, and lands once on the server', async ({
  page,
  context,
  request,
}) => {
  await createItem(request, 'placeholder')
  await page.goto('/')
  await pickFirstMember(page)
  await expect(itemNames(page)).toHaveText(['placeholder'])

  await goOffline(context, page)
  await page.getByTestId('add-button').click()
  await page.getByTestId('item-name').fill('ketchup xxl')
  await page.getByTestId('item-submit').click()
  await expect(itemNames(page)).toContainText(['ketchup xxl'])
  await page.getByTestId('buy-ketchup xxl').click()
  await expect(page.locator('[data-category="Bought"]').getByTestId('item-name-text')).toHaveText(['ketchup xxl'])

  await context.setOffline(false)
  await untilSynced(page)

  const server: { name: string; purchase: unknown }[] = await (
    await request.get(`${API}/shopping/items`)
  ).json()
  const ketchups = server.filter((i) => i.name === 'ketchup xxl')
  expect(ketchups).toHaveLength(1)
  expect(ketchups[0]?.purchase).not.toBeNull()
})

test('changes made offline survive closing the app and are sent in order on reopening', async ({
  page,
  context,
  request,
}) => {
  await createItem(request, 'milk')
  await page.goto('/')
  await pickFirstMember(page)
  await expect(itemNames(page)).toHaveText(['milk'])

  await goOffline(context, page)
  await page.getByTestId('add-button').click()
  await page.getByTestId('item-name').fill('apples')
  await page.getByTestId('item-submit').click()
  await expect(itemNames(page)).toContainText(['apples'])
  await page.getByTestId('buy-apples').click()
  await expect(page.locator('[data-category="Bought"]').getByTestId('item-name-text')).toHaveText(['apples'])
  await settle(page)

  // "Close the app": a fresh page, network back.
  await page.close()
  await context.setOffline(false)
  const reopened = await context.newPage()
  await reopened.goto('/')
  await untilSynced(reopened)

  const server: { name: string; purchase: unknown }[] = await (
    await request.get(`${API}/shopping/items`)
  ).json()
  const apples = server.find((i) => i.name === 'apples')
  expect(apples).toBeDefined()
  expect(apples?.purchase).not.toBeNull() // the buy came after the add, and both landed
})

test('later edit wins: the 10:00 edit does not overwrite the 10:05 one', async ({
  browser,
  request,
}) => {
  const item = await createItem(request, 'milk')

  // Phone A goes offline and edits at "10:00".
  const a = await browser.newContext()
  const pageA = await a.newPage()
  await pageA.goto('/')
  await expect(itemNames(pageA)).toHaveText(['milk'])
  await settle(pageA)
  await a.setOffline(true)
  await pageA.getByRole('button', { name: 'Everywhere' }).click()
  await expect(pageA.getByTestId('offline-banner')).toBeVisible({ timeout: 10_000 })
  await pageA.clock.setFixedTime(new Date('2026-09-11T10:00:00+02:00'))
  await pageA.goto(`/add?edit=${item.id}`)
  await pageA.getByTestId('item-quantity').fill('2')
  await pageA.getByTestId('item-submit').click()
  await settle(pageA)

  // Phone B, online, edits at "10:05".
  const b = await browser.newContext()
  const pageB = await b.newPage()
  await pageB.clock.setFixedTime(new Date('2026-09-11T10:05:00+02:00'))
  await pageB.goto(`/add?edit=${item.id}`)
  await pageB.getByTestId('item-quantity').fill('3')
  await pageB.getByTestId('item-submit').click()
  await expect(pageB).toHaveURL(/\/$/)
  // The server is the arbiter here; the list catches up on its own.
  await expect
    .poll(async () => ((await (await request.get(`${API}/shopping/items`)).json()) as { quantity: number }[])[0]?.quantity)
    .toBe(3)
  await expect(pageB.getByText('3 piece')).toBeVisible()

  // Phone A reconnects at "11:00"; its older edit must not win.
  await a.setOffline(false)
  await untilSynced(pageA)

  const server: { quantity: number }[] = await (await request.get(`${API}/shopping/items`)).json()
  expect(server[0]?.quantity).toBe(3)
  await a.close()
  await b.close()
})

// ---- 4: honesty ----

test('a refused change is dropped and reported, and nothing stays pending', async ({
  page,
  context,
  request,
}) => {
  const aldi = await createStore(request, 'Aldi')
  const item = await createItem(request, 'cat litter')
  await page.goto('/')
  await expect(itemNames(page)).toHaveText(['cat litter'])
  await settle(page)

  await goOffline(context, page)
  await page.goto(`/add?edit=${item.id}`)
  await page.getByTestId('pick-store-Aldi').click()
  await page.getByTestId('item-submit').click()
  await expect(page.getByTestId('pending-mark')).toHaveCount(1)

  // Meanwhile the other phone deletes Aldi.
  await request.delete(`${API}/shopping/stores/${aldi.id}`)

  await context.setOffline(false)
  await expect(page.getByTestId('sync-notice')).toBeVisible({ timeout: 15_000 })
  await expect(page.getByTestId('sync-notice')).toContainText('cat litter')
  await expect(page.getByTestId('sync-notice')).toContainText('no store')
  await expect(page.getByTestId('pending-mark')).toHaveCount(0)
  // The list shows the server's state: no store on the item.
  const server: { stores: unknown[] }[] = await (await request.get(`${API}/shopping/items`)).json()
  expect(server[0]?.stores).toEqual([])

  await page.getByTestId('sync-notice').getByRole('button', { name: 'Dismiss' }).click()
  await expect(page.getByTestId('sync-notice')).toHaveCount(0)
})

test('a temporary failure is retried silently, not dropped', async ({ page, request }) => {
  await createItem(request, 'milk')
  await page.goto('/')
  await pickFirstMember(page)
  await expect(itemNames(page)).toHaveText(['milk'])

  let failures = 0
  await page.route('**/api/shopping/items/*/purchase', async (route) => {
    if (route.request().method() === 'POST' && failures < 2) {
      failures += 1
      await route.fulfill({ status: 503, body: 'try later' })
      return
    }
    await route.continue()
  })

  await page.getByTestId('buy-milk').click()
  await expect(page.locator('[data-category="Bought"]').getByTestId('item-name-text')).toHaveText(['milk'])

  await expect(page.getByTestId('pending-mark')).toHaveCount(0, { timeout: 20_000 })
  await expect(page.getByTestId('sync-notice')).toHaveCount(0)
  expect(failures).toBe(2)
  const server: { purchase: unknown }[] = await (await request.get(`${API}/shopping/items`)).json()
  expect(server[0]?.purchase).not.toBeNull()
})

test('management pages read offline but refuse to change anything', async ({
  page,
  context,
  request,
}) => {
  await seededCategory(request, starter.dairy)
  await page.goto('/manage')
  await expect(page.getByTestId(`category-row-${starter.dairy}`)).toBeVisible()
  await settle(page)

  await context.setOffline(true)
  await page.reload()

  await expect(page.getByTestId(`category-row-${starter.dairy}`)).toBeVisible()
  await expect(page.getByTestId('offline-note')).toContainText('Cannot reach the server')
  // Playwright only calls form controls disabled, so assert on one inside
  // the guard rather than on the fieldset itself.
  await expect(page.getByTestId('category-name')).toBeDisabled()
  await expect(page.getByTestId('new-store-name')).toBeDisabled()
})

// ---- 5: the worker never serves API data ----

test('with the network blocked, an API request fails rather than being served by the worker', async ({
  page,
  context,
  request,
}) => {
  await createItem(request, 'milk')
  await page.goto('/')
  await expect(itemNames(page)).toHaveText(['milk'])
  // Give the service worker a chance to install and take control.
  await page.waitForFunction(() => navigator.serviceWorker?.controller !== null, null, { timeout: 15_000 }).catch(() => undefined)

  await context.setOffline(true)
  const outcome = await page.evaluate(async () => {
    try {
      const r = await fetch('/api/shopping/items')
      return `served: ${r.status}`
    } catch {
      return 'failed'
    }
  })

  expect(outcome).toBe('failed')
})
