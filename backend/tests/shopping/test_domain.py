"""The domain types construct, and enforce the item invariants."""

import unittest
from datetime import UTC, date, datetime
from uuid import uuid4

from app.modules.household.domain.member import HouseholdMember
from app.modules.household.errors import EmptyMemberNameError
from app.modules.shopping.domain.item import ShoppingItem
from app.modules.shopping.domain.purchase import Purchase
from app.modules.shopping.domain.store import Store
from app.modules.shopping.errors import (
    EmptyItemNameError,
    EmptyStoreNameError,
    NonPositiveQuantityError,
)

LIDL = Store(id=uuid4(), name="Lidl")
SPAR = Store(id=uuid4(), name="Spar")
ALDI = Store(id=uuid4(), name="Aldi")

TODAY = date(2026, 9, 10)


def an_item(**overrides: object) -> ShoppingItem:
    """Build an item, overriding only the fields a test cares about.

    Args:
        **overrides: Field values replacing the defaults.

    Returns:
        A shopping item built from the defaults and the overrides.
    """
    fields: dict[str, object] = {"id": uuid4(), "name": "ketchup"}
    fields.update(overrides)
    return ShoppingItem(**fields)  # pyright: ignore[reportArgumentType]


class TestConstruction(unittest.TestCase):
    def test_each_domain_type_constructs(self):
        member = HouseholdMember(id=uuid4(), name="Arpad")
        item = an_item()
        purchase = Purchase(
            id=uuid4(),
            item_id=item.id,
            member_id=member.id,
            bought_at=datetime.now(UTC),
        )

        self.assertEqual(member.name, "Arpad")
        self.assertEqual(LIDL.name, "Lidl")
        self.assertEqual(item.name, "ketchup")
        self.assertEqual(purchase.item_id, item.id)

    def test_an_item_defaults_to_one_piece_with_no_stores_and_no_date(self):
        item = an_item()

        self.assertEqual(item.quantity, 1.0)
        self.assertEqual(item.unit, "piece")
        self.assertEqual(item.stores, ())
        self.assertIsNone(item.available_from)
        self.assertEqual(item.origin, "manual")
        self.assertTrue(item.is_outstanding)


class TestItemInvariants(unittest.TestCase):
    def test_an_empty_name_is_rejected(self):
        with self.assertRaises(EmptyItemNameError):
            an_item(name="")

    def test_a_whitespace_only_name_is_rejected(self):
        with self.assertRaises(EmptyItemNameError):
            an_item(name="   \t ")

    def test_a_zero_quantity_is_rejected(self):
        with self.assertRaises(NonPositiveQuantityError):
            an_item(quantity=0)

    def test_a_negative_quantity_is_rejected(self):
        with self.assertRaises(NonPositiveQuantityError):
            an_item(quantity=-2.5)

    def test_an_empty_store_name_is_rejected(self):
        with self.assertRaises(EmptyStoreNameError):
            Store(id=uuid4(), name=" ")

    def test_an_empty_member_name_is_rejected(self):
        with self.assertRaises(EmptyMemberNameError):
            HouseholdMember(id=uuid4(), name="")


class TestStoreMembership(unittest.TestCase):
    def test_an_item_with_no_store_belongs_to_every_store(self):
        item = an_item(name="milk")

        self.assertTrue(item.belongs_to_store(LIDL.id))
        self.assertTrue(item.belongs_to_store(SPAR.id))
        self.assertTrue(item.belongs_to_store(ALDI.id))

    def test_an_item_is_restricted_to_the_stores_it_carries(self):
        item = an_item(stores=(LIDL, SPAR))

        self.assertTrue(item.belongs_to_store(LIDL.id))
        self.assertTrue(item.belongs_to_store(SPAR.id))
        self.assertFalse(item.belongs_to_store(ALDI.id))


class TestAvailability(unittest.TestCase):
    def test_an_item_without_a_date_is_always_available(self):
        self.assertTrue(an_item().is_available_on(TODAY))

    def test_an_item_is_hidden_before_its_date(self):
        item = an_item(available_from=date(2026, 9, 11))

        self.assertFalse(item.is_available_on(TODAY))

    def test_an_item_becomes_available_on_its_date(self):
        item = an_item(available_from=TODAY)

        self.assertTrue(item.is_available_on(TODAY))

    def test_an_item_stays_available_after_its_date(self):
        item = an_item(available_from=date(2026, 9, 9))

        self.assertTrue(item.is_available_on(TODAY))


class TestShoppingView(unittest.TestCase):
    def test_the_ketchup_case(self):
        ketchup = an_item(name="ketchup", stores=(LIDL, SPAR))
        milk = an_item(name="milk")
        cat_litter = an_item(name="cat litter", stores=(ALDI,))

        in_lidl = [
            i.name for i in (ketchup, milk, cat_litter) if i.is_in_shopping_view_of(LIDL.id, TODAY)
        ]

        self.assertEqual(in_lidl, ["ketchup", "milk"])

    def test_a_postponed_item_is_excluded(self):
        item = an_item(stores=(LIDL,), available_from=date(2026, 9, 30))

        self.assertFalse(item.is_in_shopping_view_of(LIDL.id, TODAY))

    def test_a_bought_item_is_excluded_from_every_store(self):
        item_id = uuid4()
        bought = an_item(
            id=item_id,
            stores=(LIDL, SPAR),
            purchase=Purchase(
                id=uuid4(),
                item_id=item_id,
                member_id=uuid4(),
                bought_at=datetime.now(UTC),
            ),
        )

        self.assertFalse(bought.is_outstanding)
        self.assertFalse(bought.is_in_shopping_view_of(LIDL.id, TODAY))
        self.assertFalse(bought.is_in_shopping_view_of(SPAR.id, TODAY))


if __name__ == "__main__":
    unittest.main()
