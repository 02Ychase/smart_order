from data_pipeline.config import PipelineConfig
from data_pipeline.models import NormalizedDish, NormalizedMerchant, RawDish, RawMerchant


def test_pipeline_config_defaults_to_tmp_outputs(monkeypatch):
    monkeypatch.delenv("AMAP_API_KEY", raising=False)
    config = PipelineConfig.from_env()

    assert config.amap_api_key == ""
    assert config.raw_dir.as_posix().endswith("tmp/data_pipeline")
    assert config.default_city == "上海"
    assert config.default_merchant_limit == 500
    assert config.default_dish_limit == 5000


def test_raw_and_normalized_models_hold_catalog_fields():
    merchant = RawMerchant(
        source="amap",
        source_id="B001",
        name="Sample Noodle Shop",
        city="Shanghai",
        district="Huangpu",
        address="1 Test Road",
        longitude=121.47,
        latitude=31.23,
        category="restaurant",
        phone="021-00000000",
        rating=4.6,
        tags=["noodles"],
        raw={"id": "B001"},
    )
    dish = RawDish(
        source="xiachufang",
        source_id="recipe-1",
        name="Beef Noodles",
        description="A real recipe record",
        ingredients=["beef", "noodles"],
        tags=["noodles"],
        cuisine_type="",
        price=None,
        raw={"name": "Beef Noodles"},
    )
    normalized_merchant = NormalizedMerchant.from_raw(
        merchant,
        homepage_category="noodles",
        description="Noodle shop in Huangpu",
        promo_text="Fresh noodles",
        business_hours="10:00-22:00",
        merchant_tags=["noodles", "quick meal"],
    )
    normalized_dish = NormalizedDish.from_raw(
        dish,
        cuisine_type="noodles",
        flavor_profile="savory",
        cooking_method="boiled",
        allergens=["gluten"],
        price=28.0,
        is_recommended=True,
    )

    assert normalized_merchant.name == "Sample Noodle Shop"
    assert normalized_merchant.delivery_radius_meters == 3000
    assert normalized_dish.name == "Beef Noodles"
    assert normalized_dish.price == 28.0
    assert normalized_dish.ingredients == ["beef", "noodles"]
