from tools.indexing_pipeline import IndexingPipeline


class FakeCatalogService:
    def list_merchants(self):
        return [
            {"id": 1, "name": "兰姨小炒", "description": "地道湘菜", "homepage_category": "湘菜",
             "merchant_tags": ["湘菜", "辣"], "phone": "13800001111", "detailed_address": "南京西路100号",
             "business_hours": "10:00-22:00", "rating": 4.7},
        ]

    def list_dishes_by_merchant(self, merchant_id):
        if merchant_id == 1:
            return [
                {"id": 11, "merchant_id": 1, "name": "小炒黄牛肉", "description": "鲜辣下饭",
                 "cuisine_type": "湘菜", "flavor_profile": "鲜辣", "price": 42.0,
                 "tags": ["湘菜", "辣"], "ingredients": ["牛肉", "辣椒"],
                 "allergens": [], "is_available": True, "is_recommended": True},
            ]
        return []


class FakeVectorStore:
    def __init__(self):
        self.upserted = []
        self._ready = True

    def is_ready(self):
        return self._ready

    def upsert_candidates(self, candidates, batch_size=30, namespace=""):
        self.upserted.extend([(c["id"], namespace) for c in candidates])
        return True


def test_pipeline_indexes_merchants_and_dishes():
    catalog = FakeCatalogService()
    vector_store = FakeVectorStore()
    pipeline = IndexingPipeline(catalog_service=catalog, vector_store=vector_store)

    stats = pipeline.run_full_sync()

    assert stats["merchants_indexed"] == 1
    assert stats["dishes_indexed"] == 1
    assert len(vector_store.upserted) == 2

    namespaces = {item[1] for item in vector_store.upserted}
    assert "merchants" in namespaces
    assert "dishes" in namespaces


def test_pipeline_skips_when_vector_store_not_ready():
    catalog = FakeCatalogService()
    vector_store = FakeVectorStore()
    vector_store._ready = False
    pipeline = IndexingPipeline(catalog_service=catalog, vector_store=vector_store)

    stats = pipeline.run_full_sync()
    assert stats["merchants_indexed"] == 0
    assert stats["dishes_indexed"] == 0
