from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.db import SessionLocal
from api.models.catalog import Merchant, Dish, DishCategory


def remove_test_merchant():
    session = SessionLocal()
    try:
        test_merchants = session.query(Merchant).filter(
            Merchant.homepage_category == '品质精选'
        ).all()

        if not test_merchants:
            print("No test merchants found with homepage_category='品质精选'")
            return

        print(f"Found {len(test_merchants)} test merchant(s):")
        for merchant in test_merchants:
            print(f"  - ID: {merchant.id}, Name: {merchant.name}")

        confirm = input("\nDo you want to delete these merchants? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Deletion cancelled.")
            return

        for merchant in test_merchants:
            session.query(Dish).filter(Dish.merchant_id == merchant.id).delete()
            session.query(DishCategory).filter(DishCategory.merchant_id == merchant.id).delete()
            session.delete(merchant)

        session.commit()
        print(f"\nSuccessfully deleted {len(test_merchants)} test merchant(s).")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    remove_test_merchant()