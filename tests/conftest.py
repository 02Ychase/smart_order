from pathlib import Path
import sys

import pytest
from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def reset_api_sqlite_database(request):
    test_path = Path(str(request.node.fspath))
    if "tests\\api" not in str(test_path) and "tests/api" not in str(test_path):
        yield
        return

    module_engine = getattr(request.module, "engine", None)
    if module_engine is None:
        from api.db import engine as module_engine
    from api.models import Base

    if not module_engine.url.drivername.startswith("sqlite"):
        yield
        return

    Base.metadata.create_all(bind=module_engine)
    with module_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())

    app = getattr(request.module, "app", None)
    override_keys = []
    if app is not None:
        for module_name in (
            "api.routes.addresses",
            "api.routes.assistant",
            "api.routes.auth",
            "api.routes.cart",
            "api.routes.catalog",
            "api.routes.orders",
        ):
            route_module = sys.modules.get(module_name)
            dependency = getattr(route_module, "get_db_session", None)
            if dependency is None:
                continue
            app.dependency_overrides[dependency] = _session_override(module_engine)
            override_keys.append(dependency)

    try:
        yield
    finally:
        if app is not None:
            for dependency in override_keys:
                app.dependency_overrides.pop(dependency, None)


def _session_override(engine):
    def override():
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    return override
