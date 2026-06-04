from data_pipeline.models import NormalizedDish, NormalizedMerchant
from data_pipeline.storage.dedupe import dedupe_dishes, dedupe_merchants, normalize_key


def merchant(name, address):
    return NormalizedMerchant(
        source="amap", source_id=name, name=name, description="", city="Shanghai", district="Jingan",
        address=address, longitude=0, latitude=0, homepage_category="中餐", promo_text="",
        delivery_radius_meters=3000, delivery_fee=3, min_order_amount=20, avg_delivery_minutes=30,
        rating=4.5, phone="", business_hours="", detailed_address=address, address_note="",
        merchant_tags=[],
    )


def dish(name):
    return NormalizedDish(
        source="xiachufang", source_id=name, name=name, description="", price=20, tags=[],
        cuisine_type="中餐", flavor_profile="家常", ingredients=["rice"], allergens=[],
        cooking_method="烹饪", is_recommended=False,
    )


def test_normalize_key_removes_spacing_and_case():
    assert normalize_key(" Sample  Shop ") == "sampleshop"


def test_dedupe_merchants_keeps_first_name_address_pair():
    merchants = [merchant("A Shop", "1 Road"), merchant("A  Shop", "1 Road"), merchant("A Shop", "2 Road")]

    result = dedupe_merchants(merchants)

    assert [m.address for m in result] == ["1 Road", "2 Road"]


def test_dedupe_dishes_keeps_first_name_cuisine_pair():
    dishes = [dish("Beef Rice"), dish("Beef  Rice")]

    assert len(dedupe_dishes(dishes)) == 1
