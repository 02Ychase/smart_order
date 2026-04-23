from typing import Literal

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = ""
    phone: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class CurrentUserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    phone: str


class AddressRequest(BaseModel):
    label: str
    contact_name: str
    contact_phone: str
    city: str
    district: str
    detail_address: str
    longitude: float
    latitude: float
    is_default: bool = Field(default=False)


class AddressResponse(AddressRequest):
    id: int


class AuthSessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    user: CurrentUserResponse
    addresses: list[AddressResponse]


class AddressActionResponse(BaseModel):
    success: bool
    address_id: int


class MerchantSummaryResponse(BaseModel):
    id: int
    name: str
    description: str
    district: str
    homepage_category: str
    promo_text: str
    delivery_fee: float
    min_order_amount: float
    avg_delivery_minutes: int
    rating: float
    phone: str
    business_hours: str
    detailed_address: str
    address_note: str
    merchant_tags: list[str]


class DishResponse(BaseModel):
    id: int
    merchant_id: int
    category_id: int
    name: str
    description: str
    price: float
    tags: list[str]
    is_recommended: bool
    cuisine_type: str
    flavor_profile: str
    ingredients: list[str]
    allergens: list[str]
    cooking_method: str


class CartMutationRequest(BaseModel):
    dish_id: int
    quantity: int = Field(ge=1)


class CheckoutPreviewRequest(BaseModel):
    address_id: int


class CheckoutItemResponse(BaseModel):
    dish_id: int
    dish_name: str
    quantity: int
    unit_price: float


class DeliveryQuoteResponse(BaseModel):
    merchant_id: int
    in_range: bool
    distance_meters: int
    estimated_minutes: int
    delivery_fee: float
    message: str


class CheckoutPreviewMerchantOrderResponse(BaseModel):
    merchant_id: int
    merchant_name: str
    items: list[CheckoutItemResponse]
    goods_amount: float
    delivery_amount: float
    payable_amount: float
    delivery_quote: DeliveryQuoteResponse


class CheckoutPreviewResponse(BaseModel):
    address_id: int
    address_snapshot: str
    merchant_orders: list[CheckoutPreviewMerchantOrderResponse]
    goods_amount: float
    delivery_amount: float
    payable_amount: float


class CheckoutOrderSummaryMerchantOrderResponse(BaseModel):
    merchant_order_id: int
    merchant_id: int
    merchant_name: str
    goods_amount: float
    delivery_amount: float
    payable_amount: float
    order_status: str
    delivery_quote: DeliveryQuoteResponse


class CheckoutOrderDetailMerchantOrderResponse(CheckoutOrderSummaryMerchantOrderResponse):
    items: list[CheckoutItemResponse]


class CheckoutOrderSummaryResponse(BaseModel):
    checkout_order_id: int
    address_snapshot: str
    goods_amount: float
    delivery_amount: float
    payable_amount: float
    payment_status: str
    order_status: str
    created_at: str
    merchant_orders: list[CheckoutOrderSummaryMerchantOrderResponse]


class CheckoutOrderDetailResponse(CheckoutOrderSummaryResponse):
    merchant_orders: list[CheckoutOrderDetailMerchantOrderResponse]


class MockPayRequest(BaseModel):
    checkout_order_id: int


class MockPayResponse(BaseModel):
    success: bool
    checkout_order_id: int
    payment_status: str
    order_status: str


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    session_id: str | None = None
    user_id: int | None = None


class AssistantConstraintResponse(BaseModel):
    query_type: Literal["recommendation", "comparison", "knowledge"]
    cuisine_types: list[str] = Field(default_factory=list)
    budget_max: float | None = None
    party_size: int | None = None
    exclude_allergens: list[str] = Field(default_factory=list)
    comparison_targets: list[str] = Field(default_factory=list)


class AssistantRecommendationResponse(BaseModel):
    source_type: Literal["dish", "merchant"]
    merchant_id: int
    merchant_name: str
    dish_id: int | None = None
    dish_name: str | None = None
    price: float | None = None
    reason: str


class AssistantComparisonResponse(BaseModel):
    merchant_id: int
    merchant_name: str
    summary: str
    highlights: list[str] = Field(default_factory=list)


class AssistantCitationResponse(BaseModel):
    source_type: Literal["dish", "merchant"]
    source_id: int
    title: str
    snippet: str


class AssistantChatResponse(BaseModel):
    session_id: str
    message: str
    response_type: Literal["greeting", "clarification", "action_pending", "action_completed", "recommendation", "comparison", "knowledge", "unsupported"] = "recommendation"
    needs_clarification: bool = False
    clarification_question: str | None = None
    extracted_constraints: AssistantConstraintResponse | None = None
    recommendations: list[AssistantRecommendationResponse] = Field(default_factory=list)
    comparisons: list[AssistantComparisonResponse] = Field(default_factory=list)
    citations: list[AssistantCitationResponse] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


class AssistantHealthResponse(BaseModel):
    status: str
    llm_ready: bool
    vector_store_ready: bool
    degraded_mode: bool


class HealthResponse(BaseModel):
    status: str
    service: str
