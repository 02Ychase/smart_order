from service.user_profile_service import UserProfileService


def save_address_tool(
    user_id: int,
    label: str,
    contact_name: str,
    contact_phone: str,
    city: str,
    district: str,
    detail_address: str,
    longitude: float,
    latitude: float,
    is_default: bool = False,
    session=None,
    _profile_service=None,
) -> dict:
    """Save a new delivery address for the user.

    Args:
        user_id: The user's ID
        label: Address label (e.g., 'home', 'work')
        contact_name: Contact person's name
        contact_phone: Contact phone number
        city: City name
        district: District name
        detail_address: Detailed street address
        longitude: Address longitude
        latitude: Address latitude
        is_default: Whether to set as default address
        session: SQLAlchemy session (injected by caller)
        _profile_service: Optional mock for testing
    """
    service = _profile_service or UserProfileService(session)
    payload = type(
        "AddressPayload",
        (),
        {
            "label": label,
            "contact_name": contact_name,
            "contact_phone": contact_phone,
            "city": city,
            "district": district,
            "detail_address": detail_address,
            "longitude": longitude,
            "latitude": latitude,
            "is_default": is_default,
        },
    )()
    return service.create_address(user_id, payload)
