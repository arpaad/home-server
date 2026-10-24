/**
 * Rows answer to a tap and a swipe; the list keeps its store; and the same
 * thing is not written twice.
 */

import { expect, test } from '@playwright/test'

import { API, createItem, createStore, itemNames, pickFirstMember, resetList, row, swipe } from './helpers'

test.beforeEach(async ({ request }) => {
  await resetList(request)
})

// ---- returning to the same store view ----

test('adding from Lidl comes back to Lidl', async ({ page, request }) => {
  await createStore(request, 'Lidl')
  await createStore(request, 'Spar')

  await page.goto('/')
  await page.getByTestId('store-chip-Lidl').click()
  await page.getByTestId('add-button').click()
  await page.getByTestId('item-name').fill('bread')
  await page.getByTestId('item-submit').click()

  await expect(page.getByTestId('store-chip-Lidl')).toHaveAttribute('aria-pressed', 'true')
  await expect(itemNames(page)).toHaveText(['bread'])
})

test('backing out of an edit from Spar comes back to Spar, by button and by gesture', async ({
  page,
  request,
}) => {
  await createStore(request, 'Spar')
  await createItem(request, 'milk')

  await page.goto('/')
  await page.getByTestId('store-chip-Spar').click()

  await page.getByTestId('edit-milk').click()
  await page.getByTestId('cancel').click()
  await expect(page.getByTestId('store-chip-Spar')).toHaveAttribute('aria-pressed', 'true')

  await page.getByTestId('edit-milk').click()
  await page.goBack()
  await expect(page.getByTestId('store-chip-Spar')).toHaveAttribute('aria-pressed', 'true')
})

// ---- row gestures ----

test('a long swipe right buys; a long swipe right on a bought row undoes', async ({ page, request }) => {
  await createItem(request, 'milk')
  await page.goto('/')
  await pickFirstMember(page)

  await swipe(page, 'milk', 220)
  await expect(row(page, 'milk')).toHaveAttribute('data-bought', 'true')

  await swipe(page, 'milk', 220)
  await expect(row(page, 'milk')).toHaveAttribute('data-bought', 'false')
})

test('a long swipe left removes the item, without a purchase', async ({ page, request }) => {
  await createItem(request, 'milk')
  await createItem(request, 'bread')
  await page.goto('/')

  await swipe(page, 'milk', -220)

  await expect(itemNames(page)).toHaveText(['bread'])
  await expect(page.locator('[data-category="Bought"]')).toHaveCount(0)
  await expect
    .poll(async () => (await (await request.get(`${API}/shopping/items`)).json()).map((i: { name: string }) => i.name))
    .toEqual(['bread'])
})

test('a short swipe changes nothing and does not open the editor', async ({ page, request }) => {
  await createItem(request, 'milk')
  await page.goto('/')
  await pickFirstMember(page)

  await swipe(page, 'milk', 40)
  await swipe(page, 'milk', -40)

  await expect(page.getByTestId('add-page')).toHaveCount(0)
  await expect(row(page, 'milk')).toHaveAttribute('data-bought', 'false')
  await expect(itemNames(page)).toHaveText(['milk'])
})

test('tapping a row opens it, and Remove on the form removes it', async ({ page, request }) => {
  await createItem(request, 'milk')
  await createItem(request, 'bread')
  await page.goto('/')

  await page.getByTestId('item-name-text').getByText('milk').click()
  await expect(page.getByTestId('item-name')).toHaveValue('milk')

  await page.getByTestId('item-remove').click()
  await expect(itemNames(page)).toHaveText(['bread'])
})

// ---- not twice ----

test('adding milk for Spar when milk for Lidl is on the list offers to edit it', async ({
  page,
  request,
}) => {
  const lidl = await createStore(request, 'Lidl')
  await createStore(request, 'Spar')
  await createItem(request, 'milk', [lidl.id])

  await page.goto('/')
  await page.getByTestId('store-chip-Spar').click()
  await page.getByTestId('add-button').click()
  await page.getByTestId('item-name').fill('Milk')
  await page.getByTestId('pick-store-Spar').click()
  await page.getByTestId('item-submit').click()

  const dialog = page.getByTestId('duplicate-dialog')
  await expect(dialog).toContainText('“milk” is already on the list — at Lidl')

  await page.getByTestId('duplicate-edit').click()
  await expect(page.getByTestId('item-name')).toHaveValue('milk')
  await expect(page.getByTestId('pick-store-Lidl')).toHaveAttribute('aria-pressed', 'true')

  // Still only one milk, and back where we came from.
  await page.getByTestId('cancel').click()
  await expect(page.getByTestId('store-chip-Spar')).toHaveAttribute('aria-pressed', 'true')
  await page.getByTestId('store-chip-anywhere').click()
  await expect(itemNames(page)).toHaveText(['milk'])
})

test('Cancel keeps the form; a bought item does not count', async ({ page, request }) => {
  await createItem(request, 'milk')
  await page.goto('/')
  await pickFirstMember(page)

  await page.getByTestId('add-button').click()
  await page.getByTestId('item-name').fill('milk')
  await page.getByTestId('item-submit').click()
  await page.getByTestId('duplicate-cancel').click()
  await expect(page.getByTestId('duplicate-dialog')).toHaveCount(0)
  await expect(page.getByTestId('item-name')).toHaveValue('milk')
  await page.getByTestId('cancel').click()

  await page.getByTestId('buy-milk').click()
  await page.getByTestId('add-button').click()
  await page.getByTestId('item-name').fill('milk')
  await page.getByTestId('item-submit').click()

  await expect(page.getByTestId('duplicate-dialog')).toHaveCount(0)
  await expect(page.locator('[data-bought="false"]').getByTestId('item-name-text')).toHaveText(['milk'])
  await expect(page.locator('[data-bought="true"]').getByTestId('item-name-text')).toHaveText(['milk'])
})
