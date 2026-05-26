"""Tool definitions for the LLM Agent.

These schemas are passed to the LLM so it knows what tools are available
and how to invoke them.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "当用户查询商家信息、菜品信息、营业时间、地址、价格等知识时使用。自动进行向量检索+数据库查询。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "优化的搜索关键词，例如：'咖啡店', '川菜馆', '营业时间'",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_dishes",
            "description": "当用户请求个性化推荐时使用。需要提供预算、人数、口味偏好等约束条件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "budget": {
                        "type": "number",
                        "description": "预算上限（元）",
                    },
                    "party_size": {
                        "type": "integer",
                        "description": "就餐人数",
                    },
                    "preferences": {
                        "type": "string",
                        "description": "口味偏好，例如：'川味麻辣', '清淡', '不吃辣'",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "将菜品批量加入用户购物车",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "批量添加菜品列表，如[{\"dish_id\":123,\"quantity\":1}]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "dish_id": {"type": "integer"},
                                "quantity": {"type": "integer", "default": 1},
                            },
                            "required": ["dish_id"],
                        },
                    },
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_address",
            "description": "保存用户配送地址",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "地址标签，例如：'家', '公司'",
                    },
                    "detail_address": {
                        "type": "string",
                        "description": "详细地址",
                    },
                    "contact_phone": {
                        "type": "string",
                        "description": "联系电话",
                    },
                },
                "required": ["label", "detail_address", "contact_phone"],
            },
        },
    },
]


def get_tools_description() -> str:
    """Return a human-readable description of all tools for the LLM prompt."""
    lines = ["可用工具："]
    for tool in TOOLS:
        fn = tool["function"]
        lines.append(f"- {fn['name']}: {fn['description']}")
    return "\n".join(lines)
