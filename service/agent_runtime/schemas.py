"""
Pydantic schemas for LangGraph agent structured output.

These schemas replace manual JSON parsing in planner.py by using
LangChain's with_structured_output() for robust, typed LLM outputs.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class GraphToolCallSchema(BaseModel):
    """Schema for a single tool call in the agent plan."""

    tool_name: str = Field(default="", description="Exact tool name from the available tool set")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments as key-value pairs")
    writes_database: bool = Field(default=False, description="Whether this tool writes to the database")
    step_id: str = Field(default="", description="Optional step identifier, auto-generated if empty")


class FiltersSchema(BaseModel):
    """Schema for search/filter constraints in the agent plan."""

    cuisine_types: list[str] = Field(default_factory=list, description="Cuisine types to filter by, e.g. ['湘菜', '粤菜']")
    flavor_preferences: list[str] = Field(default_factory=list, description="Flavor preferences, e.g. ['辣', '甜']")
    budget_max: Optional[float] = Field(default=None, description="Maximum budget per person in CNY")
    party_size: Optional[int] = Field(default=None, description="Number of people dining")
    exclude_allergens: list[str] = Field(default_factory=list, description="Allergens to exclude")
    required_keywords: list[str] = Field(default_factory=list, description="Required keywords for matching")
    forbidden_keywords: list[str] = Field(default_factory=list, description="Forbidden keywords to exclude")
    source_types: list[str] = Field(default_factory=list, description="Source types, e.g. ['merchant', 'dish']")
    limit: Optional[int] = Field(default=None, description="Maximum number of results")
    sort_by: Optional[str] = Field(default=None, description="Sort order: price_desc, price_asc, or null")
    price_preference: Optional[str] = Field(default=None, description="Price preference: most_expensive, least_expensive, or null")


AgentIntentSchema = Literal[
    "greeting",
    "recommendation",
    "knowledge",
    "cart_action",
    "address_action",
    "preference_action",
    "undo_action",
    "unsupported",
]


class AgentPlanSchema(BaseModel):
    """Schema for the full agent plan output by the LLM planner."""

    # 用户意图
    intent: str = Field(
        default="unsupported",
        description="Intent category: greeting, recommendation, knowledge, cart_action, address_action, preference_action, undo_action, unsupported",
    )
    # 把用户原话整理成更适合检索的短查询
    normalized_query: str = Field(
        default="",
        description="A concise query suitable for retrieval, distilled from the user message",
    )
    # 告诉 Agent 是否需要进入 RAG 检索
    requires_rag: bool = Field(
        default=False,
        description="Whether this plan requires RAG retrieval to answer",
    )
    # 保存从用户自然语言中抽取出的结构化约束，口味偏好，预算上限等
    filters: FiltersSchema = Field(
        default_factory=FiltersSchema,
        description="Search constraints and filter parameters",
    )
    # 告诉 Agent 后面要按顺序执行哪些工具
    tool_calls: list[GraphToolCallSchema] = Field(
        default_factory=list,
        description="Ordered list of tool calls to execute SEQUENTIALLY. Each call is a step. "
                    "For multi-step tasks (e.g., search then add_to_cart), list them in execution order.",
    )
    # 表示是否应该直接回答，而不是追问澄清
    should_answer_directly: bool = Field(
        default=True,
        description="Whether the agent should answer directly without asking clarifying questions",
    )
    # 给 respond 节点的提示信息。
    response_hint: str = Field(
        default="",
        description="A brief hint for the response generation node",
    )
