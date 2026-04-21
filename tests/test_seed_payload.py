from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.seeds.merchant_seed_data import MERCHANT_SEED_DATA


def test_seed_payload_contains_realistic_multi_merchant_data() -> None:
    assert len(MERCHANT_SEED_DATA) >= 40
    assert len({merchant["district"] for merchant in MERCHANT_SEED_DATA}) == 5
    assert all(len(merchant["categories"]) >= 2 for merchant in MERCHANT_SEED_DATA)
    assert all(sum(len(category["dishes"]) for category in merchant["categories"]) >= 8 for merchant in MERCHANT_SEED_DATA)
    assert all(not re.search(r"\d", merchant["name"]) for merchant in MERCHANT_SEED_DATA)
