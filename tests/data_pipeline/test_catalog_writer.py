from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.models.catalog import Dish, DishCategory, Merchant
from api.models import Base
from data_pipeline.models import DishAssignment, NormalizedDish, NormalizedMerchant
from data_pipeline.storage.catalog_writer import CatalogWriter


def make_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def merchant(name="Sample Shop"):
    return NormalizedMerchant(
        source="amap", source_id=name, name=name, description="desc", city="Shanghai", district="Jingan",
        address="1 Road", longitude=121.1, latitude=31.1, homepage_category="面食", promo_text="promo",
        delivery_radius_meters=3000, delivery_fee=3, min_order_amount=20, avg_delivery_minutes=30,
        rating=4.6, phone="021", business_hours="10:00-22:00", detailed_address="1 Road",
        address_note="near gate", merchant_tags=["面食"],
    )


def dish(name="Beef Noodles"):
    return NormalizedDish(
        source="xiachufang", source_id=name, name=name, description="desc", price=28.0,
        tags=["面食"], cuisine_type="面食", flavor_profile="咸鲜", ingredients=["beef", "noodles"],
        allergens=["gluten"], cooking_method="煮", is_recommended=True,
    )


def test_catalog_writer_inserts_merchant_category_and_dish():
    session = make_session()
    writer = CatalogWriter(session)
    assignments = [DishAssignment(merchant=merchant(), category_name="Signature", dishes=[dish()])]

    summary = writer.write(assignments)

    assert summary.merchants_written == 1
    assert summary.categories_written == 1
    assert summary.dishes_written == 1
    assert session.scalar(select(Merchant).where(Merchant.name == "Sample Shop")) is not None
    assert session.scalar(select(DishCategory).where(DishCategory.name == "Signature")) is not None
    assert session.scalar(select(Dish).where(Dish.name == "Beef Noodles")) is not None


def test_catalog_writer_does_not_duplicate_existing_dish():
    session = make_session()
    writer = CatalogWriter(session)
    assignment = DishAssignment(merchant=merchant(), category_name="Signature", dishes=[dish()])

    writer.write([assignment])
    summary = writer.write([assignment])

    assert summary.merchants_written == 0
    assert summary.dishes_written == 0
    assert len(list(session.scalars(select(Dish)))) == 1
