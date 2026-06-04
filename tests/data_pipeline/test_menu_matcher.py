from data_pipeline.models import NormalizedDish, NormalizedMerchant
from data_pipeline.normalizers.menu_matcher import build_menu_assignments


def merchant(name, category):
    return NormalizedMerchant(
        source="amap", source_id=name, name=name, description="", city="Shanghai", district="Jingan",
        address=name, longitude=0, latitude=0, homepage_category=category, promo_text="",
        delivery_radius_meters=3000, delivery_fee=3, min_order_amount=20, avg_delivery_minutes=30,
        rating=4.5, phone="", business_hours="", detailed_address=name, address_note="",
        merchant_tags=[category],
    )


def dish(name, cuisine):
    return NormalizedDish(
        source="xiachufang", source_id=name, name=name, description="", price=20, tags=[],
        cuisine_type=cuisine, flavor_profile="balanced", ingredients=["rice"], allergens=[],
        cooking_method="cooked", is_recommended=False,
    )


def test_build_menu_assignments_matches_category_and_limits_menu_size():
    merchants = [merchant("Noodle A", "面食")]
    dishes = [dish("Noodle One", "面食"), dish("Noodle Two", "面食"), dish("Rice One", "盖浇饭")]

    assignments = build_menu_assignments(merchants, dishes, dishes_per_merchant=2)

    assert len(assignments) == 1
    assert assignments[0].category_name == "Signature"
    assert [d.name for d in assignments[0].dishes] == ["Noodle One", "Noodle Two"]
