## Purpose

A single shared shopping list for a household, in which every item records which stores it may be bought from and when it becomes worth buying, so that a member standing in a particular shop sees exactly what to put in the basket without anyone maintaining duplicate per-store lists.

## Requirements

### Requirement: Single shared household list

The system SHALL maintain exactly one active shopping list for the household. Every household member SHALL see the same items on it, and any member's change SHALL be visible to the others. The system SHALL NOT organise items into separate per-store lists.

#### Scenario: An item added by one member is visible to another

- **WHEN** a member adds an item to the list
- **THEN** every other household member sees that item on the same list

#### Scenario: The list is not split by store

- **WHEN** a member opens the list
- **THEN** the system presents one list of items
- **AND** the member is not asked to choose which store's list to open

### Requirement: Adding an item

The system SHALL allow a member to add an item identified by a name, with a quantity and a unit of measure. The name MUST be non-empty. The quantity MUST be greater than zero. When quantity and unit are not supplied, the system SHALL default them to a quantity of one piece.

#### Scenario: Adding an item with only a name

- **WHEN** a member adds an item named "ketchup" without specifying anything else
- **THEN** the item is created with a quantity of one piece, with no stores and no availability date

#### Scenario: An empty name is rejected

- **WHEN** a member submits an item whose name is empty or contains only whitespace
- **THEN** the system rejects the request with a validation error
- **AND** no item is created

#### Scenario: A non-positive quantity is rejected

- **WHEN** a member submits an item with a quantity of zero or less
- **THEN** the system rejects the request with a validation error
- **AND** no item is created

### Requirement: Store registry

The system SHALL maintain the set of stores the household shops at. Each store SHALL have a name that is unique within the household, compared case-insensitively. Items SHALL only reference stores that exist in this set, so that a mistyped store name cannot silently hide an item from that store's shopping view.

#### Scenario: Adding a store

- **WHEN** a member adds a store named "Lidl"
- **THEN** the store becomes available for assignment to items

#### Scenario: A duplicate store name is rejected

- **WHEN** a member adds a store named "lidl" and a store named "Lidl" already exists
- **THEN** the system rejects the request with a validation error
- **AND** only the original store remains

#### Scenario: An unknown store cannot be assigned to an item

- **WHEN** a member assigns a store that does not exist in the registry to an item
- **THEN** the system rejects the request with a validation error
- **AND** the item's stores are unchanged

### Requirement: Store assignment on an item

An item SHALL carry zero or more stores. Carrying no store SHALL mean the item may be bought at any store, and such an item SHALL appear under every store's shopping view. Carrying one or more stores SHALL restrict the item to those stores only.

#### Scenario: An item restricted to specific stores

- **WHEN** an item is assigned the stores "Lidl" and "Spar"
- **THEN** the item appears in the shopping view for Lidl and for Spar
- **AND** the item does not appear in the shopping view for any other store

#### Scenario: An item with no store belongs everywhere

- **WHEN** an item has no store assigned
- **THEN** the item appears in the shopping view for every store

### Requirement: Availability date

An item MAY carry a date from which it is worth buying. Before that date the system SHALL exclude the item from shopping views. From that date onwards the system SHALL include it, without any member editing the item. An item with no such date SHALL always be considered available. The date boundary SHALL be evaluated against the household's local calendar date, with the item becoming available at the start of that date.

#### Scenario: An item is hidden until its date

- **WHEN** an item has an availability date in the future
- **THEN** the item does not appear in any store's shopping view

#### Scenario: An item surfaces on its date without manual action

- **WHEN** the household's local date reaches an item's availability date
- **THEN** the item appears in the shopping views it qualifies for
- **AND** no member had to edit or re-add the item

#### Scenario: An item without a date is always available

- **WHEN** an item has no availability date
- **THEN** its presence in a shopping view depends only on its stores and whether it is still outstanding

### Requirement: Store-filtered shopping view

Given a selected store, the system SHALL present exactly those items that are still outstanding, that are available on the current date, and that either have no store assigned or include the selected store.

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

### Requirement: Full list view

The system SHALL allow a member to view all outstanding items irrespective of store and availability, showing each item's assigned stores and its availability date when it has one, so the household can review and plan the whole list away from any shop.

#### Scenario: Reviewing the whole list at home

- **WHEN** a member opens the full list
- **THEN** the view contains outstanding items for every store, including items whose availability date has not yet arrived
- **AND** each item shows its assigned stores and its availability date when it has one

### Requirement: Marking an item as bought

When a member marks an item as bought, the system SHALL record which member did so and when, and SHALL remove the item from the shopping views of all members and all stores. Because an item exists once on the shared list, marking it bought SHALL remove it everywhere, so it cannot be bought a second time from another store's view.

#### Scenario: Buying an item removes it from every store's view

- **WHEN** an item assigned to both Lidl and Spar is marked as bought by a member shopping in Lidl
- **THEN** the item no longer appears in the shopping view for Lidl
- **AND** the item no longer appears in the shopping view for Spar
- **AND** the item no longer appears for any other member

#### Scenario: A purchase is attributed

- **WHEN** a member marks an item as bought
- **THEN** the system records that member and the time of the action against that item

### Requirement: Undoing a purchase

The system SHALL allow a member to undo an item marked as bought in error. Undoing SHALL return the item to the outstanding list for all members and SHALL leave no purchase recorded against it.

#### Scenario: Restoring an item marked bought by mistake

- **WHEN** a member undoes the purchase of an item
- **THEN** the item is outstanding again and reappears in the shopping views it qualifies for
- **AND** no purchase is recorded against the item

### Requirement: Removing an item that is no longer wanted

The system SHALL distinguish removing an item from marking it as bought. Removing an item SHALL take it off the list without recording a purchase, so that later reporting cannot mistake a discarded item for something the household bought.

#### Scenario: Discarding an item nobody wants any more

- **WHEN** a member removes an outstanding item from the list
- **THEN** the item no longer appears in any view
- **AND** no purchase is recorded against it

### Requirement: Editing an item

The system SHALL allow a member to change an outstanding item's name, quantity, unit, assigned stores and availability date. Changes SHALL apply to the single shared item and SHALL therefore be visible to every member.

#### Scenario: Correcting which stores an item belongs to

- **WHEN** a member changes an item's stores from "Lidl" to "Lidl" and "Spar"
- **THEN** the item subsequently appears in the shopping views for both stores

#### Scenario: An edit is visible to the other member

- **WHEN** one member changes an item's quantity
- **THEN** the other member sees the updated quantity on the same item

### Requirement: Protecting store assignments when a store is removed

The system SHALL refuse to delete a store that outstanding items still reference, and SHALL report which items reference it. Silently unassigning the store would turn a restricted item into an unrestricted one and make it appear in every store's view, which is the failure this capability exists to prevent.

#### Scenario: Deleting a store that is still in use is refused

- **WHEN** a member deletes a store that outstanding items still reference
- **THEN** the system rejects the request and identifies the items that reference it
- **AND** the store and the items' assignments are unchanged

#### Scenario: Deleting an unused store succeeds

- **WHEN** a member deletes a store that no outstanding item references
- **THEN** the store is removed from the registry

### Requirement: Item origin

Each item SHALL record how it came to be on the list, and that origin SHALL be visible when the item is read. In this release every item originates from a member entering it manually.

#### Scenario: A manually entered item records its origin

- **WHEN** a member adds an item by hand
- **THEN** reading that item shows that it originated from manual entry

### Requirement: Member identification without authentication

The system SHALL identify which household member is acting, so that purchases can be attributed. This release SHALL NOT authenticate members and SHALL NOT require credentials; it is intended to be reachable only from the household's own network.

#### Scenario: Acting as a chosen member

- **WHEN** a member selects who they are in the client
- **THEN** subsequent actions they take are attributed to that member

#### Scenario: No credentials are demanded

- **WHEN** a member opens the app from the household network
- **THEN** the app is usable without a password or login step

### Requirement: Installable mobile client

The system SHALL provide a client that a member can install onto a phone's home screen and open as a standalone app, since the list is used while walking around a shop.

#### Scenario: Installing the client on a phone

- **WHEN** a member opens the client in a mobile browser on the household network
- **THEN** the browser offers to install it to the home screen
- **AND** opening it from the home screen presents the app without browser chrome

### Requirement: Connectivity is required for changes

This release SHALL require a reachable server for every change. When the server cannot be reached, the client SHALL report the failure and SHALL NOT present the change as having succeeded, so that no edit is silently lost.

#### Scenario: An edit attempted with no connection

- **WHEN** a member changes an item while the server is unreachable
- **THEN** the client reports that the change could not be saved
- **AND** the client does not show the change as saved

#### Scenario: A stale view is not mistaken for a current one

- **WHEN** a member opens the client while the server is unreachable
- **THEN** the client makes clear that it cannot confirm the list is current

### Requirement: The list survives restarts

The system SHALL retain the household's items, stores and recorded purchases across restarts of the application and of the database. After a restart every member SHALL see the same list as they saw before it.

#### Scenario: The service is restarted

- **WHEN** the application is restarted
- **THEN** the outstanding items, their assigned stores and availability dates, and the recorded purchases are all unchanged

#### Scenario: The device loses power

- **WHEN** the device running the service loses power and is switched back on
- **THEN** the list becomes available again without a member restoring it by hand
- **AND** every change that was confirmed as saved before the power loss is still present
