# Merchant Seed Realism Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace cloned merchant seed generation with curated merchant instances that preserve the existing payload contract while making merchant names and same-category menus meaningfully different.

**Architecture:** Keep the existing seed payload shape consumed by `tools/seed_catalog_data.py`, but stop generating merchants from `DISTRICT_POINTS × CUISINE_PROFILES`. Instead, define curated merchant instances directly in `database/seeds/merchant_seed_data.py`, each with its own copy and menu composition. Strengthen the seed tests first so they fail on numeric merchant names and identical same-category menus, then rewrite the seed data to satisfy those tests.

**Tech Stack:** Python, pytest, SQLAlchemy seed pipeline

---

## File Map

- `database/seeds/merchant_seed_data.py`
  - Replace the current `CUISINE_PROFILES` cloning model with curated merchant instances while preserving the payload keys used by `tools/seed_catalog_data.py`.
- `tests/database/test_merchant_seed_data.py`
  - Add realism-focused assertions for category coverage, name quality, and same-category menu differentiation.
- `tests/test_seed_payload.py`
  - Update stale count assertions and keep payload-shape guards aligned with the new curated dataset.
- `tools/seed_catalog_data.py`
  - No code change expected; this file is part of verification scope only because the payload contract must stay compatible.

### Task 1: Lock the new realism rules with failing tests

**Files:**
- Modify: `tests/database/test_merchant_seed_data.py`
- Modify: `tests/test_seed_payload.py`
- Test: `tests/database/test_merchant_seed_data.py`
- Test: `tests/test_seed_payload.py`

- [ ] **Step 1: Write the failing tests in `tests/database/test_merchant_seed_data.py`**

Replace the file body with this test module so the new rules are explicit before any seed rewrite:

```python
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
```

- [ ] **Step 2: Write the failing payload-shape checks in `tests/test_seed_payload.py`**

Replace the current test body with this version so the stale `== 20` assertion is removed and the new curated dataset still has enough structure:

```python
from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.seeds.merchant_seed_data import MERCHANT_SEED_DATA


def test_seed_payload_contains_realistic_multi_merchant_data() -> None:
    assert len(MERCHANT_SEED_DATA) >= 40
    assert len({merchant["district"] for merchant in MERCHANT_SEED_DATA}) == 5
    assert all(len(merchant["categories"]) >= 2 for merchant in MERCHANT_SEED_DATA)
    assert all(sum(len(category["dishes"]) for category in merchant["categories"]) >= 8 for merchant in MERCHANT_SEED_DATA)
    assert all(not re.search(r"\d", merchant["name"]) for merchant in MERCHANT_SEED_DATA)
```

- [ ] **Step 3: Run the targeted tests to verify they fail for the expected reasons**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/database/test_merchant_seed_data.py tests/test_seed_payload.py -q
```

Expected:
- FAIL because current merchant names still contain digits from `f"{district['district']}{profile['brand']}{profile_index}"`
- FAIL because same-category merchants still share identical menu signatures across districts
- FAIL because `tests/test_seed_payload.py` currently expects the old payload shape assumptions

- [ ] **Step 4: Commit the red-phase tests**

```bash
git add tests/database/test_merchant_seed_data.py tests/test_seed_payload.py
git commit -m "test: lock merchant seed realism rules"
```

### Task 2: Replace profile cloning with curated merchant instances

**Files:**
- Modify: `database/seeds/merchant_seed_data.py`
- Test: `tests/database/test_merchant_seed_data.py`
- Test: `tests/test_seed_payload.py`

- [ ] **Step 1: Replace the generator tail with a curated-instance structure**

Remove:
- `CUISINE_PROFILES`
- the nested `for district_index ... for profile_index ...` loop in `build_merchant_seed_data()`
- the numbered merchant-name expression at `database/seeds/merchant_seed_data.py:283`

Use this file shape instead:

```python
from copy import deepcopy

DISTRICT_POINTS = {
    "静安": {"address": "南京西路 818 号", "longitude": 121.4521, "latitude": 31.2291},
    "徐汇": {"address": "漕溪北路 399 号", "longitude": 121.4372, "latitude": 31.1948},
    "浦东": {"address": "张杨路 1088 号", "longitude": 121.5440, "latitude": 31.2282},
    "杨浦": {"address": "黄兴路 1888 号", "longitude": 121.5254, "latitude": 31.2990},
    "长宁": {"address": "长宁路 1018 号", "longitude": 121.4246, "latitude": 31.2202},
}


def clone_categories(categories: list[dict]) -> list[dict]:
    return deepcopy(categories)


def build_merchant_seed(
    *,
    name: str,
    description: str,
    district: str,
    homepage_category: str,
    promo_text: str,
    delivery_radius_meters: int,
    delivery_fee: float,
    min_order_amount: float,
    avg_delivery_minutes: int,
    rating: float,
    longitude_offset: float,
    latitude_offset: float,
    categories: list[dict],
) -> dict:
    district_meta = DISTRICT_POINTS[district]
    return {
        "name": name,
        "description": description,
        "city": "上海",
        "district": district,
        "address": district_meta["address"],
        "longitude": district_meta["longitude"] + longitude_offset,
        "latitude": district_meta["latitude"] + latitude_offset,
        "homepage_category": homepage_category,
        "promo_text": promo_text,
        "delivery_radius_meters": delivery_radius_meters,
        "delivery_fee": delivery_fee,
        "min_order_amount": min_order_amount,
        "avg_delivery_minutes": avg_delivery_minutes,
        "rating": rating,
        "categories": clone_categories(categories),
    }
```

- [ ] **Step 2: Add curated menu variants instead of one menu per category**

Group menus by homepage category, but define multiple variants per category so same-category merchants no longer share identical section/dish signatures.

Add data in this style near the top of the file:

```python
XIANGCAI_HOME_STYLE = [
    {
        "name": "现炒小碗菜",
        "dishes": [
            {"name": "辣椒炒肉", "description": "鲜辣下饭", "price": 29.0, "tags": "湘菜,热卖", "is_recommended": True},
            {"name": "攸县香干炒肉", "description": "豆香浓郁", "price": 31.0, "tags": "湘菜,家常", "is_recommended": False},
            {"name": "外婆菜炒鸡蛋", "description": "咸鲜开胃", "price": 24.0, "tags": "下饭", "is_recommended": False},
            {"name": "小炒黄牛肉", "description": "锅气足", "price": 42.0, "tags": "招牌", "is_recommended": True},
        ],
    },
    {
        "name": "配饭小吃",
        "dishes": [
            {"name": "红糖糍粑", "description": "外脆内糯", "price": 12.0, "tags": "甜口", "is_recommended": False},
            {"name": "酸梅汤", "description": "解辣清爽", "price": 8.0, "tags": "饮品", "is_recommended": False},
            {"name": "米饭", "description": "现煮香米", "price": 2.0, "tags": "主食", "is_recommended": False},
            {"name": "擂椒皮蛋", "description": "香辣软嫩", "price": 16.0, "tags": "凉菜", "is_recommended": False},
        ],
    },
]

XIANGCAI_CLAYPOT = [
    {
        "name": "砂锅下饭菜",
        "dishes": [
            {"name": "砂锅豆腐", "description": "热乎入味", "price": 26.0, "tags": "砂锅", "is_recommended": False},
            {"name": "干锅肥肠", "description": "香辣浓郁", "price": 46.0, "tags": "干锅,招牌", "is_recommended": True},
            {"name": "农家一碗香", "description": "蛋香肉香", "price": 33.0, "tags": "湘菜", "is_recommended": True},
            {"name": "剁椒鱼块", "description": "鲜辣开胃", "price": 38.0, "tags": "剁椒", "is_recommended": False},
        ],
    },
    {
        "name": "热卤配菜",
        "dishes": [
            {"name": "卤香海带结", "description": "微辣入味", "price": 9.0, "tags": "配菜", "is_recommended": False},
            {"name": "酸豆角肉沫", "description": "酸香搭饭", "price": 14.0, "tags": "小炒", "is_recommended": False},
            {"name": "老长沙冰粉", "description": "爽口收尾", "price": 10.0, "tags": "甜品", "is_recommended": False},
            {"name": "米饭", "description": "热米饭", "price": 2.0, "tags": "主食", "is_recommended": False},
        ],
    },
]

LIGHT_MEAL_FITNESS = [
    {
        "name": "高蛋白能量碗",
        "dishes": [
            {"name": "香煎鸡胸藜麦碗", "description": "清爽饱腹", "price": 33.0, "tags": "轻食,高蛋白", "is_recommended": True},
            {"name": "牛肉南瓜能量碗", "description": "低负担饱腹", "price": 37.0, "tags": "轻食", "is_recommended": True},
            {"name": "椒香鸡腿温沙拉", "description": "热食更满足", "price": 35.0, "tags": "沙拉", "is_recommended": False},
            {"name": "豆腐鹰嘴豆碗", "description": "植物蛋白", "price": 28.0, "tags": "素食", "is_recommended": False},
        ],
    },
    {
        "name": "轻饮加餐",
        "dishes": [
            {"name": "冷萃美式", "description": "无糖提神", "price": 14.0, "tags": "咖啡", "is_recommended": False},
            {"name": "希腊酸奶杯", "description": "水果坚果搭配", "price": 16.0, "tags": "酸奶", "is_recommended": False},
            {"name": "羽衣甘蓝果昔", "description": "清爽顺口", "price": 18.0, "tags": "饮品", "is_recommended": False},
            {"name": "牛油果鲜虾卷", "description": "轻盈不寡淡", "price": 26.0, "tags": "卷饼", "is_recommended": True},
        ],
    },
]
```

Build the rest of the categories with the same pattern so each of the eight homepage categories has at least two distinct menu signatures. For the remaining categories, keep the prior homepage categories but rewrite the dish lists to create differentiated stores:
- `咖啡甜品`: espresso+bakehouse variant and dessert-first afternoon-tea variant
- `炸鸡汉堡`: burger-combo variant and fried-snack-sharing variant
- `粥面`: breakfast congee variant and late-night noodle/wonton variant
- `日韩料理`: donburi/sushi variant and curry/snack variant
- `麻辣烫`: soup-base variant and dry-mix/málàbàn variant
- `披萨意面`: pizza+pasta variant and baked-rice+snack variant

- [ ] **Step 3: Define the merchant roster explicitly instead of cloning by district**

Replace `build_merchant_seed_data()` with a direct list of curated merchants that references the menu variants above. Keep roughly five merchants per homepage category so the total stays at or above forty.

Use this roster format and these concrete names as the base list:

```python
MERCHANT_SEED_DATA = [
    build_merchant_seed(
        name="兰姨小炒",
        description="主打现炒湘味下饭菜，适合工作日午晚餐",
        district="静安",
        homepage_category="湘菜",
        promo_text="双人下饭套餐立减 10 元",
        delivery_radius_meters=3200,
        delivery_fee=4.0,
        min_order_amount=20.0,
        avg_delivery_minutes=28,
        rating=4.7,
        longitude_offset=0.001,
        latitude_offset=0.001,
        categories=XIANGCAI_HOME_STYLE,
    ),
    build_merchant_seed(
        name="洞庭食堂",
        description="偏重砂锅和剁椒热菜，晚餐订单更集中",
        district="徐汇",
        homepage_category="湘菜",
        promo_text="招牌热菜第二件半价",
        delivery_radius_meters=3300,
        delivery_fee=4.0,
        min_order_amount=22.0,
        avg_delivery_minutes=31,
        rating=4.6,
        longitude_offset=0.002,
        latitude_offset=0.001,
        categories=XIANGCAI_CLAYPOT,
    ),
    build_merchant_seed(
        name="谷粒厨房",
        description="高蛋白轻食工作餐，主打热食能量碗",
        district="浦东",
        homepage_category="轻食",
        promo_text="午间轻食套餐减 8 元",
        delivery_radius_meters=2800,
        delivery_fee=5.0,
        min_order_amount=26.0,
        avg_delivery_minutes=29,
        rating=4.7,
        longitude_offset=0.001,
        latitude_offset=0.002,
        categories=LIGHT_MEAL_FITNESS,
    ),
]
```

Expand that list so it contains at least these merchant names, grouped by category:

- `湘菜`: `兰姨小炒`, `洞庭食堂`, `下饭湘厨`, `火宫辣子馆`, `家味湘菜饭堂`
- `轻食`: `谷粒厨房`, `半勺轻食`, `日日鲜配`, `森活能量碗`, `晴天卷饼社`
- `咖啡甜品`: `午后豆房`, `奶油信箱`, `可可角落`, `慢烘实验室`, `甜屿茶点`
- `炸鸡汉堡`: `厚牛堡局`, `脆脆鸡食堂`, `街角汉堡铺`, `热浪炸物社`, `双层芝士屋`
- `粥面`: `阿福粥铺`, `深夜汤面`, `巷口面档`, `暖胃小馆`, `云吞早点铺`
- `日韩料理`: `元气食堂`, `海苔饭屋`, `照烧小厨`, `抹茶町`, `日和定食屋`
- `麻辣烫`: `川辣冒香锅`, `椒椒麻辣烫`, `骨汤烫铺`, `麻辣拌研究所`, `藤椒冒菜馆`
- `披萨意面`: `意面小站`, `芝士角`, `番茄厨房`, `薄脆披萨屋`, `焗饭事务所`

Rules while expanding the roster:
- do not put digits in any `name`
- keep the existing payload keys unchanged
- vary `promo_text`, `description`, `rating`, `avg_delivery_minutes`, and offsets so merchants do not read like clones
- reuse category cover behavior only at the frontend layer; no image field is needed here

- [ ] **Step 4: Run the tests to verify the seed rewrite passes**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/database/test_merchant_seed_data.py tests/test_seed_payload.py -q
```

Expected:
- PASS
- merchant count stays at `>= 40`
- no merchant names contain digits
- every homepage category remains covered
- same-category merchants have at least two menu signatures

- [ ] **Step 5: Commit the seed rewrite**

```bash
git add database/seeds/merchant_seed_data.py
git commit -m "feat: curate more realistic merchant seed data"
```

### Task 3: Verify the existing seed pipeline still accepts the payload contract

**Files:**
- Modify: none
- Verify: `tools/seed_catalog_data.py`
- Test: `tests/database/test_merchant_seed_data.py`
- Test: `tests/test_seed_payload.py`

- [ ] **Step 1: Re-read `tools/seed_catalog_data.py` and confirm the required payload keys are unchanged**

Verify the implementation still provides these keys for every merchant payload:

```python
required_keys = {
    "name",
    "description",
    "city",
    "district",
    "address",
    "longitude",
    "latitude",
    "homepage_category",
    "promo_text",
    "delivery_radius_meters",
    "delivery_fee",
    "min_order_amount",
    "avg_delivery_minutes",
    "rating",
    "categories",
}
```

- [ ] **Step 2: Run one final verification command over the focused seed tests**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/database/test_merchant_seed_data.py tests/test_seed_payload.py -q
```

Expected:
- PASS
- no schema changes required in `tools/seed_catalog_data.py`

- [ ] **Step 3: Commit the verification checkpoint**

```bash
git commit --allow-empty -m "chore: verify merchant seed payload compatibility"
```

## Self-Review Checklist

- Spec coverage:
  - numeric-free merchant names → covered in Task 1 tests + Task 2 roster rewrite
  - same-category menu differentiation → covered in Task 1 signature test + Task 2 menu variants
  - existing homepage category coverage → covered in Task 1 category test + Task 2 category roster
  - payload contract preservation → covered in Task 3 verification
- Placeholder scan:
  - no TBD/TODO markers remain
  - every code-changing step includes concrete code or exact merchant names/variants to implement
- Type consistency:
  - tests and implementation both use `MERCHANT_SEED_DATA`
  - menu differentiation uses the same `categories -> dishes` payload shape that `tools/seed_catalog_data.py` already consumes
