from __future__ import annotations

from sqlalchemy.orm import Session

from service.catalog_service import CatalogService
from tools.assistant_vector_store import AssistantVectorStore
from tools.indexing_pipeline import IndexingPipeline


def sync_catalog_vectors(
    *,
    session: Session,
    catalog_service_cls=CatalogService,
    vector_store=None,
    pipeline_cls=IndexingPipeline,
) -> dict:
    catalog_service = catalog_service_cls(session)
    store = vector_store if vector_store is not None else AssistantVectorStore()
    pipeline = pipeline_cls(catalog_service=catalog_service, vector_store=store)
    return pipeline.run_full_sync()
