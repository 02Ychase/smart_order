from api.routes.address import router as address_router
from api.routes.agent_context import router as agent_context_router
from api.routes.assistant import router as assistant_router
from api.routes.auth import router as auth_router
from api.routes.cart import router as cart_router
from api.routes.catalog import router as catalog_router
from api.routes.health import router as health_router
from api.routes.orders import router as orders_router

__all__ = ["address_router", "agent_context_router", "assistant_router", "auth_router", "cart_router", "catalog_router", "health_router", "orders_router"]
