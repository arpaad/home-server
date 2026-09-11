## Purpose

Categories group the shopping list so that a member walking around a shop collects everything from one part of it at a time, instead of criss-crossing the aisles in whatever order items happened to be typed.

## ADDED Requirements

### Requirement: Category registry

The system SHALL maintain the set of categories the household sorts its shopping into. Each category SHALL have a name that is unique within the household, compared case-insensitively, an icon, and a colour. Members SHALL be able to add, rename, recolour and remove categories.

#### Scenario: Adding a category

- **WHEN** a member adds a category named "Bakery" with an icon and a colour
- **THEN** the category becomes available for assignment to catalogue entries

#### Scenario: A duplicate category name is rejected

- **WHEN** a member adds a category named "bakery" and a category named "Bakery" already exists
- **THEN** the system rejects the request with a validation error
- **AND** only the original category remains

#### Scenario: An empty category name is rejected

- **WHEN** a member submits a category whose name is empty or contains only whitespace
- **THEN** the system rejects the request with a validation error
- **AND** no category is created

### Requirement: Seeded categories

The system SHALL provide a usable set of categories on a fresh installation, so that categorising works before anyone has configured anything. These seeded categories SHALL be editable and removable exactly like any other, carrying no special status.

#### Scenario: A fresh installation already has categories

- **WHEN** the household opens the app on a newly installed system
- **THEN** a set of categories covering everyday shopping is already present
- **AND** each has an icon and a colour

#### Scenario: A seeded category can be changed like any other

- **WHEN** a member renames or removes a seeded category
- **THEN** the change is accepted, exactly as for a category they created

### Requirement: Category appearance

Each category SHALL carry an icon and a colour, and the system SHALL show both wherever a category labels a group of items, so a member can recognise a group without reading it.

#### Scenario: A category is recognisable at a glance

- **WHEN** a member views a list grouped by category
- **THEN** each group heading shows its category's icon and colour alongside its name

#### Scenario: Choosing an icon and colour

- **WHEN** a member creates or edits a category
- **THEN** they can choose its icon and its colour
- **AND** the choice is visible immediately wherever that category appears

### Requirement: Category ordering

The system SHALL keep a household-wide order for categories, and SHALL present grouped lists in that order. Members SHALL be able to change it. The order SHALL be the same in every store's view, because it exists to match how the household shops rather than the layout of one particular shop.

#### Scenario: Groups follow the configured order

- **WHEN** the household has ordered its categories as produce, then dairy, then household
- **AND** a member opens a list containing items from all three
- **THEN** the groups appear in that order, whichever store is selected

#### Scenario: Reordering takes effect for both members

- **WHEN** a member changes the category order
- **THEN** the other member's list is grouped in the new order

### Requirement: Removing a category

The system SHALL allow a category to be removed even while catalogue entries refer to it. Those entries SHALL become uncategorised, and the system SHALL tell the member how many were affected before the removal proceeds. Unlike a store assignment, an absent category hides nothing — it moves items into the uncategorised group, where they remain visible.

#### Scenario: Removing a category in use

- **WHEN** a member removes a category that catalogue entries still refer to
- **THEN** the system states how many entries will become uncategorised
- **AND** on confirmation the category is removed and those entries become uncategorised
- **AND** no item disappears from any list

#### Scenario: Removing an unused category

- **WHEN** a member removes a category that no catalogue entry refers to
- **THEN** the category is removed without further prompting
