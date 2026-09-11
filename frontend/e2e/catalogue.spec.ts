/**
 * Categories, the catalogue, suggestions, and the read-first main screen.
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

import {
  API,
  createItem,
  createStore,
  entryFor,
  resetList,
  seededCategory,
  setEntry,
} from './helpers'

test.beforeEach(async ({ request }) => {
  await resetList(request)
})

function itemNames(page: Page) {
  return page.getByTestId('item-name-text')
}

function groupNames(page: Page) {
  return page.getByTestId('group')
}

async function categoryOrder(request: APIRequestContext): Promise<string[]> {
  const all: { id: string }[] = await (await request.get(`${API}/shopping/categories`)).json()
  return all.map((c) => c.id)
}

async function setCategoryOrder(request: APIRequestContext, ids: string[]): Promise<void> {
  await request.put(`${API}/shopping/categories/order`, { data: { ordered_ids: ids } })
}

// ---- 7: routing and the read-first main screen ----

test('the main screen has no entry form; adding is one deliberate step away', async ({
  page,
}) => {
  await page.goto('/')

  await expect(page.getByTestId('item-form')).toHaveCount(0)
  await expect(page.getByTestId('add-button')).toBeVisible()

  await page.getByTestId('add-button').click()
  await expect(page).toHaveURL(/\/add$/)
  await expect(page.getByTestId('item-form')).toBeVisible()
})

test('adding returns to the list; so does cancelling', async ({ page }) => {
  await page.goto('/add')
  await page.getByTestId('item-name').fill('paprika')
  await page.getByTestId('item-submit').click()

  await expect(page).toHaveURL(/\/$/)
  await expect(itemNames(page)).toHaveText(['paprika'])

  await page.getByTestId('add-button').click()
  await page.getByTestId('cancel').click()
  await expect(page).toHaveURL(/\/$/)
})

test('the back gesture leaves /add and returns to the list, not out of the app', async ({
  page,
}) => {
  await page.goto('/')
  await page.getByTestId('add-button').click()
  await expect(page).toHaveURL(/\/add$/)

  await page.goBack()

  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByTestId('add-button')).toBeVisible()
})

test('every route survives a full page reload', async ({ page }) => {
  for (const route of ['/add', '/manage', '/catalogue', '/']) {
    await page.goto(route)
    await page.reload()
    await expect(page.locator('.app')).toBeVisible()
    await expect(page).toHaveURL(new RegExp(`${route.replace('/', '\\/')}$`))
  }
})

// ---- 8: grouping ----

test('the list is grouped by category in the configured order, uncategorised last', async ({
  page,
  request,
}) => {
  const lidl = await createStore(request, 'Lidl')
  const produce = await seededCategory(request, 'Produce')
  const dairy = await seededCategory(request, 'Dairy')

  // A known order, whatever an earlier run left: Produce before Dairy.
  const before = await categoryOrder(request)
  const rest = before.filter((id) => id !== dairy.id && id !== produce.id)
  await setCategoryOrder(request, [produce.id, dairy.id, ...rest])

  for (const name of ['milk', 'apples', 'mystery thing', 'cheese']) {
    await createItem(request, name, [lidl.id])
  }
  await setEntry(request, 'milk', { category_id: dairy.id })
  await setEntry(request, 'cheese', { category_id: dairy.id })
  await setEntry(request, 'apples', { category_id: produce.id })

  await page.goto('/')
  await page.getByTestId('store-chip-Lidl').click()

  // Seeded order is Produce before Dairy; uncategorised comes last.
  await expect(groupNames(page)).toHaveCount(3)
  const groups = await groupNames(page).evaluateAll((els) =>
    els.map((el) => el.getAttribute('data-category')),
  )
  expect(groups).toEqual(['Produce', 'Dairy', 'Uncategorised'])
  await expect(itemNames(page)).toHaveText(['apples', 'cheese', 'milk', 'mystery thing'])

  // Each group shows its icon and name.
  const dairyGroup = page.locator('[data-category="Dairy"]')
  await expect(dairyGroup.locator('.group__icon')).toHaveText(dairy.icon)
  await expect(dairyGroup.locator('.group__title')).toContainText('Dairy')

  await setCategoryOrder(request, before)
})

test('a freshly typed item is visible under Uncategorised, never absent', async ({ page }) => {
  await page.goto('/add')
  await page.getByTestId('item-name').fill('brand new thing')
  await page.getByTestId('item-submit').click()

  await expect(page).toHaveURL(/\/$/)
  const group = page.locator('[data-category="Uncategorised"]')
  await expect(group).toBeVisible()
  await expect(group.getByTestId('item-name-text')).toHaveText(['brand new thing'])
})

test('reordering categories on the manage page reorders the list', async ({ page, request }) => {
  const dairy = await seededCategory(request, 'Dairy')
  const produce = await seededCategory(request, 'Produce')

  // Start from a known order regardless of what an earlier run left behind:
  // Produce immediately before Dairy, at the front.
  const before = await categoryOrder(request)
  const rest = before.filter((id) => id !== dairy.id && id !== produce.id)
  await setCategoryOrder(request, [produce.id, dairy.id, ...rest])

  await createItem(request, 'milk')
  await createItem(request, 'apples')
  await setEntry(request, 'milk', { category_id: dairy.id })
  await setEntry(request, 'apples', { category_id: produce.id })

  await page.goto('/')
  await expect(itemNames(page)).toHaveText(['apples', 'milk'])

  await page.getByTestId('nav-manage').click()
  await page.getByTestId('move-up-Dairy').click()
  await expect(page.getByTestId('move-up-Dairy')).toBeDisabled()

  await page.getByRole('link', { name: 'List' }).click()
  await expect(itemNames(page)).toHaveText(['milk', 'apples'])

  await setCategoryOrder(request, before)
})

// ---- 8: suggestions ----

test('typing offers what was bought before, and adding an unfamiliar name is never blocked', async ({
  page,
  request,
}) => {
  await createItem(request, 'milk')
  await createItem(request, 'mild cheddar')
  await createItem(request, 'bread')

  await page.goto('/add')
  await page.getByTestId('item-name').fill('mil')

  const suggestions = page.getByTestId('suggestions')
  await expect(suggestions).toBeVisible()
  await expect(suggestions.locator('.typeahead__name')).toHaveText(['mild cheddar', 'milk'])

  // Slow the suggestion request right down; the add must not wait for it.
  await page.route('**/api/shopping/catalogue/suggest**', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 3000))
    await route.continue()
  })
  await page.getByTestId('item-name').fill('something never bought')
  await expect(page.getByTestId('item-submit')).toBeEnabled()
  await page.getByTestId('item-submit').click()

  await expect(page).toHaveURL(/\/$/)
  await expect(itemNames(page)).toContainText(['something never bought'])
})

test('choosing a suggestion prefills category and stores; the stores can be changed for one item', async ({
  page,
  request,
}) => {
  const lidl = await createStore(request, 'Lidl')
  const spar = await createStore(request, 'Spar')
  await createStore(request, 'Aldi')
  const household = await seededCategory(request, 'Household')
  const seed = await createItem(request, 'ketchup', [lidl.id, spar.id])
  await setEntry(request, 'ketchup', { category_id: household.id, store_ids: [lidl.id, spar.id] })
  await request.delete(`${API}/shopping/items/${seed.id}`)

  await page.goto('/add')
  await page.getByTestId('item-name').fill('ket')
  await page.getByTestId('suggest-ketchup').click()

  await expect(page.getByTestId('item-name')).toHaveValue('ketchup')
  await expect(page.getByTestId('prefilled-category')).toContainText('Household')
  await expect(page.getByTestId('pick-store-Lidl')).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByTestId('pick-store-Spar')).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByTestId('pick-store-Aldi')).toHaveAttribute('aria-pressed', 'false')

  // This once, get it anywhere.
  await page.getByTestId('pick-store-Lidl').click()
  await page.getByTestId('pick-store-Spar').click()
  await page.getByTestId('item-submit').click()

  await expect(page).toHaveURL(/\/$/)
  await page.getByTestId('store-chip-Aldi').click()
  await expect(itemNames(page)).toHaveText(['ketchup'])
  const householdGroup = page.locator('[data-category="Household"]')
  await expect(householdGroup.getByTestId('item-name-text')).toHaveText(['ketchup'])

  // The entry still remembers Lidl and Spar.
  const entry = await entryFor(request, 'ketchup')
  expect(entry.stores.map((s) => s.name).sort()).toEqual(['Lidl', 'Spar'])
})

// ---- 8: the correct-it-later flow ----

test('type a name in a hurry, categorise it later, and the next add carries the category', async ({
  page,
  request,
}) => {
  const bakery = await seededCategory(request, 'Bakery')

  // In a hurry: just the name.
  await page.goto('/add')
  await page.getByTestId('item-name').fill('sourdough')
  await page.getByTestId('item-submit').click()
  await expect(page.locator('[data-category="Uncategorised"]').getByTestId('item-name-text')).toHaveText(['sourdough'])

  // Later, at home: one correction on the catalogue page.
  await page.getByTestId('nav-catalogue').click()
  await page.getByTestId('category-select-sourdough').selectOption(bakery.id)
  await expect(page.getByTestId('category-select-sourdough')).toHaveValue(bakery.id)

  // The item already on the list regrouped, with no edit to the item.
  await page.getByRole('link', { name: 'List' }).click()
  await expect(page.locator('[data-category="Bakery"]').getByTestId('item-name-text')).toHaveText(['sourdough'])

  // And the next add of that name carries it.
  await page.getByTestId('add-button').click()
  await page.getByTestId('item-name').fill('sour')
  await page.getByTestId('suggest-sourdough').click()
  await expect(page.getByTestId('prefilled-category')).toContainText('Bakery')
})

test('a rename collision offers a merge instead of silently failing', async ({ page, request }) => {
  await createItem(request, 'milk')
  await createItem(request, 'mlik')

  await page.goto('/catalogue')
  await page.getByTestId('rename-mlik').click()
  await page.getByTestId('rename-input-mlik').fill('milk')
  await page.getByTestId('rename-save-mlik').click()

  await expect(page.getByTestId('collision-mlik')).toContainText('already exists')

  page.once('dialog', (dialog) => void dialog.accept())
  await page.getByTestId('merge-mlik').click()

  await expect(page.getByTestId('entry-row-mlik')).toHaveCount(0)
  await expect(page.getByTestId('entry-row-milk')).toBeVisible()
  // Both items now sit under the one entry.
  const entry = await entryFor(request, 'milk')
  const items: { catalogue_entry_id: string }[] = await (
    await request.get(`${API}/shopping/items`)
  ).json()
  expect(items.map((i) => i.catalogue_entry_id)).toEqual([entry.id, entry.id])
})

test('categories can be created with an emoji and colour, and removed', async ({ page }) => {
  await page.goto('/manage')

  await page.getByTestId('category-icon').fill('🧪')
  await page.getByTestId('category-name').fill('E2E Chemicals')
  await page.getByRole('radio', { name: '#7a4cc4' }).click()
  await page.getByTestId('category-submit').click()

  const row = page.getByTestId('category-row-E2E Chemicals')
  await expect(row).toBeVisible()
  await expect(row.locator('.manage-row__swatch')).toHaveText('🧪')

  page.once('dialog', (dialog) => void dialog.accept())
  await row.getByRole('button', { name: 'Remove E2E Chemicals' }).click()
  await expect(row).toHaveCount(0)
})

test.afterAll(async ({ request }) => {
  // Leave the dev database the way the seed made it.
  const all: { id: string; name: string }[] = await (
    await request.get(`${API}/shopping/categories`)
  ).json()
  for (const c of all) {
    if (c.name.startsWith('E2E ')) await request.delete(`${API}/shopping/categories/${c.id}`)
  }
})
