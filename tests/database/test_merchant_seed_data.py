from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.seeds.merchant_seed_data import MERCHANT_SEED_DATA


CATEGORY_SET = {"湘菜", "轻食", "咖啡甜品", "炸鸡汉堡", "粥面", "日韩料理", "麻辣烫", "披萨意面"}


def menu_signature(merchant: dict) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(
        (category["name"], tuple(dish["name"] for dish in category["dishes"]))
        for category in merchant["categories"]
    )


def test_merchant_seed_data_contains_diverse_homepage_categories() -> None:
    categories = {merchant["homepage_category"] for merchant in MERCHANT_SEED_DATA}

    assert CATEGORY_SET.issubset(categories)
    assert len(categories) >= 8
    assert len(MERCHANT_SEED_DATA) >= 40


def test_merchant_seed_data_uses_realistic_names_without_numeric_suffixes() -> None:
    names = [merchant["name"] for merchant in MERCHANT_SEED_DATA]

    assert len(names) == len(set(names))
    assert all(not re.search(r"\d", name) for name in names)
    assert all(len(name) >= 3 for name in names)


def test_merchants_include_precise_operational_metadata() -> None:
    assert all(merchant["phone"].startswith("021-") for merchant in MERCHANT_SEED_DATA)
    assert all(merchant["business_hours"] for merchant in MERCHANT_SEED_DATA)
    assert all(merchant["detailed_address"] for merchant in MERCHANT_SEED_DATA)
    assert all(merchant["address_note"] for merchant in MERCHANT_SEED_DATA)
    assert all(isinstance(merchant["merchant_tags"], list) and merchant["merchant_tags"] for merchant in MERCHANT_SEED_DATA)


def test_same_category_merchants_do_not_share_one_menu_signature() -> None:
    signatures_by_category: dict[str, set[tuple[tuple[str, tuple[str, ...]], ...]]] = {}

    for merchant in MERCHANT_SEED_DATA:
        category = merchant["homepage_category"]
        signatures_by_category.setdefault(category, set()).add(menu_signature(merchant))

    for category in CATEGORY_SET:
        assert len(signatures_by_category[category]) >= 2, category


def test_every_seeded_dish_contains_structured_rag_fields() -> None:
    dishes = [
        dish
        for merchant in MERCHANT_SEED_DATA
        for category in merchant["categories"]
        for dish in category["dishes"]
    ]

    assert all(dish["cuisine_type"] for dish in dishes)
    assert all(dish["flavor_profile"] for dish in dishes)
    assert all(isinstance(dish["ingredients"], list) and dish["ingredients"] for dish in dishes)
    assert all(isinstance(dish["allergens"], list) for dish in dishes)
    assert all(dish["cooking_method"] for dish in dishes)


def test_selected_signature_dishes_use_handwritten_menu_copy() -> None:
    signature_descriptions = {
        dish["name"]: dish["description"]
        for merchant in MERCHANT_SEED_DATA
        for category in merchant["categories"]
        for dish in category["dishes"]
        if dish["name"] in {"辣椒炒肉", "小炒黄牛肉", "鲜虾云吞面", "香煎鸡胸藜麦碗", "燕麦拿铁", "巴斯克芝士蛋糕"}
    }

    assert signature_descriptions["辣椒炒肉"] == "现切猪前腿肉搭配青红椒大火快炒，锅气足、咸香辣劲明显，是工作日最稳的下饭菜。"
    assert signature_descriptions["小炒黄牛肉"] == "黄牛肉片现炒到刚刚断生，芹菜和小米椒提香提辣，口感嫩爽，越吃越开胃。"
    assert signature_descriptions["鲜虾云吞面"] == "鲜虾云吞现煮后配细面和热汤，入口鲜甜不腻，适合想吃热乎主食的时候来一碗。"
    assert signature_descriptions["香煎鸡胸藜麦碗"] == "香煎鸡胸切片铺在藜麦和时蔬上，调味清爽不厚重，饱腹感在线，做午餐很合适。"
    assert signature_descriptions["燕麦拿铁"] == "浓缩咖啡融合燕麦奶，入口顺滑带坚果香，苦感柔和，适合上午提神或下午慢慢喝。"
    assert signature_descriptions["巴斯克芝士蛋糕"] == "表层带一点焦香，内里绵密湿润，芝士味浓但不腻，配一杯热美式会更舒服。"
