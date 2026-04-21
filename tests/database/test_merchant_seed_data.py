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


def test_same_category_merchants_do_not_share_one_menu_signature() -> None:
    signatures_by_category: dict[str, set[tuple[tuple[str, tuple[str, ...]], ...]]] = {}

    for merchant in MERCHANT_SEED_DATA:
        category = merchant["homepage_category"]
        signatures_by_category.setdefault(category, set()).add(menu_signature(merchant))

    for category in CATEGORY_SET:
        assert len(signatures_by_category[category]) >= 2, category
