## ADDED Requirements

### Requirement: Important items

A member SHALL be able to flag an item as important when adding or editing it, and to remove the flag. The flag SHALL belong to the item, not to its catalogue entry, and SHALL NOT be remembered for the next item of the same name.

An important item that is outstanding SHALL be shown in a group marked "!" at the top of every view it appears in, ahead of every category group. Importance SHALL NOT change which views an item appears in, and an important item SHALL appear once. An important item SHALL carry the "!" mark on its row wherever it is shown, including in the bought group.

#### Scenario: Flagging an item that must not be forgotten

- **WHEN** a member adds "nappies" and flags it important
- **THEN** "nappies" is shown in the "!" group at the top of the list, above every category group
- **AND** it is not also shown in its category group

#### Scenario: Importance does not widen a store restriction

- **WHEN** "nappies" is important and assigned only to Lidl
- **AND** a member views the store Spar
- **THEN** "nappies" is not shown

#### Scenario: An item is not important unless flagged

- **WHEN** a member adds an item without flagging it
- **THEN** it is not important, and is shown in its category group

#### Scenario: Removing the flag

- **WHEN** a member edits an important item and clears the flag
- **THEN** the item returns to its category group

#### Scenario: A bought important item

- **WHEN** a member marks an important item bought
- **THEN** it moves to the bought group like any other item, still carrying the "!" mark

#### Scenario: Importance is not remembered

- **WHEN** an important "nappies" was bought and cleared
- **AND** a member adds "nappies" again without flagging it
- **THEN** the new item is not important

### Requirement: Adding several items in a row

The add form SHALL offer, beside the action that adds an item and returns to the list, an action that adds the item and presents the add form again, empty. After adding this way the system SHALL show a brief, non-blocking indication naming the item just added. That indication SHALL say the item is pending while the add has not reached the server, and SHALL NOT present it as added until it has.

#### Scenario: Writing up the week's shopping

- **WHEN** a member types "milk" and chooses "Add (again)"
- **THEN** "milk" is on the list
- **AND** the add form is shown again with every field empty
- **AND** a thin status bar says "milk" was added, and goes away by itself

#### Scenario: Adding again with no connection

- **WHEN** the server cannot be reached and a member adds "milk" with "Add (again)"
- **THEN** the status bar says "milk" is pending, not that it was added
- **AND** the form is empty for the next item

### Requirement: The no-store filter is called Anywhere

The store filter SHALL offer, after the household's stores, a choice named "Anywhere" that applies no store filter. It SHALL be the default selection.

#### Scenario: Opening the list

- **WHEN** a member opens the list
- **THEN** the store chips are shown with "Anywhere" last, selected
- **AND** every outstanding item is shown, whatever its stores
