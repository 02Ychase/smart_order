from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.db import SessionLocal
from api.models.user import User, UserAddress
from api.security import hash_password
from tools.seed_catalog_data import seed_catalog



def seed_demo_user(session) -> None:
    session.query(UserAddress).delete()
    session.query(User).delete()
    session.commit()

    demo_user = User(
        username="demo_user",
        password_hash=hash_password("demo123456"),
        full_name="演示用户",
        phone="13800000000",
    )
    session.add(demo_user)
    session.flush()

    session.add(
        UserAddress(
            user_id=demo_user.id,
            label="家",
            contact_name="演示用户",
            contact_phone="13800000000",
            city="上海",
            district="静安",
            detail_address="南京西路 818 号 12 楼",
            longitude=121.4521,
            latitude=31.2291,
            is_default=True,
        )
    )
    session.commit()



def main() -> None:
    session = SessionLocal()
    try:
        merchant_count = seed_catalog(session)
        seed_demo_user(session)
        print(f"Seeded {merchant_count} merchants and one demo user")
    finally:
        session.close()


if __name__ == "__main__":
    main()
