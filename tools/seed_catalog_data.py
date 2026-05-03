from pathlib import Path
import sys

from sqlalchemy.orm import Session
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.models.catalog import Dish, DishCategory, Merchant
from api.models.cart import CartItem
from api.models.order import OrderItem, DeliveryQuote, MerchantOrder
from database.seeds.merchant_seed_data import MERCHANT_SEED_DATA



def seed_catalog(session: Session) -> int:
    session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    session.query(DeliveryQuote).delete()
    session.query(MerchantOrder).delete()
    session.query(OrderItem).delete()
    session.query(CartItem).delete()
    session.query(Dish).delete()
    session.query(DishCategory).delete()
    session.query(Merchant).delete()
    session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    session.commit()

    for merchant_payload in MERCHANT_SEED_DATA:
        merchant = Merchant(
            name=merchant_payload["name"],
            description=merchant_payload["description"],
            city=merchant_payload["city"],
            district=merchant_payload["district"],
            address=merchant_payload["address"],
            longitude=merchant_payload["longitude"],
            latitude=merchant_payload["latitude"],
            homepage_category=merchant_payload["homepage_category"],
            promo_text=merchant_payload["promo_text"],
            delivery_radius_meters=merchant_payload["delivery_radius_meters"],
            delivery_fee=merchant_payload["delivery_fee"],
            min_order_amount=merchant_payload["min_order_amount"],
            avg_delivery_minutes=merchant_payload["avg_delivery_minutes"],
            rating=merchant_payload["rating"],
            phone=merchant_payload["phone"],
            business_hours=merchant_payload["business_hours"],
            detailed_address=merchant_payload["detailed_address"],
            address_note=merchant_payload["address_note"],
            merchant_tags=merchant_payload["merchant_tags"],
        )
        session.add(merchant)
        session.flush()

        for sort_order, category_payload in enumerate(merchant_payload["categories"], start=1):
            category = DishCategory(
                merchant_id=merchant.id,
                name=category_payload["name"],
                sort_order=sort_order,
            )
            session.add(category)
            session.flush()

            for dish_payload in category_payload["dishes"]:
                session.add(
                    Dish(
                        merchant_id=merchant.id,
                        category_id=category.id,
                        name=dish_payload["name"],
                        description=dish_payload["description"],
                        price=dish_payload["price"],
                        tags=dish_payload["tags"],
                        cuisine_type=dish_payload["cuisine_type"],
                        flavor_profile=dish_payload["flavor_profile"],
                        ingredients=dish_payload["ingredients"],
                        allergens=dish_payload["allergens"],
                        cooking_method=dish_payload["cooking_method"],
                        is_recommended=dish_payload["is_recommended"],
                    )
                )

    session.commit()
    return len(MERCHANT_SEED_DATA)
