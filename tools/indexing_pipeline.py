from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class IndexingPipeline:
    def __init__(self, catalog_service=None, vector_store=None) -> None:
        self._catalog = catalog_service
        self._vector_store = vector_store

    def run_full_sync(self) -> dict:
        if not self._vector_store or not self._vector_store.is_ready():
            logger.warning("Vector store not ready, skipping indexing")
            return {"merchants_indexed": 0, "dishes_indexed": 0}

        merchants = self._catalog.list_merchants()

        # Clear existing vectors before full sync
        logger.info("Clearing existing vectors before sync")
        self._vector_store.clear_namespace("merchants")
        self._vector_store.clear_namespace("dishes")

        merchant_candidates = []
        for m in merchants:
            text = self._merchant_to_text(m)
            merchant_candidates.append({
                "id": f"merchant:{m['id']}",
                "text": text,
                "metadata": {
                    "source_type": "merchant",
                    "source_id": m["id"],
                    "merchant_id": m["id"],
                    "merchant_name": m["name"],
                    "name": m["name"],
                    "description": m.get("description", ""),
                    "homepage_category": m.get("homepage_category", ""),
                    "merchant_tags": m.get("merchant_tags", []),
                    "phone": m.get("phone", ""),
                    "detailed_address": m.get("detailed_address", ""),
                    "business_hours": m.get("business_hours", ""),
                    "rating": m.get("rating", 0.0),
                },
            })

        dish_candidates = []
        for m in merchants:
            dishes = self._catalog.list_dishes_by_merchant(m["id"])
            for d in dishes:
                text = self._dish_to_text(d, m["name"])
                dish_candidates.append({
                    "id": f"dish:{d['id']}",
                    "text": text,
                    "metadata": {
                        "source_type": "dish",
                        "source_id": d["id"],
                        "dish_id": d["id"],
                        "dish_name": d["name"],
                        "merchant_id": d["merchant_id"],
                        "merchant_name": m["name"],
                        "price": d.get("price", 0.0),
                        "cuisine_type": d.get("cuisine_type", ""),
                        "flavor_profile": d.get("flavor_profile", ""),
                        "tags": d.get("tags", []),
                        "ingredients": d.get("ingredients", []),
                        "allergens": d.get("allergens", []),
                        "is_available": d.get("is_available", True),
                        "is_recommended": d.get("is_recommended", False),
                    },
                })

        if merchant_candidates:
            self._vector_store.upsert_candidates(merchant_candidates, namespace="merchants")
        if dish_candidates:
            self._vector_store.upsert_candidates(dish_candidates, namespace="dishes")

        stats = {
            "merchants_indexed": len(merchant_candidates),
            "dishes_indexed": len(dish_candidates),
        }
        logger.info("Indexing complete: %s", stats)
        return stats

    @staticmethod
    def _merchant_to_text(m: dict) -> str:
        parts = [
            m.get("name", ""),
            m.get("description", ""),
            " ".join(m.get("merchant_tags", [])),
        ]
        return " ".join(part for part in parts if part)

    @staticmethod
    def _dish_to_text(d: dict, merchant_name: str) -> str:
        parts = [
            d.get("name", ""),
            d.get("description", ""),
        ]
        return " ".join(part for part in parts if part)
