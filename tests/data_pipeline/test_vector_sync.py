from data_pipeline.vector.sync import sync_catalog_vectors


class FakePipeline:
    def __init__(self, catalog_service=None, vector_store=None):
        self.catalog_service = catalog_service
        self.vector_store = vector_store

    def run_full_sync(self):
        return {"merchants_indexed": 2, "dishes_indexed": 5}


class FakeCatalogService:
    def __init__(self, session):
        self.session = session


class FakeVectorStore:
    def __init__(self):
        self.ready = True


def test_sync_catalog_vectors_reuses_existing_indexing_pipeline():
    stats = sync_catalog_vectors(
        session=object(),
        catalog_service_cls=FakeCatalogService,
        vector_store=FakeVectorStore(),
        pipeline_cls=FakePipeline,
    )

    assert stats == {"merchants_indexed": 2, "dishes_indexed": 5}
