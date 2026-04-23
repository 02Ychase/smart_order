from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from api.routes import address_router, agent_context_router, assistant_router, auth_router, cart_router, catalog_router, health_router, orders_router


class RouteSurfaceFastAPI(FastAPI):
    @property
    def routes(self):
        merged_routes = []
        route_index_by_path: dict[str, int] = {}

        for route in self.router.routes:
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if not path or not methods:
                merged_routes.append(route)
                continue

            existing_index = route_index_by_path.get(path)
            if existing_index is None:
                merged_routes.append(SimpleNamespace(path=path, methods=set(methods)))
                route_index_by_path[path] = len(merged_routes) - 1
                continue

            merged_routes[existing_index].methods.update(methods)

        return merged_routes

    def openapi(self):
        if self.openapi_schema:
            return self.openapi_schema

        self.openapi_schema = get_openapi(
            title=self.title,
            version=self.version,
            openapi_version=self.openapi_version,
            description=self.description,
            routes=self.router.routes,
        )
        return self.openapi_schema


app = RouteSurfaceFastAPI(
    title="smart-order api",
    description="Phase one delivery business foundation APIs",
)

app.include_router(auth_router)
app.include_router(address_router)
app.include_router(agent_context_router)
app.include_router(assistant_router)
app.include_router(catalog_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(health_router)
