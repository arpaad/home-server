## ADDED Requirements

### Requirement: Returning to the same store view

The list SHALL keep the store view a member selected when they go to add or edit an item and come back, whether by completing the form, by its back control, or by the device's back gesture.

#### Scenario: Adding while shopping in Lidl

- **WHEN** a member is viewing the store Lidl
- **AND** opens the add form, adds an item and returns
- **THEN** the list shows the store view for Lidl

#### Scenario: Backing out of an edit

- **WHEN** a member is viewing the store Spar, opens an item to edit, and goes back without saving
- **THEN** the list shows the store view for Spar

### Requirement: Row gestures

Each item on the list SHALL respond to a tap by opening it for editing, to a swipe to the right by marking it bought (or, for a bought item, undoing the purchase), and to a swipe to the left by removing it. A swipe SHALL act only when it travels past a threshold; a shorter swipe SHALL leave the item unchanged. While swiping, the item SHALL show what releasing will do. The tick control SHALL continue to mark bought and undo. Removing SHALL also be possible from the edit form.

#### Scenario: Swiping an item bought

- **WHEN** a member swipes "milk" to the right past the threshold
- **THEN** "milk" is marked bought, exactly as by its tick

#### Scenario: Swiping an item away

- **WHEN** a member swipes "milk" to the left past the threshold
- **THEN** "milk" is removed from the list, and no purchase is recorded

#### Scenario: A short swipe does nothing

- **WHEN** a member swipes "milk" a short way and lets go
- **THEN** "milk" is unchanged

#### Scenario: Tapping an item opens it

- **WHEN** a member taps "milk"
- **THEN** the edit form for "milk" is shown

### Requirement: An item already on the list is not added twice

The system SHALL refuse to add an item whose name, ignoring case and surrounding whitespace, matches an outstanding item, whatever stores either is assigned to. The refusal SHALL identify the existing item. A bought item SHALL NOT block adding. A create replayed with the identifier of an item that already exists SHALL still return that item rather than be refused.

When the member's device already knows of the matching item, the add form SHALL say so before sending, naming the stores the existing item is assigned to, and SHALL offer to edit the existing item instead.

#### Scenario: Milk for Spar when milk for Lidl is on the list

- **WHEN** "milk" assigned to Lidl is outstanding
- **AND** a member adds "Milk" assigned to Spar
- **THEN** the add is refused
- **AND** the member is told "milk" is already on the list, at Lidl, and offered to edit it

#### Scenario: Buying more of something just bought

- **WHEN** "milk" has been bought and not cleared
- **AND** a member adds "milk"
- **THEN** the new item is added

#### Scenario: Both phones added it while apart

- **WHEN** both members add "milk" while their phones cannot reach the server
- **AND** both phones reconnect
- **THEN** one "milk" is on the list
- **AND** the member whose add was refused is told why
