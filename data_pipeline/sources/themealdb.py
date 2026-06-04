from __future__ import annotations

from typing import Any

import requests

from data_pipeline.models import RawDish


THEMEALDB_SEARCH_URL = "https://www.themealdb.com/api/json/v1/1/search.php"


def parse_themealdb_meal(meal: dict[str, Any]) -> RawDish:
    ingredients: list[str] = []
    for index in range(1, 21):
        ingredient = str(meal.get(f"strIngredient{index}") or "").strip()
        if ingredient:
            ingredients.append(ingredient)
    return RawDish(
        source="themealdb",
        source_id=str(meal.get("idMeal") or meal.get("strMeal") or ""),
        name=str(meal.get("strMeal") or "")[:128],
        description=str(meal.get("strInstructions") or "")[:500],
        ingredients=ingredients,
        tags=[str(meal.get("strCategory") or ""), str(meal.get("strArea") or "")],
        cuisine_type=str(meal.get("strArea") or ""),
        price=None,
        raw=meal,
    )


def fetch_themealdb_by_letter(letter: str, session=None) -> list[RawDish]:
    client = session or requests.Session()
    response = client.get(THEMEALDB_SEARCH_URL, params={"f": letter}, timeout=10)
    response.raise_for_status()
    meals = response.json().get("meals") or []
    return [parse_themealdb_meal(meal) for meal in meals if meal.get("strMeal")]
