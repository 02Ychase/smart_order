import json
import logging
import warnings

warnings.warn(
    "AgentLoop is deprecated. Use service.agent_runtime.graph.build_agent_graph() instead.",
    DeprecationWarning,
    stacklevel=2,
)

from service.tool_registry import ToolRegistry, ToolSchema
from service.tools.cart_tool import add_to_cart_tool
from service.tools.address_tool import save_address_tool
from tools.llm_tool import call_llm

logger = logging.getLogger(__name__)


_REACT_PROMPT = """你是一个智能点餐助手的 ReAct Agent。

用户意图：{intent}
用户消息：{user_message}

你可以使用以下工具：
- add_to_cart: 将菜品加入购物车
- save_address: 保存配送地址

请按照以下 JSON 格式返回你的思考和行动，不要包含任何其他文字：

{{
    "thought": "你的思考过程",
    "action": "工具名称",
    "action_input": {{"参数名": "参数值"}}
}}

如果不需要执行工具，action 填 "none"。

记住：只返回纯 JSON，不要有任何额外字符和解释。"""


class AgentLoop:
    def __init__(self, session) -> None:
        self.session = session
        self.tool_registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self) -> None:
        self.tool_registry.register(
            ToolSchema(
                name="add_to_cart",
                description="Add a dish to the user's shopping cart",
                parameters={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer"},
                        "dish_id": {"type": "integer"},
                        "quantity": {"type": "integer", "default": 1},
                    },
                    "required": ["user_id", "dish_id"],
                },
            ),
            lambda **kwargs: add_to_cart_tool(session=self.session, **kwargs),
        )
        self.tool_registry.register(
            ToolSchema(
                name="save_address",
                description="Save a new delivery address for the user",
                parameters={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer"},
                        "label": {"type": "string"},
                        "contact_name": {"type": "string"},
                        "contact_phone": {"type": "string"},
                        "city": {"type": "string"},
                        "district": {"type": "string"},
                        "detail_address": {"type": "string"},
                        "longitude": {"type": "number"},
                        "latitude": {"type": "number"},
                        "is_default": {"type": "boolean", "default": False},
                    },
                    "required": ["user_id", "label", "contact_name", "contact_phone", "city", "district", "detail_address", "longitude", "latitude"],
                },
            ),
            lambda **kwargs: save_address_tool(session=self.session, **kwargs),
        )

    def run(self, intent: str, user_message: str, constraints, user_id: int) -> dict:
        if intent == "greeting":
            return {"response_type": "greeting", "message": "你好！我是你的智能点餐助手，有什么可以帮你的吗？"}

        if intent == "action_intent":
            return self._run_action(user_message, user_id)

        if intent in ("recommendation", "comparison", "knowledge"):
            return {"response_type": "needs_retrieval", "intent": intent}

        return {"response_type": "unsupported", "message": "暂不支持该类型的请求。"}

    def _run_action(self, user_message: str, user_id: int) -> dict:
        prompt = _REACT_PROMPT.format(intent="action_intent", user_message=user_message)
        llm_response = call_llm(query=prompt, system_instruction="")

        cleaned = self._clean_json_response(llm_response)
        parsed = json.loads(cleaned)

        action = parsed.get("action")
        action_input = parsed.get("action_input", {})

        if action and action != "none":
            if "user_id" not in action_input:
                action_input["user_id"] = user_id
            tool_result = self.tool_registry.execute(action, action_input)
            return {"response_type": "action_completed", "tool_result": tool_result}

        return {"response_type": "action_pending", "message": parsed.get("thought", "我已理解你的意图，请提供更多细节以便执行。")}

    @staticmethod
    def _clean_json_response(raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return raw[start : end + 1]
        return raw
