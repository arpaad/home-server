## MODIFIED Requirements

### Requirement: Adding an item

The system SHALL allow a member to add an item identified by a name, with a quantity and a unit of measure. The name MUST be non-empty. The quantity MUST be greater than zero. When quantity and unit are not supplied, the system SHALL default them to a quantity of one piece.

Every added item SHALL be linked to a catalogue entry matching its name, creating that entry when none exists. The member SHALL NOT be required to choose or create an entry: adding an item by typing a name remains a single action.

A client MAY supply the item's identifier. Adding an item whose identifier already exists SHALL return the existing item unchanged rather than creating a second one, so that a change sent twice — once before a connection dropped and once after — lands once.

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

#### Scenario: Adding the same item twice lands once

- **WHEN** a client adds an item with an identifier it generated, and then sends the same request again
- **THEN** exactly one item with that identifier exists
- **AND** the second request succeeds and returns it

### Requirement: Editing an item

The system SHALL allow a member to change an outstanding item's name, quantity, unit, assigned stores and availability date. Changes SHALL apply to the single shared item and SHALL therefore be visible to every member.

A member MAY also choose a category while editing. Because an item's category is its catalogue entry's, that choice SHALL be recorded on the entry and SHALL therefore apply to every item of that name; the system SHALL make this visible at the point of choosing, so a member is not surprised by other items moving.

A client MAY state when an edit was made. The system SHALL NOT apply an edit that was made earlier than the item's most recent applied edit, so that of two members' edits made while apart, the later one stands whichever arrives first. An edit without a stated time SHALL always apply.

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

#### Scenario: An older edit arriving later does not overwrite a newer one

- **WHEN** an item's quantity was set to 3 by an edit made at 10:05
- **AND** an edit made at 10:00 setting it to 2 arrives afterwards
- **THEN** the quantity stays 3
- **AND** the late edit is answered as not applied, not as an error

### Requirement: Removing an item that is no longer wanted

The system SHALL distinguish removing an item from marking it as bought. Removing an item SHALL take it off the list without recording a purchase, so that later reporting cannot mistake a discarded item for something the household bought.

Removing an item that no longer exists SHALL succeed, so that a removal sent twice, or a removal of something the other member already removed, is not an error.

#### Scenario: Discarding an item nobody wants any more

- **WHEN** a member removes an outstanding item from the list
- **THEN** the item no longer appears in any view
- **AND** no purchase is recorded against it

#### Scenario: Removing something already gone

- **WHEN** a client removes an item that does not exist
- **THEN** the request succeeds
- **AND** nothing changes

### Requirement: Connectivity is required for changes

This requirement is reversed: the client SHALL NOT require a reachable server for a change to the list. A change SHALL be applied to the phone's local copy at once and queued for the server, and SHALL be shown as pending — never as confirmed — until the server accepts it. When the server cannot be reached, the client SHALL say so and SHALL state when the list was last confirmed, so that no edit is silently lost and no stale view is mistaken for a current one.

#### Scenario: An edit attempted with no connection

- **WHEN** a member changes an item while the server is unreachable
- **THEN** the change is applied to the local copy and shown as pending
- **AND** the client does not show the change as confirmed by the server
- **AND** the change is sent once the server is reachable

#### Scenario: A stale view is not mistaken for a current one

- **WHEN** a member opens the client while the server is unreachable
- **THEN** the client shows the local copy and states when it was last confirmed with the server
