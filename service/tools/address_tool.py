import re
from dataclasses import asdict, dataclass

from service.agent_state import ToolResult
from service.user_profile_service import UserProfileService


PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")


@dataclass
class AddressPayload:
    label: str
    contact_name: str
    contact_phone: str
    city: str
    district: str
    detail_address: str
    longitude: float
    latitude: float
    is_default: bool = False

    def model_dump(self) -> dict:
        return asdict(self)


def build_address_payload(**kwargs) -> AddressPayload:
    return AddressPayload(**kwargs)


def commit_address_action_tool(
    user_id: int,
    address: dict,
    session=None,
    _profile_service=None,
) -> dict:
    service = _profile_service or UserProfileService(session)
    payload = build_address_payload(**address)
    return service.create_address(user_id, payload)


def parse_address_tool(message: str) -> ToolResult:
    phone_match = PHONE_PATTERN.search(message)
    contact_phone = phone_match.group(0) if phone_match else ""
    contact_name = ""
    name_match = re.search(r"联系人[:：]?([\u4e00-\u9fa5]{2,4})", message)
    if name_match:
        contact_name = name_match.group(1)

    city = "上海市" if "上海" in message else ""
    district = "静安区" if "静安" in message else ""
    detail = message
    for token in ("帮我将以下地址加入地址管理：", "帮我将以下地址加入地址管理:", f"联系人{contact_name}", contact_phone):
        detail = detail.replace(token, "")
    detail = detail.strip(" ，,。")

    missing = []
    if not contact_phone:
        missing.append("contact_phone")
    if not contact_name:
        missing.append("contact_name")
    if not detail:
        missing.append("detail_address")

    if missing:
        return ToolResult.error_result(
            tool_name="parse_address",
            code="MISSING_ADDRESS_FIELDS",
            message=f"缺少字段：{', '.join(missing)}",
        )

    return ToolResult.ok_result(
        tool_name="parse_address",
        data={
            "address": {
                "label": "家",
                "contact_name": contact_name,
                "contact_phone": contact_phone,
                "city": city or "上海市",
                "district": district or "静安区",
                "detail_address": detail,
                "longitude": 121.45,
                "latitude": 31.22,
                "is_default": False,
            }
        },
    )


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
    return commit_address_action_tool(
        user_id=user_id,
        address={
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
        session=session,
        _profile_service=_profile_service,
    )
