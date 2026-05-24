from service.agent_runtime import planner as planner_module
from service.agent_runtime.planner import LangGraphAgentPlanner
from service.agent_runtime.schemas import AgentPlanSchema, FiltersSchema, GraphToolCallSchema


class StubStructuredLLM:
    """Mock for LLM with `invoke()` method that returns a Pydantic schema."""

    def __init__(self, schema_result: AgentPlanSchema) -> None:
        self.schema_result = schema_result

    def invoke(self, messages, **kwargs):
        return self.schema_result


class RaisingStructuredLLM:
    """Mock structured LLM that always raises, to test fallback."""

    def invoke(self, messages, **kwargs):
        raise RuntimeError("structured llm unavailable")


def test_planner_recommends_directly_without_budget_or_party_size() -> None:
    planner = LangGraphAgentPlanner()
    planner._structured_llm = StubStructuredLLM(
        AgentPlanSchema(
            intent="recommendation",
            normalized_query="辣的湘菜",
            requires_rag=True,
            filters=FiltersSchema(cuisine_types=["湘菜"], flavor_preferences=["辣"]),
            tool_calls=[],
            should_answer_directly=True,
            response_hint="推荐辣味湘菜",
        )
    )

    plan = planner.plan("帮我推荐几个比较辣的湘菜", {"loaded_user_memories": []})

    assert plan.intent == "recommendation"
    assert plan.should_answer_directly is True
    assert plan.requires_rag is True
    assert plan.filters["cuisine_types"] == ["湘菜"]
    assert plan.filters["flavor_preferences"] == ["辣"]
    assert plan.filters["party_size"] is None
    assert plan.filters["budget_max"] is None


def test_planner_normalizes_hallucinated_dish_search_tool_to_recommendation_tool() -> None:
    planner = LangGraphAgentPlanner()
    planner._structured_llm = StubStructuredLLM(
        AgentPlanSchema(
            intent="recommendation",
            normalized_query="湘菜",
            requires_rag=True,
            filters=FiltersSchema(),
            tool_calls=[
                GraphToolCallSchema(
                    tool_name="search_dishes",
                    arguments={"query": "湘菜", "cuisine_types": ["湘菜"]},
                    writes_database=False,
                )
            ],
            should_answer_directly=True,
            response_hint="推荐湘菜",
        )
    )

    plan = planner.plan("推荐几个湘菜", {})

    assert plan.requires_rag is True
    assert plan.tool_calls[0].tool_name == "recommend_dishes"
    assert plan.tool_calls[0].writes_database is False
    assert plan.filters["cuisine_types"] == ["湘菜"]


def test_planner_extracts_limit_and_price_sort_from_user_message() -> None:
    planner = LangGraphAgentPlanner()
    planner._structured_llm = StubStructuredLLM(
        AgentPlanSchema(
            intent="recommendation",
            normalized_query="最贵的湘菜",
            requires_rag=True,
            filters=FiltersSchema(cuisine_types=["湘菜"]),
            tool_calls=[
                GraphToolCallSchema(
                    tool_name="recommend_dishes",
                    arguments={"query": "最贵的湘菜", "cuisine_types": ["湘菜"]},
                    writes_database=False,
                )
            ],
            should_answer_directly=True,
            response_hint="推荐最贵的湘菜",
        )
    )

    plan = planner.plan("推荐一个最贵的湘菜", {})

    assert plan.filters["limit"] == 1
    assert plan.filters["sort_by"] == "price_desc"
    assert plan.filters["price_preference"] == "most_expensive"


def test_planner_splits_compound_recommendation_into_scoped_rag_calls() -> None:
    planner = LangGraphAgentPlanner()
    planner._structured_llm = StubStructuredLLM(
        AgentPlanSchema(
            intent="recommendation",
            normalized_query="推荐川菜和咖啡",
            requires_rag=True,
            filters=FiltersSchema(cuisine_types=["川菜", "咖啡"], limit=2),
            tool_calls=[
                GraphToolCallSchema(
                    tool_name="recommend_dishes",
                    arguments={
                        "query": "推荐川菜和咖啡",
                        "cuisine_types": ["川菜", "咖啡"],
                        "limit": 2,
                    },
                    writes_database=False,
                )
            ],
            should_answer_directly=True,
            response_hint="用户同时需要川菜和咖啡两个方向的推荐，各推荐1个即可。",
        )
    )

    plan = planner.plan("推荐一个川菜和咖啡", {})

    assert plan.requires_rag is True
    assert [call.step_id for call in plan.tool_calls] == [
        "recommend_dishes_0",
        "recommend_dishes_1",
    ]
    assert [call.arguments["query"] for call in plan.tool_calls] == ["推荐川菜", "推荐咖啡"]
    assert [call.arguments["cuisine_types"] for call in plan.tool_calls] == [["川菜"], ["咖啡"]]
    assert [call.arguments["limit"] for call in plan.tool_calls] == [1, 1]
    assert plan.tool_calls[1].arguments["required_keywords"] == ["咖啡"]


def test_planner_normalizes_hallucinated_cafe_search_tool_to_catalog_tool() -> None:
    planner = LangGraphAgentPlanner()
    planner._structured_llm = StubStructuredLLM(
        AgentPlanSchema(
            intent="knowledge",
            normalized_query="卖咖啡的店铺",
            requires_rag=False,
            filters=FiltersSchema(),
            tool_calls=[
                GraphToolCallSchema(
                    tool_name="search_cafes",
                    arguments={"query": "卖咖啡的店铺", "required_keywords": ["咖啡"]},
                    writes_database=False,
                )
            ],
            should_answer_directly=True,
            response_hint="查询咖啡店",
        )
    )

    plan = planner.plan("推荐几个卖咖啡的店铺", {})

    assert plan.requires_rag is True
    assert plan.tool_calls[0].tool_name == "search_catalog"
    assert plan.tool_calls[0].writes_database is False
    assert plan.filters["required_keywords"] == ["咖啡"]


def test_planner_rule_fallback_detects_undo() -> None:
    planner = LangGraphAgentPlanner()
    planner._model_name = None

    plan = planner.plan("帮我撤回刚才的删除", {"recent_action_ids": ["act_1"]})

    assert plan.intent == "undo_action"
    assert plan.tool_calls[0].tool_name == "undo_last_action"


def test_planner_rule_fallback_routes_cart_clear_as_direct_write() -> None:
    planner = LangGraphAgentPlanner()
    planner._model_name = None

    plan = planner.plan("清空购物车", {"user_id": 9})

    assert plan.intent == "cart_action"
    assert plan.tool_calls[0].tool_name == "cart_clear"
    assert plan.tool_calls[0].writes_database is True


def test_planner_llm_failure_falls_back_to_rule_plan_for_cart_clear(monkeypatch) -> None:
    planner = LangGraphAgentPlanner()
    planner._structured_llm = None
    planner._model_name = "test-model"

    def raise_llm_failure(**kwargs):
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr(planner_module, "call_llm_with_retry", raise_llm_failure)

    plan = planner.plan("清空购物车", {"user_id": 9})

    assert plan.intent == "cart_action"
    assert plan.tool_calls[0].tool_name == "cart_clear"
    assert plan.tool_calls[0].writes_database is True


def test_planner_parses_common_false_strings_and_normalizes_read_tool_from_fenced_json(monkeypatch) -> None:
    planner = LangGraphAgentPlanner()
    planner._structured_llm = None
    planner._model_name = "test-model"

    def return_fenced_json(**kwargs):
        return """
        ```json
        {
          "intent": "knowledge",
          "normalized_query": "营业时间",
          "requires_rag": "false",
          "tool_calls": [
            {
              "tool_name": "search_menu",
              "arguments": {"query": "营业时间"},
              "writes_database": "false"
            }
          ],
          "should_answer_directly": "false",
          "response_hint": ""
        }
        ```
        """

    monkeypatch.setattr(planner_module, "call_llm_with_retry", return_fenced_json)

    plan = planner.plan("营业时间", {})

    assert plan.requires_rag is True
    assert plan.should_answer_directly is False
    assert plan.tool_calls[0].tool_name == "search_catalog"
    assert plan.tool_calls[0].writes_database is False


def test_planner_treats_null_tool_calls_as_empty_list(monkeypatch) -> None:
    planner = LangGraphAgentPlanner()
    planner._structured_llm = None
    planner._model_name = "test-model"

    def return_plan_with_null_tool_calls(**kwargs):
        return {
            "intent": "greeting",
            "normalized_query": "你好",
            "requires_rag": False,
            "tool_calls": None,
            "should_answer_directly": True,
            "response_hint": "你好",
        }

    monkeypatch.setattr(planner_module, "call_llm_with_retry", return_plan_with_null_tool_calls)

    plan = planner.plan("你好", {})

    assert plan.tool_calls == []


# ---------------------------------------------------------------------------
# Structured output tests
# ---------------------------------------------------------------------------


def test_planner_schema_to_plan_converts_recommendation_correctly() -> None:
    """Verify _schema_to_plan converts a Pydantic schema to AgentPlan with
    correct tool name normalization and filter merging."""
    planner = LangGraphAgentPlanner()

    schema = AgentPlanSchema(
        intent="recommendation",
        normalized_query="辣的湘菜",
        requires_rag=True,
        filters=FiltersSchema(
            cuisine_types=["湘菜"],
            flavor_preferences=["辣"],
        ),
        tool_calls=[
            GraphToolCallSchema(
                tool_name="recommend_dishes",
                arguments={"query": "辣的湘菜", "cuisine_types": ["湘菜"], "flavor_preferences": ["辣"]},
                writes_database=False,
            )
        ],
        should_answer_directly=True,
        response_hint="推荐辣味湘菜",
    )

    plan = planner._schema_to_plan(schema)

    assert plan.intent == "recommendation"
    assert plan.normalized_query == "辣的湘菜"
    assert plan.requires_rag is True
    assert plan.should_answer_directly is True
    assert plan.filters["cuisine_types"] == ["湘菜"]
    assert plan.filters["flavor_preferences"] == ["辣"]
    assert plan.tool_calls[0].tool_name == "recommend_dishes"
    assert plan.tool_calls[0].writes_database is False
    assert plan.response_hint == "推荐辣味湘菜"


def test_planner_schema_to_plan_normalizes_hallucinated_tool_name() -> None:
    """Schema with hallucinated `search_dishes` tool → normalized to `recommend_dishes`."""
    planner = LangGraphAgentPlanner()

    schema = AgentPlanSchema(
        intent="recommendation",
        normalized_query="湘菜",
        requires_rag=True,
        tool_calls=[
            GraphToolCallSchema(
                tool_name="search_dishes",
                arguments={"query": "湘菜", "cuisine_types": ["湘菜"]},
            )
        ],
    )

    plan = planner._schema_to_plan(schema)

    assert plan.tool_calls[0].tool_name == "recommend_dishes"
    assert plan.filters["cuisine_types"] == ["湘菜"]


def test_planner_schema_to_plan_enforces_requires_rag_for_recommendation() -> None:
    """Even if `requires_rag` is False in the schema, intent=recommendation forces True."""
    planner = LangGraphAgentPlanner()

    schema = AgentPlanSchema(
        intent="recommendation",
        normalized_query="推荐湘菜",
        requires_rag=False,
        tool_calls=[
            GraphToolCallSchema(
                tool_name="recommend_dishes",
                arguments={"query": "湘菜"},
            )
        ],
    )

    plan = planner._schema_to_plan(schema)
    assert plan.requires_rag is True


def test_planner_schema_to_plan_filters_have_defaults() -> None:
    """Empty schema should produce an AgentPlan with full default filters."""
    planner = LangGraphAgentPlanner()

    schema = AgentPlanSchema(intent="greeting")
    plan = planner._schema_to_plan(schema)

    assert plan.filters["cuisine_types"] == []
    assert plan.filters["budget_max"] is None
    assert plan.filters["party_size"] is None
    assert plan.filters["required_keywords"] == []
    assert plan.filters["limit"] is None


def test_planner_structured_output_path_is_used_when_available() -> None:
    """When _structured_llm is set, it is used before other fallback paths."""
    planner = LangGraphAgentPlanner()
    planner._structured_llm = StubStructuredLLM(
        AgentPlanSchema(
            intent="greeting",
            normalized_query="hello",
            should_answer_directly=True,
        )
    )

    plan = planner.plan("hello", {})

    assert plan.intent == "greeting"
    assert plan.normalized_query == "hello"


def test_planner_structured_output_falls_back_to_rule_plan_on_failure() -> None:
    """When structured output fails and no model fallback exists, fall back to rule plan."""
    planner = LangGraphAgentPlanner()
    planner._model_name = None
    planner._structured_llm = RaisingStructuredLLM()

    plan = planner.plan("清空购物车", {"user_id": 9})

    assert plan.intent == "cart_action"
    assert plan.tool_calls[0].tool_name == "cart_clear"


def test_planner_structured_output_falls_back_to_direct_llm_on_failure(monkeypatch) -> None:
    """When structured output fails but MODEL_NAME exists, fall back to direct LLM path."""
    planner = LangGraphAgentPlanner()
    planner._model_name = "test-model"
    planner._structured_llm = RaisingStructuredLLM()

    def return_plan_json(**kwargs):
        return {
            "intent": "greeting",
            "normalized_query": "你好",
            "tool_calls": [],
            "should_answer_directly": True,
            "response_hint": "你好",
        }

    monkeypatch.setattr(planner_module, "call_llm_with_retry", return_plan_json)

    plan = planner.plan("你好", {})

    assert plan.intent == "greeting"
    assert plan.normalized_query == "你好"


def test_plan_add_to_cart_intent():
    planner = LangGraphAgentPlanner()
    plan = planner._rule_plan("帮我把宫保鸡丁加到购物车")
    assert plan.intent == "cart_action"
    assert any(call.tool_name == "add_to_cart" for call in plan.tool_calls)


def test_plan_save_address_intent():
    planner = LangGraphAgentPlanner()
    plan = planner._rule_plan("帮我保存地址：上海市静安区南京西路100号")
    assert plan.intent == "address_action"
    assert any(call.tool_name == "save_address" for call in plan.tool_calls)


def test_plan_preference_intent():
    planner = LangGraphAgentPlanner()
    plan = planner._rule_plan("我不吃花生，记住我的偏好")
    assert plan.intent == "preference_action"
    assert any(call.tool_name == "upsert_preference" for call in plan.tool_calls)
