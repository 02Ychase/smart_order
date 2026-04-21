from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.user import User, UserAddress


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username))

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def create_user(self, username: str, password_hash: str, full_name: str, phone: str) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            phone=phone,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def list_addresses(self, user_id: int) -> list[UserAddress]:
        statement = (
            select(UserAddress)
            .where(UserAddress.user_id == user_id)
            .order_by(UserAddress.is_default.desc(), UserAddress.id.asc())
        )
        return list(self.session.scalars(statement))

    def get_address(self, user_id: int, address_id: int) -> UserAddress | None:
        statement = select(UserAddress).where(
            UserAddress.user_id == user_id,
            UserAddress.id == address_id,
        )
        return self.session.scalar(statement)

    def create_address(self, user_id: int, payload) -> UserAddress:
        if payload.is_default:
            for address in self.list_addresses(user_id):
                address.is_default = False

        address = UserAddress(user_id=user_id, **payload.model_dump())
        self.session.add(address)
        self.session.commit()
        self.session.refresh(address)
        return address

    def update_address(self, user_id: int, address_id: int, payload) -> UserAddress | None:
        address = self.get_address(user_id, address_id)
        if address is None:
            return None

        if payload.is_default:
            for candidate in self.list_addresses(user_id):
                candidate.is_default = candidate.id == address_id

        for field, value in payload.model_dump().items():
            setattr(address, field, value)

        self.session.commit()
        self.session.refresh(address)
        return address

    def set_default_address(self, user_id: int, address_id: int) -> UserAddress | None:
        address = self.get_address(user_id, address_id)
        if address is None:
            return None

        for candidate in self.list_addresses(user_id):
            candidate.is_default = candidate.id == address_id

        self.session.commit()
        self.session.refresh(address)
        return address

    def delete_address(self, user_id: int, address_id: int) -> bool:
        address = self.get_address(user_id, address_id)
        if address is None:
            return False

        self.session.delete(address)
        self.session.commit()
        return True
