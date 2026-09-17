## Purpose

Lets the list be read and changed where the server cannot be reached — in a shop with no signal, or anywhere away from the home network — by keeping a local copy on the phone, applying changes to it first, and sending them on when the server is reachable again, without ever passing a local change off as confirmed.

## ADDED Requirements

### Requirement: The list is readable without the server

The client SHALL keep a local copy of the list, the stores, the categories and the catalogue, refreshed whenever the server is reachable and retained across the app being closed. When the server cannot be reached, the client SHALL present the local copy and SHALL state when it was last confirmed against the server, so a stale view is never mistaken for a current one.

#### Scenario: Opening the list with no signal

- **WHEN** a member opens the app where the server cannot be reached
- **AND** the app has been used before on this phone
- **THEN** the list, its store filter and its groups are shown from the local copy
- **AND** the app states when the list was last confirmed with the server

#### Scenario: Suggestions still work offline

- **WHEN** a member adds an item while the server cannot be reached
- **THEN** typing still offers catalogue suggestions from the local copy
- **AND** the store chips and categories are still available

#### Scenario: Never used on this phone

- **WHEN** a member opens the app for the first time on a phone, where the server cannot be reached
- **THEN** the app says it cannot reach the server and has nothing to show yet
- **AND** it does not present an empty list as if the list were empty

### Requirement: Changes apply locally first and are queued

When a member adds, edits, removes, buys, undoes or clears items, the client SHALL apply the change to the local copy immediately and SHALL queue it for the server. The queue SHALL survive the app being closed. Changes SHALL be sent in the order they were made.

#### Scenario: Buying an item in a basement

- **WHEN** a member marks an item bought while the server cannot be reached
- **THEN** the item moves to the bought group at once
- **AND** the change is queued

#### Scenario: Adding an item offline and referring to it

- **WHEN** a member adds "ketchup" offline and then marks it bought, still offline
- **THEN** both changes are queued, in that order
- **AND** when the server becomes reachable, "ketchup" exists on the server exactly once and is bought

#### Scenario: The queue survives closing the app

- **WHEN** a member makes changes offline and closes the app
- **AND** later opens it where the server is reachable
- **THEN** the queued changes are sent

### Requirement: A pending change is shown as pending

The client SHALL show, on each affected item, that a change is queued and not yet confirmed by the server, and SHALL remove that indication once the server confirms it. A queued change SHALL NOT be presented as saved on the server.

#### Scenario: A pending item

- **WHEN** an item has a queued change
- **THEN** the item is marked as pending in every view it appears in

#### Scenario: Confirmation clears the mark

- **WHEN** the server confirms a queued change
- **THEN** the pending mark is removed from that item

### Requirement: The queue drains when the server is reachable

The client SHALL send queued changes as soon as the server becomes reachable — when the app is opened, when the connection returns, and on a periodic retry while the app is open — without the member doing anything.

#### Scenario: Walking back into the house

- **WHEN** a member with queued changes comes within reach of the server
- **THEN** the queued changes are sent in order
- **AND** the other member sees them without either member doing anything

#### Scenario: Signal returns in the shop

- **WHEN** the server becomes reachable while the app is open
- **THEN** queued changes are sent without a reload

### Requirement: Later edit wins

When both members changed the same item's field while apart, the change made later in time SHALL stand once both have reached the server. Buying SHALL remain idempotent; removing SHALL be final; neither SHALL prompt the member.

#### Scenario: Two edits to the quantity

- **WHEN** one member changed an item's quantity to 2 at 10:00 offline, and the other changed it to 3 at 10:05 online
- **AND** the first member's change reaches the server at 11:00
- **THEN** the quantity is 3

#### Scenario: Both bought it

- **WHEN** both members mark the same item bought while apart
- **THEN** one purchase is recorded and the item is bought
- **AND** neither member is asked anything

#### Scenario: Removed on one phone, edited on the other

- **WHEN** one member removed an item and the other edited it while apart
- **THEN** the item stays removed
- **AND** the edit is dropped, and the editing member is told

### Requirement: A refused change is dropped and reported

When the server refuses a queued change for a reason that will not change on retry, the client SHALL drop that change, SHALL refresh the local copy from the server, and SHALL tell the member what was not applied and why, in a notice they can dismiss. A queued change SHALL NOT remain pending indefinitely.

#### Scenario: The store was deleted meanwhile

- **WHEN** a member assigned an item to Aldi offline, and the other member deleted Aldi before the change reached the server
- **THEN** the change is dropped
- **AND** a notice says the item could not be updated because Aldi no longer exists
- **AND** the list shows the server's state

#### Scenario: A temporary failure is retried, not dropped

- **WHEN** the server is reachable but answers with a temporary error
- **THEN** the change stays queued and is retried
- **AND** no notice is shown for it

### Requirement: Management needs the server

Changing stores, categories or catalogue entries SHALL require a reachable server. When it cannot be reached, the client SHALL say so on those pages and SHALL NOT queue those changes.

#### Scenario: Renaming a category offline

- **WHEN** a member tries to rename a category where the server cannot be reached
- **THEN** the client says this needs a connection
- **AND** nothing is queued or changed locally
