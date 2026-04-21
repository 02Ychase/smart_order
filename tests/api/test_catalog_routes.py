from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
import os
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_DATABASE_PATH = PROJECT_ROOT / "test_catalog_routes.db"
TEST_DATABASE_PATH.unlink(missing_ok=True)

os.environ["JWT_SECRET_KEY"] = "test-phase1-secret"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"

from api.db import SessionLocal, engine
from api.main import app
from api.models import Base
from api.models.catalog import Merchant
from api.routes import catalog as catalog_routes
from repository.catalog_repository import CatalogRepository


Base.metadata.create_all(bind=engine)
client = TestClient(app, raise_server_exceptions=False)



def test_list_merchants_returns_summary_items(monkeypatch) -> None:
    monkeypatch.setattr(
        catalog_routes.CatalogService,
        "list_merchants",
        lambda self, district=None: [
            {
                "id": 1,
                "name": "川湘小馆",
                "description": "下饭川菜",
                "district": "静安",
                "homepage_category": "热销榜",
                "promo_text": "满39减12，招牌菜限时折扣",
                "delivery_fee": 4.0,
                "min_order_amount": 20.0,
                "avg_delivery_minutes": 28,
                "rating": 4.7,
                "phone": "021-62180001",
                "business_hours": "10:00-21:00",
                "detailed_address": "南京西路688号1层",
                "address_note": "近地铁口",
                "merchant_tags": ["现炒", "工作餐"],
            }
        ],
    )

    response = client.get("/catalog/merchants")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "川湘小馆"
    assert response.json()[0]["homepage_category"] == "热销榜"
    assert response.json()[0]["promo_text"] == "满39减12，招牌菜限时折扣"



def test_list_merchants_returns_homepage_card_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        CatalogRepository,
        "list_merchants",
        lambda self, district=None: [
            SimpleNamespace(
                id=1,
                name="川湘小馆",
                description="下饭川菜",
                district="静安",
                homepage_category="热销榜",
                promo_text="",
                delivery_fee=4.0,
                min_order_amount=20.0,
                avg_delivery_minutes=28,
                rating=4.7,
                phone="021-62180002",
                business_hours="10:30-21:30",
                detailed_address="南京西路700号1层",
                address_note="近商场东门",
                merchant_tags=["下饭菜", "工作餐"],
            )
        ],
    )

    response = client.get("/catalog/merchants")

    assert response.status_code == 200
    assert response.json()[0]["homepage_category"] == "热销榜"
    assert response.json()[0]["promo_text"] == "下饭川菜"



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



def test_list_merchants_returns_homepage_card_fields_from_real_rows() -> None:
    suffix = uuid4().hex[:8]
    with SessionLocal() as session:
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
            merchant_tags=["商场店", "现炒"],
            is_open=True,
            created_at=datetime.utcnow(),
        )
        session.add(merchant)
        session.commit()

    response = client.get("/catalog/merchants")

    assert response.status_code == 200
    assert any(
        item["name"] == f"测试商户-{suffix}"
        and item["homepage_category"] == "品质精选"
        and item["promo_text"] == "新店立减 8 元"
        and item["phone"] == "021-63001234"
        and item["business_hours"] == "09:30-21:00"
        and item["detailed_address"] == "南京西路100号梅龙镇广场东区1层"
        and item["address_note"] == "近3号门电梯厅"
        and item["merchant_tags"] == ["商场店", "现炒"]
        for item in response.json()
    )



def test_list_dishes_returns_recommended_and_tag_lists(monkeypatch) -> None:
    monkeypatch.setattr(
        catalog_routes.CatalogService,
        "list_dishes_by_merchant",
        lambda self, merchant_id: [
            {
                "id": 11,
                "merchant_id": merchant_id,
                "category_id": 2,
                "name": "鱼香肉丝",
                "description": "招牌热菜",
                "price": 28.0,
                "tags": ["招牌", "下饭"],
                "is_recommended": True,
                "cuisine_type": "川菜",
                "flavor_profile": "酸甜微辣",
                "ingredients": ["猪里脊", "木耳", "胡萝卜", "青椒"],
                "allergens": [],
                "cooking_method": "爆炒",
            }
        ],
    )

    response = client.get("/catalog/merchants/1/dishes")

    assert response.status_code == 200
    assert response.json()[0]["tags"] == ["招牌", "下饭"]



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
