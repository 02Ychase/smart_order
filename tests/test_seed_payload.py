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
