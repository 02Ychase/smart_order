from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from repository.user_repository import UserRepository


class UserProfileService:
    def __init__(self, session: Session):
        self.users = UserRepository(session)

    def _serialize_address(self, address) -> dict:
        return {
            "id": address.id,
            "label": address.label,
            "contact_name": address.contact_name,
            "contact_phone": address.contact_phone,
            "city": address.city,
            "district": address.district,
            "detail_address": address.detail_address,
            "longitude": address.longitude,
            "latitude": address.latitude,
            "is_default": address.is_default,
        }

    def list_addresses(self, user_id: int) -> list[dict]:
        return [self._serialize_address(address) for address in self.users.list_addresses(user_id)]

    def create_address(self, user_id: int, payload) -> dict:
        return self._serialize_address(self.users.create_address(user_id, payload))

    def update_address(self, user_id: int, address_id: int, payload) -> dict:
        address = self.users.update_address(user_id, address_id, payload)
        if address is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="address not found")
        return self._serialize_address(address)

    def set_default_address(self, user_id: int, address_id: int) -> dict:
        address = self.users.set_default_address(user_id, address_id)
        if address is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="address not found")
        return {"success": True, "address_id": address.id}

    def delete_address(self, user_id: int, address_id: int) -> dict:
        deleted = self.users.delete_address(user_id, address_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="address not found")
        return {"success": True, "address_id": address_id}
