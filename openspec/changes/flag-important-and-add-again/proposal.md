## Why

Three small frictions from using the list in shops.

- **"Everywhere" reads wrong.** The filter chip means "no store chosen — show the whole list", which is what the add form already calls *anywhere*. Two words for one idea. It also sits first, ahead of the stores, which is where the thumb lands when picking a store.
- **Some things must not be forgotten.** A list of thirty items flattens them all to the same weight; the one thing the trip is actually for gets lost among the nice-to-haves. The household wants to mark an item as *must buy — do not come home without it* and have it impossible to miss.
- **Adding several things is slow.** Every add returns to the list, so writing up a week's shopping is add, +, add, +, … The household wants to add one and land straight back in an empty form, with a small sign that the last one went in.

## What Changes

- **The filter chip is renamed "Anywhere" and moved to the end** of the store chips. It is still the default selection and still means "no filter".
- **An item can be flagged important.** A toggle on the add and edit form. An important, outstanding item is shown in a **"Must buy" group at the very top** of the list, marked with "!", ahead of every category group, in every view it would appear in anyway. Its row carries the "!" mark wherever it is shown, including once bought. This needs one boolean column on the item.
- **"Add (again)"** next to "Add" on the add form. It adds the item exactly as "Add" does, then resets the form empty for the next one instead of returning to the list, and shows a thin, self-dismissing status bar naming the item just added. The bar says *pending* while the add is queued and *added* once the server has it — never "added" for something not yet saved.

### Out of Scope

- **Importance on the catalogue entry.** Whether milk is urgent is about this week, not about milk. The flag is the item's own, and is not remembered for the next time the name is added.
- **Importance changing membership.** An important item assigned only to Lidl still does not appear in Spar's view. Importance arranges; the store and availability rules decide what is shown.
- **Ordering within the Must-buy group** beyond the server's existing order (category, then name).
- **"Add (again)" on the edit form.** Editing is one item by definition.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `shopping-list`: new requirements **Important items** and **Adding several items in a row**, and **The no-store filter is called Anywhere**. Existing requirements are not rewritten: importance is an arrangement on top of the views they define, and leaves their membership exactly as it is.

> **Layering note.** The changes `add-item-catalogue-and-categories`, `offline-first-list` and `show-bought-until-cleared` are not yet archived. This change only adds requirements, so it can be archived in any order relative to them.

## Impact

**Affected code**

- `backend/app/modules/shopping/repository/orm.py` — `shopping_items.important`, boolean, not null, default false.
- `backend/.../domain/item.py`, `mapping.py`, `repository/item_repository.py`, `interfaces.py`, `service/shopping_list_service.py`, `dto/item_dto.py`, `api/routes.py` — carry the flag through create, edit and read.
- `frontend/src/components/StoreFilter.tsx` — rename and move the chip.
- `frontend/src/grouping.ts`, `GroupedList.tsx`, `ItemRow.tsx` — the Must-buy group and the "!" mark.
- `frontend/src/pages/AddPage.tsx` — the important toggle, "Add (again)", and the status bar.
- `frontend/src/api/mutations.ts`, `types.ts` — the flag in optimistic updates.
- New Alembic migration: add the column with `server_default false`. Existing items become not important.

**Data**

- One column, not null, defaulted, no backfill beyond the default. Reversible by dropping it.

**Assumptions recorded**

- The Must-buy group is arranged by the client, as category grouping already is, so an item flagged offline moves to the top at once rather than after the next refetch.
- A bought important item goes to the Bought group like any other; the "!" stays on its row so the end-of-trip review can confirm it was got.
- "Add (again)" keeps nothing from the previous item — not stores, not category, not the important flag. Each item is chosen on its own.
