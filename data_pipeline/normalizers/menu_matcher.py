from __future__ import annotations

from collections import defaultdict

from data_pipeline.models import DishAssignment, NormalizedDish, NormalizedMerchant


def build_menu_assignments(
    merchants: list[NormalizedMerchant],
    dishes: list[NormalizedDish],
    *,
    dishes_per_merchant: int = 20,
) -> list[DishAssignment]:
    dishes_by_cuisine: dict[str, list[NormalizedDish]] = defaultdict(list)
    for dish in dishes:
        dishes_by_cuisine[dish.cuisine_type].append(dish)

    assignments: list[DishAssignment] = []
    for merchant in merchants:
        matched = list(dishes_by_cuisine.get(merchant.homepage_category, []))
        unique: list[NormalizedDish] = []
        seen_names: set[str] = set()
        for dish in matched:
            if dish.name in seen_names:
                continue
            seen_names.add(dish.name)
            unique.append(dish)
            if len(unique) >= dishes_per_merchant:
                break
        assignments.append(DishAssignment(merchant=merchant, category_name="Signature", dishes=unique))
    return assignments
