from api.models import Base


EXPECTED_TABLES = {
    "users",
    "user_addresses",
    "merchants",
    "dish_categories",
    "dishes",
    "carts",
    "cart_items",
    "checkout_orders",
    "merchant_orders",
    "order_items",
    "payment_records",
    "delivery_quotes",
    "action_journal",
    "user_memories",
}



def test_phase1_models_register_expected_tables() -> None:
    assert EXPECTED_TABLES == set(Base.metadata.tables)
