from data_pipeline.models import RawDish, RawMerchant
from data_pipeline.normalizers.dish_normalizer import normalize_dish
from data_pipeline.normalizers.merchant_normalizer import normalize_merchant


def test_normalize_merchant_maps_category_and_defaults():
    raw = RawMerchant(
        source="amap",
        source_id="B001",
        name="Sample Hotpot",
        city="Shanghai",
        district="Jingan",
        address="88 Test Road",
        longitude=121.455,
        latitude=31.229,
        category="Food;Hotpot",
        phone="021-11111111",
        rating=None,
        tags=["Hotpot"],
        raw={},
    )

    merchant = normalize_merchant(raw)

    assert merchant.homepage_category == "火锅"
    assert merchant.rating == 4.5
    assert merchant.business_hours == "10:00-22:00"


def test_normalize_dish_infers_flavor_allergen_method_and_price():
    raw = RawDish(
        source="xiachufang",
        source_id="r1",
        name="Spicy Beef Noodles",
        description="A spicy noodle recipe",
        ingredients=["beef", "wheat noodles", "chili"],
        tags=[],
        cuisine_type="",
        price=None,
        raw={},
    )

    dish = normalize_dish(raw, fallback_cuisine="面食")

    assert dish.cuisine_type == "面食"
    assert dish.flavor_profile == "辣"
    assert dish.cooking_method == "煮"
    assert "麸质" in dish.allergens
    assert dish.price >= 18.0


def test_normalize_chinese_merchant_infers_sichuan_category():
    raw = RawMerchant(
        source="amap",
        source_id="B100",
        name="老四川川菜馆",
        city="Shanghai",
        district="Pudong",
        address="100 Century Avenue",
        longitude=121.5,
        latitude=31.2,
        category="餐饮服务;中餐厅;川菜",
        phone="021-22222222",
        rating=4.8,
        tags=["川菜", "中餐"],
        raw={},
    )

    merchant = normalize_merchant(raw)

    assert merchant.homepage_category == "川菜"


def test_normalize_chinese_dish_infers_spicy_stir_fry():
    raw = RawDish(
        source="xiachufang",
        source_id="r2",
        name="辣椒炒肉",
        description="湖南经典家常菜，辣椒与五花肉大火快炒",
        ingredients=["辣椒", "五花肉", "酱油", "蒜"],
        tags=["湘菜"],
        cuisine_type="",
        price=None,
        raw={},
    )

    dish = normalize_dish(raw, fallback_cuisine="湘菜")

    assert dish.cuisine_type == "湘菜"
    assert dish.flavor_profile == "辣"
    assert dish.cooking_method == "炒"
    assert "大豆" in dish.allergens


def test_normalize_chinese_hotpot_merchant():
    raw = RawMerchant(
        source="amap",
        source_id="B200",
        name="海底捞火锅",
        city="Shanghai",
        district="Jingan",
        address="1 Nanjing Road",
        longitude=121.47,
        latitude=31.23,
        category="餐饮服务;火锅",
        phone="021-33333333",
        rating=4.9,
        tags=["火锅"],
        raw={},
    )

    merchant = normalize_merchant(raw)

    assert merchant.homepage_category == "火锅"


def test_normalize_dish_infers_cuisine_from_tags():
    raw = RawDish(
        source="xiachufang",
        source_id="r3",
        name="小炒黄牛肉",
        description="经典湖南小炒",
        ingredients=["牛肉", "辣椒", "葵花"],
        tags=["湘菜", "湖南"],
        cuisine_type="",
        price=None,
        raw={},
    )

    dish = normalize_dish(raw, fallback_cuisine="中餐")

    assert dish.cuisine_type == "湘菜"
    assert dish.flavor_profile == "辣"
    assert dish.cooking_method == "炒"
