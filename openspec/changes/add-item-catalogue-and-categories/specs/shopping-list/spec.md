## ADDED Requirements

### Requirement: An item's category comes from its catalogue entry

An item SHALL take its category from the catalogue entry it refers to, rather than holding a category of its own. Changing that entry's category SHALL therefore change how every item referring to it is grouped, including items already on the list.

This is what makes "fix it once" mean once: a member who miscategorises something corrects it in one place and never meets the mistake again.

#### Scenario: Correcting a category regroups the current list

- **WHEN** the list holds an item "sourdough" whose catalogue entry is uncategorised
- **AND** a member sets that entry's category to Bakery
- **THEN** the item appears under Bakery in the list, without being re-added or edited

#### Scenario: An item whose entry has no category is still shown

- **WHEN** an item's catalogue entry has no category
- **THEN** the item appears in the list under the uncategorised group

### Requirement: The main screen is for taking things off the list

The main screen SHALL present the list and the store filter, and SHALL NOT present an item entry form. Adding SHALL be reached deliberately, from a control that opens a separate view for it.

The screen used while walking around a shop is used to remove things, not add them. An entry form sitting beneath rows that are themselves tap targets is a mis-tap risk exactly when a member has one hand full.

#### Scenario: Arriving at the list

- **WHEN** a member opens the app
- **THEN** the list and the store filter are shown
- **AND** no item entry form is present on that screen

#### Scenario: Adding is one deliberate step away

- **WHEN** a member activates the add control
- **THEN** a separate view for adding an item is presented
- **AND** on adding, or on cancelling, the member is returned to the list

### Requirement: Managing stores, categories and the catalogue

The system SHALL provide views for managing stores, categories and catalogue entries, separate from the shopping views. These are for tidying up at home; the shopping views SHALL NOT require any of this to be done first.

#### Scenario: Tidying up away from a shop

- **WHEN** a member opens the management views
- **THEN** they can add, edit and remove stores and categories, and correct catalogue entries

#### Scenario: Shopping never depends on tidying first

- **WHEN** a member has never opened the management views
- **THEN** they can still add items, filter by store and mark things bought

## MODIFIED Requirements

### Requirement: Adding an item

The system SHALL allow a member to add an item identified by a name, with a quantity and a unit of measure. The name MUST be non-empty. The quantity MUST be greater than zero. When quantity and unit are not supplied, the system SHALL default them to a quantity of one piece.

Every added item SHALL be linked to a catalogue entry matching its name, creating that entry when none exists. The member SHALL NOT be required to choose or create an entry: adding an item by typing a name remains a single action.

#### Scenario: Adding an item with only a name

- **WHEN** a member adds an item named "ketchup" without specifying anything else
- **THEN** the item is created with a quantity of one piece, with no stores and no availability date
- **AND** it is linked to the catalogue entry for "ketchup", which is created if it did not exist

#### Scenario: An empty name is rejected

- **WHEN** a member submits an item whose name is empty or contains only whitespace
- **THEN** the system rejects the request with a validation error
- **AND** no item is created
- **AND** no catalogue entry is created

#### Scenario: A non-positive quantity is rejected

- **WHEN** a member submits an item with a quantity of zero or less
- **THEN** the system rejects the request with a validation error
- **AND** no item is created
- **AND** no catalogue entry is created

#### Scenario: Choosing a category while adding

- **WHEN** a member adds "ketchup" and chooses the category Household
- **THEN** the catalogue entry for "ketchup" is categorised as Household
- **AND** the new item, and every other item named "ketchup" on the list, appears under Household

### Requirement: Editing an item

The system SHALL allow a member to change an outstanding item's name, quantity, unit, assigned stores and availability date. Changes SHALL apply to the single shared item and SHALL therefore be visible to every member.

A member MAY also choose a category while editing. Because an item's category is its catalogue entry's, that choice SHALL be recorded on the entry and SHALL therefore apply to every item of that name; the system SHALL make this visible at the point of choosing, so a member is not surprised by other items moving.

#### Scenario: Correcting which stores an item belongs to

- **WHEN** a member changes an item's stores from "Lidl" to "Lidl" and "Spar"
- **THEN** the item subsequently appears in the shopping views for both stores

#### Scenario: An edit is visible to the other member

- **WHEN** one member changes an item's quantity
- **THEN** the other member sees the updated quantity on the same item

#### Scenario: Choosing a category while editing applies to the entry

- **WHEN** a member edits one "milk" item and chooses the category Dairy
- **THEN** the catalogue entry for "milk" is categorised as Dairy
- **AND** every "milk" item on the list appears under Dairy

### Requirement: Store-filtered shopping view

Given a selected store, the system SHALL present exactly those items that are still outstanding, that are available on the current date, and that either have no store assigned or include the selected store.

The view SHALL group those items by category, in the household's configured category order, with items whose catalogue entry has no category shown in a final uncategorised group. Grouping SHALL NOT change which items appear — only how they are arranged.

#### Scenario: Shopping in one store shows that store's items plus the unrestricted ones

- **WHEN** the list holds "ketchup" assigned to Lidl and Spar, "milk" with no store, and "cat litter" assigned to Aldi
- **AND** a member selects the store Lidl
- **THEN** the view contains "ketchup" and "milk"
- **AND** the view does not contain "cat litter"

#### Scenario: A postponed item is excluded from the store view

- **WHEN** an item is assigned to Lidl but has an availability date in the future
- **AND** a member selects the store Lidl
- **THEN** the view does not contain that item

#### Scenario: An already bought item is excluded

- **WHEN** an item assigned to Lidl has been marked as bought
- **AND** a member selects the store Lidl
- **THEN** the view does not contain that item

#### Scenario: The store view is grouped by category

- **WHEN** a member selects a store and the matching items span several categories
- **THEN** the items are grouped under their categories, in the household's configured order
- **AND** each group shows its category's name, icon and colour

#### Scenario: An uncategorised item is still visible

- **WHEN** a matching item's catalogue entry has no category
- **THEN** the item appears in an uncategorised group rather than being omitted

### Requirement: Full list view

The system SHALL allow a member to view all outstanding items irrespective of store and availability, showing each item's assigned stores and its availability date when it has one, so the household can review and plan the whole list away from any shop.

This view SHALL be grouped by category on the same terms as the store-filtered view.

#### Scenario: Reviewing the whole list at home

- **WHEN** a member opens the full list
- **THEN** the view contains outstanding items for every store, including items whose availability date has not yet arrived
- **AND** each item shows its assigned stores and its availability date when it has one
- **AND** the items are grouped by category in the household's configured order
