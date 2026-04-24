from tools.assistant_sync import _build_dish_text


def test_dish_text_contains_search_scenarios_and_allergen_copy() -> None:
    merchant = {"name": "兰姨小炒"}
    dish = {
        "name": "鱼香肉丝",
        "cuisine_type": "川味麻辣",
        "flavor_profile": "酸甜微辣",
        "price": 28.0,
        "ingredients": ["猪里脊", "木耳"],
        "allergens": [],
        "description": "酸甜微辣，下饭感强",
        "cooking_method": "爆炒",
    }

    text = _build_dish_text(dish, merchant)

    assert "适合场景" in text
    assert "无显式过敏原" in text
