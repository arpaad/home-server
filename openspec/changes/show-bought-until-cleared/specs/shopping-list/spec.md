## ADDED Requirements

### Requirement: Clearing bought items

The system SHALL provide a single action that takes every bought item out of every view. Clearing SHALL mark the items as cleared and SHALL NOT delete them or their purchase records: the records are what a later purchase history attaches to, and the action that tidies the list must not be the action that destroys history. A cleared item SHALL NOT reappear in any view.

The action SHALL be available wherever the list is shown, and SHALL say how many items it will clear.

#### Scenario: Clearing away today's shopping

- **WHEN** the list holds three bought items and two outstanding ones
- **AND** a member clears the bought items
- **THEN** the three bought items no longer appear in any view
- **AND** the two outstanding items are unchanged
- **AND** the three purchases are still recorded

#### Scenario: Clearing is household-wide

- **WHEN** a member clears the bought items while viewing the store Lidl
- **THEN** bought items assigned only to other stores are cleared as well
- **AND** the other member no longer sees any of them

#### Scenario: Nothing to clear

- **WHEN** no item is bought and uncleared
- **THEN** the clear action is not offered, or is offered disabled, and does nothing

## MODIFIED Requirements

### Requirement: Marking an item as bought

When a member marks an item as bought, the system SHALL record which member did so and when. The item SHALL remain visible in every view it appeared in, but SHALL be shown as bought — unmistakably distinct from outstanding items, and grouped after them — until it is cleared. Because an item exists once on the shared list, it SHALL show as bought in every member's view and every store's view at once, so it cannot be bought a second time from another store's view.

#### Scenario: Buying an item marks it bought in every store's view

- **WHEN** an item assigned to both Lidl and Spar is marked as bought by a member shopping in Lidl
- **THEN** the item is shown as bought in the shopping view for Lidl
- **AND** the item is shown as bought in the shopping view for Spar
- **AND** the item is shown as bought for the other member
- **AND** the item is no longer among the outstanding items in any view

#### Scenario: A bought item sits after the outstanding ones

- **WHEN** a member marks one of several items as bought
- **THEN** that item moves to a bought group shown after every outstanding group
- **AND** the outstanding items keep their category grouping and order

#### Scenario: A purchase is attributed

- **WHEN** a member marks an item as bought
- **THEN** the system records that member and the time of the action against that item

### Requirement: Undoing a purchase

The system SHALL allow a member to undo an item marked as bought in error, from the bought item itself. Undoing SHALL return the item to the outstanding list for all members, SHALL leave no purchase recorded against it, and SHALL leave it uncleared.

#### Scenario: Restoring an item marked bought by mistake

- **WHEN** a member undoes the purchase of a bought item
- **THEN** the item is outstanding again and reappears in the shopping views it qualifies for, in its category group
- **AND** no purchase is recorded against the item

#### Scenario: Undo is on the bought item

- **WHEN** a member views a bought item
- **THEN** the same control that marked it bought now undoes it

### Requirement: Store-filtered shopping view

Given a selected store, the system SHALL present exactly those items that are still outstanding, that are available on the current date, and that either have no store assigned or include the selected store.

The view SHALL group those items by category, in the household's configured category order, with items whose catalogue entry has no category shown in a final uncategorised group. Grouping SHALL NOT change which items appear — only how they are arranged.

After the outstanding items, the view SHALL present the bought and uncleared items that either have no store assigned or include the selected store, regardless of their availability date, in a single bought group with the most recently bought first.

#### Scenario: Shopping in one store shows that store's items plus the unrestricted ones

- **WHEN** the list holds "ketchup" assigned to Lidl and Spar, "milk" with no store, and "cat litter" assigned to Aldi
- **AND** a member selects the store Lidl
- **THEN** the view contains "ketchup" and "milk"
- **AND** the view does not contain "cat litter"

#### Scenario: A postponed item is excluded from the store view

- **WHEN** an item is assigned to Lidl but has an availability date in the future
- **AND** a member selects the store Lidl
- **THEN** the view does not contain that item

#### Scenario: A bought item is shown as bought, after the outstanding ones

- **WHEN** an item assigned to Lidl has been marked as bought and not cleared
- **AND** a member selects the store Lidl
- **THEN** the view shows that item in the bought group, after every outstanding item

#### Scenario: A cleared item is not shown

- **WHEN** an item assigned to Lidl has been marked as bought and then cleared
- **AND** a member selects the store Lidl
- **THEN** the view does not contain that item

#### Scenario: A bought item follows its stores

- **WHEN** an item assigned only to Aldi has been marked as bought
- **AND** a member selects the store Lidl
- **THEN** the view does not contain that item, bought or otherwise

#### Scenario: The store view is grouped by category

- **WHEN** a member selects a store and the matching items span several categories
- **THEN** the items are grouped under their categories, in the household's configured order
- **AND** each group shows its category's name, icon and colour

#### Scenario: An uncategorised item is still visible

- **WHEN** a matching item's catalogue entry has no category
- **THEN** the item appears in an uncategorised group rather than being omitted

### Requirement: Full list view

The system SHALL allow a member to view all outstanding items irrespective of store and availability, showing each item's assigned stores and its availability date when it has one, so the household can review and plan the whole list away from any shop.

This view SHALL be grouped by category on the same terms as the store-filtered view, and SHALL present every bought and uncleared item after the outstanding ones on the same terms.

#### Scenario: Reviewing the whole list at home

- **WHEN** a member opens the full list
- **THEN** the view contains outstanding items for every store, including items whose availability date has not yet arrived
- **AND** each item shows its assigned stores and its availability date when it has one
- **AND** the items are grouped by category in the household's configured order

#### Scenario: Reviewing what was bought

- **WHEN** a member opens the full list after a shopping trip
- **THEN** every bought and uncleared item is shown in the bought group, after the outstanding items
