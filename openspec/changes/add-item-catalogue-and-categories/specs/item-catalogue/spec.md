## Purpose

The household's memory of what it buys, so that the same twenty-odd things are not retyped and re-categorised every week: typing a few letters offers what was bought before, and choosing it brings its category and its usual stores along.

## ADDED Requirements

### Requirement: The catalogue fills itself

The system SHALL record a catalogue entry for an item name the first time it is added to the list, without the member being asked to create one. Adding an item whose name already matches an entry SHALL reuse that entry rather than creating a second one, compared case-insensitively.

This is what makes the catalogue worth having: it is a by-product of using the list, not a database somebody has to maintain first.

#### Scenario: A new name creates an entry

- **WHEN** a member adds an item named "sourdough" and no catalogue entry matches that name
- **THEN** an uncategorised catalogue entry named "sourdough" is created
- **AND** the item is linked to it

#### Scenario: A familiar name reuses its entry

- **WHEN** a member adds an item named "Sourdough" and an entry named "sourdough" already exists
- **THEN** no second entry is created
- **AND** the item is linked to the existing entry

#### Scenario: Adding an item is never blocked by the catalogue

- **WHEN** a member types a name that has never been used and adds it
- **THEN** the item is added with no extra step, prompt or confirmation

### Requirement: Adding an entry directly

The system SHALL also allow a member to add a catalogue entry on its own, with a name, an optional category and remembered stores, without putting an item on the list. This is for setting up the things the household knows it buys, before the first time they are needed. The name SHALL be subject to the same case-insensitive uniqueness as any other entry.

#### Scenario: Adding an entry ahead of needing it

- **WHEN** a member adds the entry "oat milk" with the category Dairy and the store Lidl, from the catalogue page
- **THEN** the entry exists with that category and store
- **AND** no item is added to the list
- **AND** typing "oat" afterwards offers it, carrying Dairy and Lidl

#### Scenario: A duplicate name is refused

- **WHEN** a member adds an entry named "Milk" while "milk" already exists
- **THEN** the system rejects the request and identifies the existing entry
- **AND** no second entry is created

### Requirement: Suggestions while typing

While a member is typing an item name, the system SHALL offer matching catalogue entries. A match SHALL be on the beginning of the name, compared case-insensitively. Suggestions SHALL be ordered with the most recently used first, so the things bought often are reached first.

#### Scenario: Typing offers what was bought before

- **WHEN** the catalogue holds "milk", "mild cheddar" and "bread"
- **AND** a member types "mil"
- **THEN** "milk" and "mild cheddar" are offered
- **AND** "bread" is not

#### Scenario: The most recently used comes first

- **WHEN** the catalogue holds "milk" and "mild cheddar", and "mild cheddar" was added to the list more recently
- **AND** a member types "mil"
- **THEN** "mild cheddar" is offered before "milk"

#### Scenario: An unfamiliar name offers nothing and blocks nothing

- **WHEN** a member types a name that matches no entry
- **THEN** no suggestion is offered
- **AND** the member can still add the item

### Requirement: A suggestion carries what is remembered

When a member chooses a suggestion, the system SHALL prefill the new item with that entry's category and its remembered stores. The prefilled stores SHALL remain editable before the item is added, so a member can depart from the usual without changing what is remembered.

#### Scenario: Choosing a suggestion brings its category and stores

- **WHEN** the entry "ketchup" is categorised as Household and remembers the stores Lidl and Spar
- **AND** a member chooses "ketchup" from the suggestions
- **THEN** the new item is prefilled with the stores Lidl and Spar
- **AND** the item is categorised as Household

#### Scenario: A prefilled store can be changed for one item

- **WHEN** a member chooses a suggestion that prefills Lidl and Spar
- **AND** clears the stores before adding
- **THEN** the item is added with no store, and so appears under every store
- **AND** the catalogue entry still remembers Lidl and Spar

### Requirement: What a catalogue entry remembers

A catalogue entry SHALL hold a name, an optional category, and a set of remembered stores. It SHALL NOT hold a quantity or a unit, because how much is needed genuinely varies from week to week and a remembered quantity would be wrong more often than right.

#### Scenario: An entry holds a category and stores

- **WHEN** a member views a catalogue entry
- **THEN** its name, its category if it has one, and its remembered stores are shown

#### Scenario: Quantity is asked for every time

- **WHEN** a member chooses a suggestion
- **THEN** the quantity and unit are not prefilled from the catalogue

### Requirement: Correcting an entry after the fact

The system SHALL allow a member to set or change a catalogue entry's category and its remembered stores at any time, independently of adding anything to the list. This is the other half of typing fast: a name typed in a hurry is corrected later, once, and every future use benefits.

#### Scenario: Categorising something typed in a hurry

- **WHEN** a member sets the category of the previously uncategorised entry "sourdough" to Bakery
- **THEN** the entry is categorised as Bakery
- **AND** the next item added from that entry is categorised as Bakery

#### Scenario: Changing what stores an entry remembers

- **WHEN** a member changes the remembered stores of "ketchup" to Lidl only
- **THEN** choosing "ketchup" afterwards prefills Lidl only

### Requirement: Renaming and merging entries

The system SHALL allow a catalogue entry to be renamed, and two entries to be merged into one. Merging SHALL move every item referring to the merged-away entry onto the surviving one, and SHALL then remove the merged-away entry.

Without this the catalogue accumulates every typo permanently, and a suggestion list full of near-duplicates is worse than no suggestions at all.

#### Scenario: Fixing a typo by renaming

- **WHEN** a member renames the entry "mlik" to "milk" and no other entry is named "milk"
- **THEN** the entry is renamed
- **AND** typing "mil" offers it

#### Scenario: Merging a duplicate into the real entry

- **WHEN** the catalogue holds both "mlik" and "milk", and a member merges "mlik" into "milk"
- **THEN** only "milk" remains in the catalogue
- **AND** every item that referred to "mlik" now refers to "milk"

#### Scenario: Renaming onto an existing name is refused

- **WHEN** a member renames "mlik" to "milk" while an entry named "milk" already exists
- **THEN** the system rejects the request and offers merging instead
- **AND** both entries are unchanged

### Requirement: An entry in use is not lost

The system SHALL NOT remove a catalogue entry that items still refer to, other than through a merge. Removing one outright would leave those items without the identity they were grouped and suggested by.

#### Scenario: Removing an entry that items refer to

- **WHEN** a member tries to remove a catalogue entry that items on the list still refer to
- **THEN** the system rejects the request and identifies the items
- **AND** the entry remains

#### Scenario: Removing an entry nothing refers to

- **WHEN** a member removes a catalogue entry that no item refers to
- **THEN** the entry is removed
