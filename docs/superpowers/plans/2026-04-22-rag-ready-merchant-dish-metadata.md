# RAG-Ready Merchant & Dish Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand merchant and dish schema, seed payloads, and catalog APIs so the demo dataset exposes richer structured metadata for later RAG retrieval.

**Architecture:** Extend the existing `Merchant` and `Dish` tables directly instead of creating side tables. Keep `database/seeds/merchant_seed_data.py` as the single authored source of merchant and dish metadata, update `tools/seed_catalog_data.py` to persist the richer payload, and expose the new fields through the existing catalog routes. Store array-like fields as JSON-backed columns when possible so the API contract can return `list[str]` values directly.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, MySQL, pytest

---

## File Map

- Create: `database/migrations/versions/20260422_01_rag_metadata_expansion.py`
  - Add the new merchant and dish metadata columns to the existing schema.
- Modify: `api/models/catalog.py`
  - Extend `Merchant` and `Dish` ORM models with the new metadata fields.
- Modify: `api/schemas.py`
  - Extend merchant and dish response models so the new metadata is serialized by the API.
- Modify: `service/catalog_service.py`
  - Map the new ORM fields into API response dictionaries.
- Modify: `database/seeds/merchant_seed_data.py`
  - Expand merchant and dish payloads with structured metadata.
- Modify: `tools/seed_catalog_data.py`
  - Persist the richer merchant and dish payload fields into the database.
- Modify: `tests/api/test_catalog_routes.py`
  - Add contract coverage for the new merchant and dish API fields.
- Modify: `tests/database/test_merchant_seed_data.py`
  - Add richer realism and metadata assertions for merchant and dish seed payloads.
- Modify: `tests/test_seed_payload.py`
  - Add payload-shape checks for the new structured fields.
- Verify: `tests/test_alembic_env.py`
  - No code change expected; keep this in verification scope because migrations still rely on `.env` / environment DB resolution.
- Verify: `tools/seed_demo_data.py`
  - No code change expected; it should still reseed the runtime catalog through `seed_catalog(session)`.

### Task 1: Lock the richer merchant and dish API contract with failing tests

**Files:**
- Modify: `tests/api/test_catalog_routes.py`
- Test: `tests/api/test_catalog_routes.py`

- [ ] **Step 1: Add a failing merchant summary API test**

Insert this test after `test_list_merchants_returns_homepage_card_fields` in `tests/api/test_catalog_routes.py`:

```python
def test_list_merchants_returns_rag_ready_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        catalog_routes.CatalogService,
        "list_merchants",
        lambda self, district=None: [
            {
                "id": 1,
                "name": "兰姨小炒",
                "description": "主打现炒湘味下饭菜，适合工作日午晚餐",
                "district": "静安",
                "homepage_category": "湘菜",
                "promo_text": "双人下饭套餐立减10元",
                "delivery_fee": 4.0,
                "min_order_amount": 20.0,
                "avg_delivery_minutes": 28,
                "rating": 4.7,
                "phone": "021-62581234",
                "business_hours": "10:00-21:30",
                "detailed_address": "南京西路818号818广场B座1层105室",
                "address_note": "近2号线南京西路站1号口",
                "merchant_tags": ["写字楼午餐", "现炒", "下饭菜"],
            }
        ],
    )

    response = client.get("/catalog/merchants")

    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["phone"] == "021-62581234"
    assert payload["business_hours"] == "10:00-21:30"
    assert payload["detailed_address"] == "南京西路818号818广场B座1层105室"
    assert payload["address_note"] == "近2号线南京西路站1号口"
    assert payload["merchant_tags"] == ["写字楼午餐", "现炒", "下饭菜"]
```

- [ ] **Step 2: Add a failing dishes API test for structured culinary metadata**

Insert this test after `test_list_dishes_returns_recommended_and_tag_lists` in `tests/api/test_catalog_routes.py`:

```python
def test_list_dishes_returns_structured_rag_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        catalog_routes.CatalogService,
        "list_dishes_by_merchant",
        lambda self, merchant_id: [
            {
                "id": 11,
                "merchant_id": merchant_id,
                "category_id": 2,
                "name": "宫保鸡丁",
                "description": "经典川菜，鸡肉丁配花生米，酸甜微辣，口感丰富",
                "price": 28.0,
                "tags": ["招牌", "下饭"],
                "is_recommended": True,
                "cuisine_type": "川菜",
                "flavor_profile": "酸甜微辣",
                "ingredients": ["鸡胸肉", "花生米", "青椒", "红椒", "葱段"],
                "allergens": ["花生", "可能含有麸质"],
                "cooking_method": "爆炒",
            }
        ],
    )

    response = client.get("/catalog/merchants/1/dishes")

    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["cuisine_type"] == "川菜"
    assert payload["flavor_profile"] == "酸甜微辣"
    assert payload["ingredients"] == ["鸡胸肉", "花生米", "青椒", "红椒", "葱段"]
    assert payload["allergens"] == ["花生", "可能含有麸质"]
    assert payload["cooking_method"] == "爆炒"
```

- [ ] **Step 3: Add a failing real-row merchant response test**

In `tests/api/test_catalog_routes.py`, update `test_list_merchants_returns_homepage_card_fields_from_real_rows` so the inserted `Merchant(...)` includes the new fields and the assertions verify they round-trip:

```python
        merchant = Merchant(
            name=f"测试商户-{suffix}",
            description="现炒快餐",
            city="上海",
            district="静安",
            address="南京西路 100 号",
            longitude=121.4737,
            latitude=31.2304,
            homepage_category="品质精选",
            promo_text="新店立减 8 元",
            delivery_radius_meters=3000,
            delivery_fee=Decimal("5.00"),
            min_order_amount=Decimal("20.00"),
            avg_delivery_minutes=30,
            rating=Decimal("4.90"),
            phone="021-63001234",
            business_hours="09:30-21:00",
            detailed_address="南京西路100号梅龙镇广场东区1层",
            address_note="近3号门电梯厅",
            merchant_tags='["商场店", "现炒"]',
            is_open=True,
            created_at=datetime.utcnow(),
        )
```

And append this assertion block:

```python
    assert any(
        item["name"] == f"测试商户-{suffix}"
        and item["phone"] == "021-63001234"
        and item["business_hours"] == "09:30-21:00"
        and item["detailed_address"] == "南京西路100号梅龙镇广场东区1层"
        and item["address_note"] == "近3号门电梯厅"
        and item["merchant_tags"] == ["商场店", "现炒"]
        for item in response.json()
    )
```

- [ ] **Step 4: Run the API route tests to verify they fail for the expected missing fields**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/api/test_catalog_routes.py -q
```

Expected:
- FAIL because `MerchantSummaryResponse` does not yet define `phone`, `business_hours`, `detailed_address`, `address_note`, or `merchant_tags`
- FAIL because `DishResponse` does not yet define `cuisine_type`, `flavor_profile`, `ingredients`, `allergens`, or `cooking_method`
- FAIL because `Merchant` ORM does not yet accept the new columns in the real-row test

- [ ] **Step 5: Commit the red API contract tests**

```bash
git add tests/api/test_catalog_routes.py
git commit -m "test: lock rag-ready catalog metadata contract"
```

### Task 2: Lock richer seed payload requirements with failing tests

**Files:**
- Modify: `tests/database/test_merchant_seed_data.py`
- Modify: `tests/test_seed_payload.py`
- Test: `tests/database/test_merchant_seed_data.py`
- Test: `tests/test_seed_payload.py`

- [ ] **Step 1: Add a failing merchant metadata seed test**

Append this test to `tests/database/test_merchant_seed_data.py`:

```python
def test_merchants_include_precise_operational_metadata() -> None:
    assert all(merchant["phone"].startswith("021-") for merchant in MERCHANT_SEED_DATA)
    assert all(merchant["business_hours"] for merchant in MERCHANT_SEED_DATA)
    assert all(merchant["detailed_address"] for merchant in MERCHANT_SEED_DATA)
    assert all(merchant["address_note"] for merchant in MERCHANT_SEED_DATA)
    assert all(isinstance(merchant["merchant_tags"], list) and merchant["merchant_tags"] for merchant in MERCHANT_SEED_DATA)
```

- [ ] **Step 2: Add a failing dish metadata seed test**

Append this test to `tests/database/test_merchant_seed_data.py`:

```python
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
```

- [ ] **Step 3: Strengthen the payload shape test**

Replace the body of `tests/test_seed_payload.py` with this version:

```python
from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.seeds.merchant_seed_data import MERCHANT_SEED_DATA


def test_seed_payload_contains_rag_ready_catalog_metadata() -> None:
    assert len(MERCHANT_SEED_DATA) >= 40
    assert len({merchant["district"] for merchant in MERCHANT_SEED_DATA}) == 5
    assert all(not re.search(r"\d", merchant["name"]) for merchant in MERCHANT_SEED_DATA)
    assert all(merchant["phone"].startswith("021-") for merchant in MERCHANT_SEED_DATA)
    assert all(merchant["business_hours"] for merchant in MERCHANT_SEED_DATA)
    assert all(isinstance(merchant["merchant_tags"], list) for merchant in MERCHANT_SEED_DATA)
    assert all(len(merchant["categories"]) >= 2 for merchant in MERCHANT_SEED_DATA)
    assert all(sum(len(category["dishes"]) for category in merchant["categories"]) >= 8 for merchant in MERCHANT_SEED_DATA)
    assert all(
        all(isinstance(dish["ingredients"], list) for dish in category["dishes"])
        for merchant in MERCHANT_SEED_DATA
        for category in merchant["categories"]
    )
```

- [ ] **Step 4: Run the seed tests to verify they fail before implementation**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/database/test_merchant_seed_data.py tests/test_seed_payload.py -q
```

Expected:
- FAIL because merchants do not yet include `phone`, `business_hours`, `detailed_address`, `address_note`, or `merchant_tags`
- FAIL because dishes do not yet include `cuisine_type`, `flavor_profile`, `ingredients`, `allergens`, or `cooking_method`

- [ ] **Step 5: Commit the red seed tests**

```bash
git add tests/database/test_merchant_seed_data.py tests/test_seed_payload.py
git commit -m "test: lock rag-ready seed metadata rules"
```

### Task 3: Add schema support for structured merchant and dish metadata

**Files:**
- Create: `database/migrations/versions/20260422_01_rag_metadata_expansion.py`
- Modify: `api/models/catalog.py`
- Test: `tests/api/test_catalog_routes.py`
- Verify: `tests/test_alembic_env.py`

- [ ] **Step 1: Extend the ORM models in `api/models/catalog.py`**

Update imports and model fields as follows:

```python
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
```

Add these `Merchant` columns after `rating`:

```python
    phone: Mapped[str] = mapped_column(String(32), default="")
    business_hours: Mapped[str] = mapped_column(String(64), default="")
    detailed_address: Mapped[str] = mapped_column(Text, default="")
    address_note: Mapped[str] = mapped_column(String(128), default="")
    merchant_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
```

Add these `Dish` columns after `tags`:

```python
    cuisine_type: Mapped[str] = mapped_column(String(64), default="")
    flavor_profile: Mapped[str] = mapped_column(String(64), default="")
    ingredients: Mapped[list[str]] = mapped_column(JSON, default=list)
    allergens: Mapped[list[str]] = mapped_column(JSON, default=list)
    cooking_method: Mapped[str] = mapped_column(String(64), default="")
```

- [ ] **Step 2: Create the Alembic migration file**

Create `database/migrations/versions/20260422_01_rag_metadata_expansion.py` with this body:

```python
from alembic import op
import sqlalchemy as sa


revision = "20260422_01"
down_revision = "20260420_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("merchants", sa.Column("phone", sa.String(length=32), nullable=False, server_default=""))
    op.add_column("merchants", sa.Column("business_hours", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("merchants", sa.Column("detailed_address", sa.Text(), nullable=False, server_default=""))
    op.add_column("merchants", sa.Column("address_note", sa.String(length=128), nullable=False, server_default=""))
    op.add_column("merchants", sa.Column("merchant_tags", sa.JSON(), nullable=False, server_default=sa.text("('[]')")))

    op.add_column("dishes", sa.Column("cuisine_type", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("dishes", sa.Column("flavor_profile", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("dishes", sa.Column("ingredients", sa.JSON(), nullable=False, server_default=sa.text("('[]')")))
    op.add_column("dishes", sa.Column("allergens", sa.JSON(), nullable=False, server_default=sa.text("('[]')")))
    op.add_column("dishes", sa.Column("cooking_method", sa.String(length=64), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("dishes", "cooking_method")
    op.drop_column("dishes", "allergens")
    op.drop_column("dishes", "ingredients")
    op.drop_column("dishes", "flavor_profile")
    op.drop_column("dishes", "cuisine_type")

    op.drop_column("merchants", "merchant_tags")
    op.drop_column("merchants", "address_note")
    op.drop_column("merchants", "detailed_address")
    op.drop_column("merchants", "business_hours")
    op.drop_column("merchants", "phone")
```

- [ ] **Step 3: Run the catalog route tests to prove the ORM/migration layer unblocks the real-row merchant test failure**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/api/test_catalog_routes.py -q
```

Expected:
- Some tests may still fail because response schemas and service mapping are not updated yet
- The `Merchant(...) got an unexpected keyword argument` failure should be gone

- [ ] **Step 4: Run the Alembic environment checks**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/test_alembic_env.py -q
```

Expected:
- PASS
- Migration environment still resolves DB URLs correctly after the new revision is added

- [ ] **Step 5: Commit the schema layer**

```bash
git add api/models/catalog.py database/migrations/versions/20260422_01_rag_metadata_expansion.py
git commit -m "feat: add rag-ready catalog metadata fields"
```

### Task 4: Expose the new metadata through the catalog API

**Files:**
- Modify: `api/schemas.py`
- Modify: `service/catalog_service.py`
- Modify: `tests/api/test_catalog_routes.py`
- Test: `tests/api/test_catalog_routes.py`

- [ ] **Step 1: Extend the response schemas in `api/schemas.py`**

Update `MerchantSummaryResponse` to:

```python
class MerchantSummaryResponse(BaseModel):
    id: int
    name: str
    description: str
    district: str
    homepage_category: str
    promo_text: str
    delivery_fee: float
    min_order_amount: float
    avg_delivery_minutes: int
    rating: float
    phone: str
    business_hours: str
    detailed_address: str
    address_note: str
    merchant_tags: list[str]
```

Update `DishResponse` to:

```python
class DishResponse(BaseModel):
    id: int
    merchant_id: int
    category_id: int
    name: str
    description: str
    price: float
    tags: list[str]
    is_recommended: bool
    cuisine_type: str
    flavor_profile: str
    ingredients: list[str]
    allergens: list[str]
    cooking_method: str
```

- [ ] **Step 2: Extend the merchant mapping in `service/catalog_service.py`**

Replace the merchant dict returned in `list_merchants` with:

```python
            {
                "id": merchant.id,
                "name": merchant.name,
                "description": merchant.description,
                "district": merchant.district,
                "homepage_category": merchant.homepage_category,
                "promo_text": merchant.promo_text or merchant.description,
                "delivery_fee": float(merchant.delivery_fee),
                "min_order_amount": float(merchant.min_order_amount),
                "avg_delivery_minutes": merchant.avg_delivery_minutes,
                "rating": float(merchant.rating),
                "phone": merchant.phone,
                "business_hours": merchant.business_hours,
                "detailed_address": merchant.detailed_address,
                "address_note": merchant.address_note,
                "merchant_tags": list(merchant.merchant_tags or []),
            }
```

- [ ] **Step 3: Extend the dish mapping in `service/catalog_service.py`**

Replace the dish dict returned in `list_dishes_by_merchant` with:

```python
            {
                "id": dish.id,
                "merchant_id": dish.merchant_id,
                "category_id": dish.category_id,
                "name": dish.name,
                "description": dish.description,
                "price": float(dish.price),
                "tags": [tag for tag in dish.tags.split(",") if tag],
                "is_recommended": dish.is_recommended,
                "cuisine_type": dish.cuisine_type,
                "flavor_profile": dish.flavor_profile,
                "ingredients": list(dish.ingredients or []),
                "allergens": list(dish.allergens or []),
                "cooking_method": dish.cooking_method,
            }
```

- [ ] **Step 4: Run the catalog route tests until the new API contract passes**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/api/test_catalog_routes.py -q
```

Expected:
- PASS
- Merchant route tests now include the new metadata fields
- Dish route tests now include structured arrays in the response

- [ ] **Step 5: Commit the API response layer**

```bash
git add api/schemas.py service/catalog_service.py tests/api/test_catalog_routes.py
git commit -m "feat: expose rag-ready catalog metadata"
```

### Task 5: Expand the seed payloads and catalog seeding pipeline

**Files:**
- Modify: `database/seeds/merchant_seed_data.py`
- Modify: `tools/seed_catalog_data.py`
- Modify: `tests/database/test_merchant_seed_data.py`
- Modify: `tests/test_seed_payload.py`
- Test: `tests/database/test_merchant_seed_data.py`
- Test: `tests/test_seed_payload.py`

- [ ] **Step 1: Extend the seed helper functions in `database/seeds/merchant_seed_data.py`**

Change the `dish(...)` helper to:

```python
def dish(
    name: str,
    description: str,
    price: float,
    tags: str,
    cuisine_type: str,
    flavor_profile: str,
    ingredients: list[str],
    allergens: list[str],
    cooking_method: str,
    is_recommended: bool = False,
) -> dict:
    return {
        "name": name,
        "description": description,
        "price": price,
        "tags": tags,
        "cuisine_type": cuisine_type,
        "flavor_profile": flavor_profile,
        "ingredients": ingredients,
        "allergens": allergens,
        "cooking_method": cooking_method,
        "is_recommended": is_recommended,
    }
```

Change `build_merchant_seed(...)` to accept and persist the new merchant fields:

```python
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
    phone: str,
    business_hours: str,
    detailed_address: str,
    address_note: str,
    merchant_tags: list[str],
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
        "phone": phone,
        "business_hours": business_hours,
        "detailed_address": detailed_address,
        "address_note": address_note,
        "merchant_tags": merchant_tags,
        "categories": clone_categories(categories),
    }
```

- [ ] **Step 2: Upgrade one full menu variant as the pattern to follow**

Convert the first four dishes inside `XIANGCAI_HOME_STYLE` to this richer structure:

```python
XIANGCAI_HOME_STYLE = [
    section(
        "现炒小碗菜",
        [
            dish(
                "辣椒炒肉",
                "经典湘味下饭菜，青红椒配五花肉快火翻炒，香辣开胃",
                29.0,
                "湘菜,热卖",
                "湘菜",
                "香辣",
                ["五花肉", "青椒", "红椒", "蒜片"],
                [],
                "爆炒",
                True,
            ),
            dish(
                "攸县香干炒肉",
                "豆香和肉香融合，口感紧实有嚼劲，适合配饭",
                31.0,
                "湘菜,家常",
                "湘菜",
                "咸鲜微辣",
                ["香干", "猪肉", "青椒", "蒜苗"],
                ["大豆"],
                "爆炒",
            ),
            dish(
                "外婆菜炒鸡蛋",
                "咸鲜脆爽，发酵菜香明显，是工作餐常点配菜",
                24.0,
                "下饭",
                "湘菜",
                "咸鲜",
                ["外婆菜", "鸡蛋", "蒜末", "小米椒"],
                ["鸡蛋"],
                "爆炒",
            ),
            dish(
                "小炒黄牛肉",
                "牛肉片搭小米椒和芹菜大火快炒，锅气足、香辣突出",
                42.0,
                "招牌",
                "湘菜",
                "香辣",
                ["黄牛肉", "芹菜", "小米椒", "蒜末"],
                [],
                "爆炒",
                True,
            ),
        ],
    ),
```

Then apply the same field pattern to the rest of the seed file. Rules while expanding:
- every merchant gets unique `phone`, `business_hours`, `detailed_address`, `address_note`, and a non-empty `merchant_tags`
- every dish gets non-empty `cuisine_type`, `flavor_profile`, `ingredients`, `allergens`, and `cooking_method`
- keep merchant names free of digits
- continue to differentiate same-category merchants and menus semantically

- [ ] **Step 3: Update `tools/seed_catalog_data.py` to persist the new fields**

In the merchant insert block, add:

```python
            phone=merchant_payload["phone"],
            business_hours=merchant_payload["business_hours"],
            detailed_address=merchant_payload["detailed_address"],
            address_note=merchant_payload["address_note"],
            merchant_tags=merchant_payload["merchant_tags"],
```

In the dish insert block, add:

```python
                        cuisine_type=dish_payload["cuisine_type"],
                        flavor_profile=dish_payload["flavor_profile"],
                        ingredients=dish_payload["ingredients"],
                        allergens=dish_payload["allergens"],
                        cooking_method=dish_payload["cooking_method"],
```

- [ ] **Step 4: Run the seed payload tests until they pass**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/database/test_merchant_seed_data.py tests/test_seed_payload.py -q
```

Expected:
- PASS
- Merchant payloads include the richer operational fields
- Dish payloads include structured metadata fields

- [ ] **Step 5: Commit the richer seed layer**

```bash
git add database/seeds/merchant_seed_data.py tools/seed_catalog_data.py tests/database/test_merchant_seed_data.py tests/test_seed_payload.py
git commit -m "feat: enrich seeded merchant and dish metadata"
```

### Task 6: Verify migration and reseed against the active runtime database

**Files:**
- Modify: none
- Verify: `database/migrations/versions/20260422_01_rag_metadata_expansion.py`
- Verify: `tools/seed_demo_data.py`
- Test: `tests/api/test_catalog_routes.py`
- Test: `tests/database/test_merchant_seed_data.py`
- Test: `tests/test_seed_payload.py`

- [ ] **Step 1: Apply the migration to the configured runtime database**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" alembic upgrade head
```

Expected:
- PASS
- The active database gets the new merchant and dish columns

- [ ] **Step 2: Reseed the active runtime database**

Run:

```bash
PYTHONUTF8=1 python tools/seed_demo_data.py
```

Expected:
- `Seeded 40 merchants and one demo user`
- Catalog tables now contain the richer metadata

- [ ] **Step 3: Re-run the focused automated tests**

Run:

```bash
PYTHONPATH="D:/projects/smart_order/.worktrees/phase1-foundation" pytest tests/api/test_catalog_routes.py tests/database/test_merchant_seed_data.py tests/test_seed_payload.py tests/test_alembic_env.py -q
```

Expected:
- PASS

- [ ] **Step 4: Spot-check the live catalog API**

Run:

```bash
PYTHONUTF8=1 python - <<'PY'
import json
import urllib.request

with urllib.request.urlopen('http://127.0.0.1:8000/catalog/merchants', timeout=10) as response:
    merchants = json.load(response)

sample_merchant = merchants[0]
print({
    'name': sample_merchant['name'],
    'phone': sample_merchant['phone'],
    'business_hours': sample_merchant['business_hours'],
    'merchant_tags': sample_merchant['merchant_tags'],
})

merchant_id = sample_merchant['id']
with urllib.request.urlopen(f'http://127.0.0.1:8000/catalog/merchants/{merchant_id}/dishes', timeout=10) as response:
    dishes = json.load(response)

sample_dish = dishes[0]
print({
    'name': sample_dish['name'],
    'cuisine_type': sample_dish['cuisine_type'],
    'flavor_profile': sample_dish['flavor_profile'],
    'ingredients': sample_dish['ingredients'],
    'allergens': sample_dish['allergens'],
    'cooking_method': sample_dish['cooking_method'],
})
PY
```

Expected:
- Merchant output includes `phone`, `business_hours`, and `merchant_tags`
- Dish output includes structured arrays for `ingredients` and `allergens`

- [ ] **Step 5: Commit the verification checkpoint**

```bash
git commit --allow-empty -m "chore: verify rag-ready catalog metadata"
```

## Self-Review Checklist

- Spec coverage:
  - merchant operational metadata → covered in Tasks 1, 3, 4, 5, and 6
  - dish structured metadata → covered in Tasks 1, 3, 4, 5, and 6
  - API exposure of new fields → covered in Tasks 1 and 4
  - migration plus reseed workflow → covered in Tasks 3 and 6
  - backend-first scope control → maintained throughout; no frontend redesign tasks included
- Placeholder scan:
  - no TBD/TODO markers remain
  - each code-changing step includes concrete code or exact commands
  - each verification step names exact pytest/alembic/seed commands
- Type consistency:
  - `merchant_tags`, `ingredients`, and `allergens` are consistently treated as `list[str]`
  - merchant schema fields use `phone`, `business_hours`, `detailed_address`, `address_note`, `merchant_tags`
  - dish schema fields use `cuisine_type`, `flavor_profile`, `ingredients`, `allergens`, `cooking_method`
