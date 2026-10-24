## Context

The list is grouped in the client (`grouping.ts`) from rows the server hands over in category order, outstanding first and bought last. Every list change is a local-first, replayable mutation (`mutations.ts`) that patches the cached views optimistically. Both shape where the important flag is applied.

## Decisions

### The flag is a column on the item, not on the catalogue entry

Urgency belongs to this week's need, not to the product. Putting it on the entry would make "milk is important" stick to every future milk, the reverse of the category rule (fix once, applies everywhere) — and for the opposite reason. A boolean, `NOT NULL DEFAULT false`, on `shopping_items`.

*Rejected:* a priority number. Nobody asked for degrees, and a scale invites arguing about whether bread is a 2 or a 3.

### The Must-buy group is arranged in the client

`groupByCategory` takes outstanding important items out first, in the order the server sent them, then groups the rest as before. The server's ordering is unchanged.

*Rejected:* ordering `important DESC` in `list_outstanding`. It would work online, but the optimistic edit only patches fields in place, so toggling the flag offline would not move the row until a refetch — and offline there is none. The client already owns arrangement; keeping it there means one place decides it. It also leaves the outstanding query — the correctness core — untouched.

Membership is unaffected: an item appears in exactly the views it appeared in before, once. Only its group changes. Invariant 10 (grouping changes arrangement, never membership) covers it.

### Edits carry the flag like any other field

`important` is optional on edit, absent meaning unchanged, and subject to the same later-edit-wins `edited_at` check. The form always sends it, as it always sends the stores.

### "Add (again)" resets by remounting the form; the status bar lives above it

The page keys the form on a counter and bumps it after an add-again, so every field returns to its initial empty state with no per-field reset code to forget. The status bar belongs to the page, not the form, so it survives the remount.

The bar reads the add's real state from the mutation cache (`useMutationState`, matched on the client-chosen item id), not from a timer:

- in flight or paused → `"milk" — pending, will send when online` (or `sending…`)
- succeeded → `"milk" added`
- refused → the bar disappears; the existing refusal notice says why.

*Rejected:* a fixed "Added!" on submit. Offline, the add is only queued, and invariant 13 forbids showing a pending change as saved.

The bar is a thin strip fixed to the bottom of the screen, `role="status"`, auto-hiding a few seconds after its last change. It does not block the form.

### The filter chip

Label "Anywhere", rendered after the stores. Still the default and still `null`. Moving it to the end puts the stores, which are what one taps in a shop, first.

## Risks

- **Two submit buttons, one Enter key.** Enter submits as plain "Add" (the form's first submit button), keeping today's behaviour for anyone used to it.
