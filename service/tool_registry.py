from dataclasses import dataclass


@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: dict


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, callable] = {}
        self._schemas: dict[str, ToolSchema] = {}

    def register(self, schema: ToolSchema, handler: callable) -> None:
        self._tools[schema.name] = handler
        self._schemas[schema.name] = schema

    def execute(self, name: str, params: dict) -> dict:
        handler = self._tools.get(name)
        if handler is None:
            raise ValueError(f"Tool '{name}' is not registered")
        return handler(**params)

    def list_schemas(self) -> list[ToolSchema]:
        return list(self._schemas.values())
