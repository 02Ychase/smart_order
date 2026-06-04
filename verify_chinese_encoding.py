"""Verify that Chinese normalization rules are correctly encoded and functional.

Run: python verify_chinese_encoding.py

This script checks:
1. File bytes are valid UTF-8 (not mojibake)
2. Specific Chinese keywords exist as correct UTF-8 byte sequences
3. Merchant category inference works with real Chinese AMap-style data
4. Dish normalization works with real Chinese XiaChuFang-style data
"""
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_file_encoding():
    """Check that normalizer files contain correct UTF-8 Chinese."""
    files = [
        "data_pipeline/normalizers/merchant_normalizer.py",
        "data_pipeline/normalizers/dish_normalizer.py",
    ]
    all_ok = True
    for fpath in files:
        data = (PROJECT_ROOT / fpath).read_bytes()
        # Valid UTF-8 Chinese chars are 3-byte sequences: E4-E9 followed by 80-BF twice
        chinese_pattern = rb"[\xe4-\xe9][\x80-\xbf][\x80-\xbf]"
        matches = re.findall(chinese_pattern, data)
        print(f"  {fpath}: {len(matches)} valid UTF-8 Chinese sequences")
        if len(matches) == 0:
            all_ok = False
    return all_ok


def check_specific_keywords():
    """Check that specific Chinese keywords exist as correct byte sequences."""
    data = (PROJECT_ROOT / "data_pipeline/normalizers/merchant_normalizer.py").read_bytes()
    keywords = {
        "火锅": "hotpot",       # 火锅
        "川菜": "sichuan",      # 川菜
        "湘菜": "hunan",        # 湘菜
        "烧烤": "bbq",          # 烧烤
        "咖啡": "coffee",       # 咖啡
    }
    all_ok = True
    for chinese, expected_cat in keywords.items():
        expected_bytes = chinese.encode("utf-8")
        if expected_bytes in data:
            print(f"  {chinese} ({expected_cat}): FOUND [{expected_bytes.hex()}]")
        else:
            print(f"  {chinese} ({expected_cat}): MISSING! Expected bytes {expected_bytes.hex()}")
            all_ok = False
    return all_ok


def check_merchant_matching():
    """Test merchant category inference with real Chinese strings."""
    from data_pipeline.models import RawMerchant
    from data_pipeline.normalizers.merchant_normalizer import infer_homepage_category

    tests = [
        ("餐饮服务;中餐厅;川菜", [], "sichuan"),
        ("餐饮服务;火锅", [], "hotpot"),
        ("Food", ["海底捞火锅"], "hotpot"),
        ("餐饮服务;烧烤", [], "bbq"),
        ("餐饮服务;日料", [], "japanese korean"),
    ]
    all_ok = True
    for category, tags, expected in tests:
        raw = RawMerchant(
            source="amap", source_id="1", name="test",
            city="Shanghai", district="Pudong", address="",
            longitude=0, latitude=0, category=category,
            tags=tags, raw={},
        )
        result = infer_homepage_category(raw)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] category={category!r}, tags={tags!r} => {result} (expected {expected})")
        if result != expected:
            all_ok = False
    return all_ok


def check_dish_matching():
    """Test dish normalization with real Chinese strings."""
    from data_pipeline.models import RawDish
    from data_pipeline.normalizers.dish_normalizer import normalize_dish

    tests = [
        {
            "name": "辣椒炒肉",
            "desc": "湖南经典家常菜，辣椒与五花肉大火快炒",
            "ingredients": ["辣椒", "五花肉", "酱油", "蒜"],
            "tags": ["湘菜"],
            "expected_cuisine": "hunan",
            "expected_flavor": "spicy",
            "expected_method": "fried",
            "expected_allergens": ["soy"],
        },
        {
            "name": "红烧牛肉面",
            "desc": "经典红烧口味牛肉面",
            "ingredients": ["牛肉", "面条", "酱油"],
            "tags": [],
            "expected_cuisine": "noodles",
            "expected_flavor": "savory",
            "expected_method": "boiled",
            "expected_allergens": ["gluten", "soy"],
        },
        {
            "name": "小炒黄牛肉",
            "desc": "经典湖南小炒",
            "ingredients": ["牛肉", "辣椒", "葵花"],
            "tags": ["湖南"],
            "expected_cuisine": "hunan",
            "expected_flavor": "spicy",
            "expected_method": "fried",
            "expected_allergens": [],
        },
    ]
    all_ok = True
    for t in tests:
        raw = RawDish(
            source="xiachufang", source_id="1",
            name=t["name"], description=t["desc"],
            ingredients=t["ingredients"], tags=t["tags"],
            cuisine_type="", price=None, raw={},
        )
        dish = normalize_dish(raw, fallback_cuisine="restaurant")
        checks = [
            ("cuisine", dish.cuisine_type, t["expected_cuisine"]),
            ("flavor", dish.flavor_profile, t["expected_flavor"]),
            ("method", dish.cooking_method, t["expected_method"]),
        ]
        for allergen in t["expected_allergens"]:
            checks.append(("allergen", allergen in dish.allergens, True))

        failed = [c for c in checks if c[1] != c[2]]
        status = "PASS" if not failed else "FAIL"
        print(f"  [{status}] {t['name']}: cuisine={dish.cuisine_type}, flavor={dish.flavor_profile}, method={dish.cooking_method}, allergens={dish.allergens}")
        if failed:
            for name, got, expected in failed:
                print(f"         {name}: got {got!r}, expected {expected!r}")
            all_ok = False
    return all_ok


if __name__ == "__main__":
    print("=== Chinese Normalization Verification ===\n")

    print("1. File encoding check:")
    ok1 = check_file_encoding()

    print("\n2. Keyword byte verification:")
    ok2 = check_specific_keywords()

    print("\n3. Merchant category matching:")
    ok3 = check_merchant_matching()

    print("\n4. Dish normalization matching:")
    ok4 = check_dish_matching()

    print()
    all_ok = ok1 and ok2 and ok3 and ok4
    print(f"{'ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED'}")
    sys.exit(0 if all_ok else 1)
