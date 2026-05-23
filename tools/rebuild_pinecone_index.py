"""Rebuild the smart-order-assistant Pinecone index after switching to BAAI/bge-m3 (1024-dim).

This script:
1. Deletes the old smart-order-assistant index (1536-dim)
2. Recreates it with the new dimension (1024)
3. Re-embeds all dishes and merchants from MySQL and upserts into Pinecone

Usage:
    python tools/rebuild_pinecone_index.py
    python tools/rebuild_pinecone_index.py --db-url "mysql+mysqlconnector://..."
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _delete_index_if_exists(pc, index_name: str) -> None:
    """Delete a Pinecone index if it exists."""
    if pc.has_index(index_name):
        logger.info("Deleting old index: %s", index_name)
        pc.delete_index(index_name)
        # Wait for deletion to complete
        for _ in range(30):
            if not pc.has_index(index_name):
                break
            time.sleep(1)
        logger.info("Index deleted: %s", index_name)
    else:
        logger.info("Index does not exist, skipping delete: %s", index_name)


def _create_index(pc, index_name: str, dimension: int, region: str) -> None:
    """Create a new Pinecone index with the given dimension."""
    from pinecone import ServerlessSpec

    logger.info("Creating index: %s (dim=%d)", index_name, dimension)
    pc.create_index(
        name=index_name,
        vector_type="dense",
        dimension=dimension,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=region),
    )
    # Wait for index to be ready
    for _ in range(60):
        if pc.has_index(index_name):
            break
        time.sleep(1)
    logger.info("Index created: %s", index_name)


def rebuild_assistant_index(db_url: str | None = None) -> None:
    """Rebuild the smart-order-assistant index used by RAG DenseVectorRecallRoute."""
    from pinecone import Pinecone

    from service.embedding import get_embedding_service

    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        logger.error("PINECONE_API_KEY not set, skipping assistant index rebuild")
        return

    index_name = os.getenv("PINECONE_ASSISTANT_INDEX", "smart-order-assistant")
    region = os.getenv("PINECONE_ENY", "us-east-1")
    svc = get_embedding_service()

    pc = Pinecone(api_key=api_key)

    # 1. Delete old index
    _delete_index_if_exists(pc, index_name)

    # 2. Create new index with correct dimension
    _create_index(pc, index_name, svc.dimension, region)

    # 3. Re-ingest data from database
    if db_url:
        os.environ["DATABASE_URL"] = db_url

    from sqlalchemy import select

    from api.db import SessionLocal
    from api.models.catalog import Dish, Merchant

    session = SessionLocal()
    try:
        # Query ALL dishes (including unavailable) directly via ORM
        dishes: list[Dish] = list(session.scalars(select(Dish).order_by(Dish.id)))
        # Query ALL merchants (including closed)
        merchants: list[Merchant] = list(session.scalars(select(Merchant).order_by(Merchant.id)))

        index = pc.Index(index_name)

        # Ingest dishes
        logger.info("Embedding %d dishes...", len(dishes))
        dish_texts = []
        dish_metas = []
        for dish in dishes:
            text = f"{dish.name} {dish.cuisine_type or ''} {dish.flavor_profile or ''} {dish.description or ''}"
            dish_texts.append(text.strip())
            dish_metas.append({
                "source_type": "dish",
                "source_id": dish.id,
                "dish_id": dish.id,
                "dish_name": dish.name,
                "price": float(dish.price),
                "cuisine_type": dish.cuisine_type or "",
                "flavor_profile": dish.flavor_profile or "",
                "description": dish.description or "",
                "merchant_id": dish.merchant_id,
                "is_available": dish.is_available,
                "content": text.strip(),
            })

        if dish_texts:
            vectors = svc.embed_batch(dish_texts, batch_size=32)
            batch = []
            for vec, meta in zip(vectors, dish_metas):
                batch.append((f"dish_{meta['source_id']}", vec, meta))
                if len(batch) >= 50:
                    index.upsert(vectors=batch, namespace="dishes")
                    batch = []
            if batch:
                index.upsert(vectors=batch, namespace="dishes")
            logger.info("Ingested %d dishes into namespace 'dishes'", len(dish_texts))

        # Ingest merchants
        logger.info("Embedding %d merchants...", len(merchants))
        merchant_texts = []
        merchant_metas = []
        for m in merchants:
            text = f"{m.name} {m.homepage_category or ''} {m.description or ''}"
            merchant_texts.append(text.strip())
            merchant_metas.append({
                "source_type": "merchant",
                "source_id": m.id,
                "merchant_id": m.id,
                "merchant_name": m.name,
                "homepage_category": m.homepage_category or "",
                "description": m.description or "",
                "merchant_rating": float(m.rating),
                "content": text.strip(),
            })

        if merchant_texts:
            vectors = svc.embed_batch(merchant_texts, batch_size=32)
            batch = []
            for vec, meta in zip(vectors, merchant_metas):
                batch.append((f"merchant_{meta['source_id']}", vec, meta))
                if len(batch) >= 50:
                    index.upsert(vectors=batch, namespace="merchants")
                    batch = []
            if batch:
                index.upsert(vectors=batch, namespace="merchants")
            logger.info("Ingested %d merchants into namespace 'merchants'", len(merchant_texts))

    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild Pinecone indexes for bge-m3")
    parser.add_argument("--db-url", type=str, default=None, help="SQLAlchemy DB URL")
    args = parser.parse_args()

    from service.embedding import get_embedding_service
    svc = get_embedding_service()
    logger.info("Using embedding model: %s (dim=%d)", svc.model_name, svc.dimension)

    logger.info("=== Rebuilding assistant index ===")
    rebuild_assistant_index(db_url=args.db_url)

    logger.info("Done!")


if __name__ == "__main__":
    main()
