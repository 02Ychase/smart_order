"""Tests for Issue #2: multi-turn conversation context.

Covers:
- _format_recent_turns helper
- Planner receives conversation history and last_recommendations
- RAG uses effective_query (plan.normalized_query) instead of raw user message
- respond_node outputs last_recommendations for next turn
- Conversation store metadata (set/get/eviction)
- Full graph multi-turn flow: recommend → follow-up → ordinal add-to-cart
"""

from langchain_core.messages import AIMessage, HumanMessage

from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.nodes import _format_recent_turns, respond_node
from service.agent_runtime.planner import LangGraphAgentPlanner
from service.agent_runtime.runtime import AgentRuntimeContext
from service.agent_runtime.state import AgentPlan, GraphToolCall
from service.conversation_store import InMemoryConversationStore


# ── _format_recent_turns unit tests ──────────────────────────────────


def test_format_recent_turns_empty_messages() -> None:
    assert _format_recent_turns([]) == ""


def test_format_recent_turns_single_human_message_no_history() -> None:
    """A single human message (current turn) has no previous turns."""
    messages = [HumanMessage(content="推荐川菜")]
    assert _format_recent_turns(messages, max_turns=3) == ""


def test_format_recent_turns_one_complete_turn() -> None:
    messages = [
        HumanMessage(content="推荐川菜"),
        AIMessage(content="给你推荐宫保鸡丁"),
        HumanMessage(content="再来几个"),
    ]
    result = _format_recent_turns(messages, max_turns=3)
    assert "用户: 推荐川菜" in result
    assert "助手: 给你推荐宫保鸡丁" in result
    assert "再来几个" not in result  # current message excluded


def test_format_recent_turns_respects_max_turns() -> None:
    messages = [
        HumanMessage(content="第一轮"),
        AIMessage(content="回复一"),
        HumanMessage(content="第二轮"),
        AIMessage(content="回复二"),
        HumanMessage(content="第三轮"),
        AIMessage(content="回复三"),
        HumanMessage(content="当前消息"),
    ]
    result = _format_recent_turns(messages, max_turns=2)
    assert "第一轮" not in result
    assert "第二轮" in result
    assert "第三轮" in result
    assert "当前消息" not in result


# ── Planner _build_human_input tests ─────────────────────────────────


def test_planner_build_human_input_with_history_and_recommendations() -> None:
    planner = LangGraphAgentPlanner.__new__(LangGraphAgentPlanner)
    context = {
        "conversation_history": "用户: 推荐川菜\n助手: 给你推荐宫保鸡丁",
        "last_recommendations": [
            {"dish_name": "宫保鸡丁", "dish_id": 12, "price": 28.0},
        ],
    }
    result = LangGraphAgentPlanner._build_human_input("第一个加购物车", context)

    assert "## 对话历史" in result
    assert "推荐川菜" in result
    assert "## 上一轮推荐结果" in result
    assert "dish_id=12" in result
    assert "## 用户最新消息" in result
    assert "第一个加购物车" in result


def test_planner_build_human_input_without_history() -> None:
    result = LangGraphAgentPlanner._build_human_input("推荐川菜", {})
    assert "## 对话历史" not in result
    assert "## 上一轮推荐结果" not in result
    assert "推荐川菜" in result


# ── RAG effective_query test ─────────────────────────────────────────


class RecordingRetriever:
    """Retriever that records the query it was called with."""

    def __init__(self):
        self.called_with_query = None

    def retrieve(self, original_query, agent_plan, memories, limit):
        self.called_with_query = original_query
        return []


class StubPlanner:
    """Planner that returns a fixed plan with a normalized_query."""

    def __init__(self, normalized_query="推荐川菜"):
        self._normalized_query = normalized_query

    def plan(self, message, context):
        return AgentPlan(
            intent="recommendation",
            normalized_query=self._normalized_query,
            requires_rag=True,
        )


def test_rag_node_uses_normalized_query_over_raw_message() -> None:
    retriever = RecordingRetriever()
    planner = StubPlanner(normalized_query="推荐辣的川菜")
    graph = build_agent_graph()

    runtime = AgentRuntimeContext(
        planner=planner,
        retriever=retriever,
        use_llm_response=False,
    )

    graph.invoke(
        {
            "messages": [HumanMessage(content="再来几个")],
            "session_id": "s1",
            "user_id": 1,
        },
        config={"configurable": {"thread_id": "s1", "runtime": runtime}},
    )

    assert retriever.called_with_query == "推荐辣的川菜"


# ── respond_node outputs last_recommendations ────────────────────────


def test_respond_node_carries_recommendations_in_output() -> None:
    graph = build_agent_graph()

    retriever_evidence = [
        type("E", (), {
            "source_type": "dish", "source_id": 12, "merchant_id": 1,
            "title": "宫保鸡丁", "facts": {"dish_id": 12, "dish_name": "宫保鸡丁", "price": 28.0, "merchant_name": "川味坊"},
            "why_matched": ["川菜"], "citation": "经典川菜", "score": 0.9,
        })(),
    ]

    class FixedRetriever:
        def retrieve(self, q, agent_plan, memories, limit):
            return retriever_evidence

    runtime = AgentRuntimeContext(
        planner=StubPlanner(),
        retriever=FixedRetriever(),
        use_llm_response=False,
    )

    result = graph.invoke(
        {
            "messages": [HumanMessage(content="推荐川菜")],
            "session_id": "s1",
            "user_id": 1,
        },
        config={"configurable": {"thread_id": "s1", "runtime": runtime}},
    )

    assert result.get("last_recommendations")
    assert result["last_recommendations"][0]["dish_id"] == 12


# ── Conversation store metadata tests ────────────────────────────────


def test_conversation_store_metadata_set_and_get() -> None:
    store = InMemoryConversationStore()
    store.set_metadata("s1", "last_recommendations", [{"dish_id": 12}])

    assert store.get_metadata("s1", "last_recommendations") == [{"dish_id": 12}]
    assert store.get_metadata("s1", "nonexistent") is None
    assert store.get_metadata("s999", "last_recommendations") is None


def test_conversation_store_metadata_evicted_with_session() -> None:
    store = InMemoryConversationStore(max_sessions=2)
    store.append("s1", HumanMessage(content="a"))
    store.set_metadata("s1", "key", "value1")
    store.append("s2", HumanMessage(content="b"))
    store.set_metadata("s2", "key", "value2")
    # Adding s3 should evict s1 (oldest)
    store.append("s3", HumanMessage(content="c"))

    assert store.get_metadata("s1", "key") is None
    assert store.get_metadata("s2", "key") == "value2"


def test_conversation_store_clear_removes_metadata() -> None:
    store = InMemoryConversationStore()
    store.append("s1", HumanMessage(content="a"))
    store.set_metadata("s1", "last_recommendations", [{"dish_id": 1}])
    store.clear("s1")

    assert store.get_history("s1") == []
    assert store.get_metadata("s1", "last_recommendations") is None


# ── Full graph multi-turn: recommend → ordinal add-to-cart ───────────


class MultiTurnPlanner:
    """Planner that simulates a two-turn flow:
    Turn 1: recommendation (recommend_dishes)
    Turn 2: reads last_recommendations from context, resolves "第一个" to dish_id
    """

    def __init__(self):
        self.call_count = 0
        self.received_contexts = []

    def plan(self, message, context):
        self.call_count += 1
        self.received_contexts.append(dict(context))

        if "推荐" in message:
            return AgentPlan(
                intent="recommendation",
                normalized_query="推荐川菜",
                requires_rag=True,
            )

        # Second turn: ordinal reference
        last_recs = context.get("last_recommendations", [])
        if last_recs:
            dish_id = last_recs[0].get("dish_id")
            return AgentPlan(
                intent="cart_action",
                tool_calls=[GraphToolCall("add_to_cart", {"dish_id": dish_id, "quantity": 1}, True)],
            )
        return AgentPlan(intent="unsupported")


class FixedRetriever:
    def retrieve(self, q, agent_plan, memories, limit):
        return [
            type("E", (), {
                "source_type": "dish", "source_id": 12, "merchant_id": 1,
                "title": "宫保鸡丁", "facts": {"dish_id": 12, "dish_name": "宫保鸡丁", "price": 28.0, "merchant_name": "川味坊"},
                "why_matched": ["川菜"], "citation": "经典川菜", "score": 0.9,
            })(),
        ]


class StubActionExecutor:
    def __init__(self):
        self.executed = []

    def execute_action(self, plan, state):
        call = plan.tool_calls[0] if plan.tool_calls else None
        self.executed.append(call)
        return {"success": True, "action_id": "act_1", "message": "已加入购物车", "undo_available": True}

    def undo_last(self, state):
        return {"success": False, "message": "无可撤回操作"}


def test_multiturn_recommend_then_ordinal_add_to_cart() -> None:
    """Full two-turn test:
    Turn 1: "推荐川菜" → recommendations with dish_id=12
    Turn 2: "第一个加购物车" → planner sees last_recommendations, resolves to dish_id=12
    """
    planner = MultiTurnPlanner()
    retriever = FixedRetriever()
    executor = StubActionExecutor()
    graph = build_agent_graph()

    runtime = AgentRuntimeContext(
        planner=planner,
        retriever=retriever,
        action_executor=executor,
        use_llm_response=False,
    )
    config = {"configurable": {"thread_id": "mt1", "runtime": runtime}}

    # Turn 1: recommend
    turn1 = graph.invoke(
        {
            "messages": [HumanMessage(content="推荐川菜")],
            "session_id": "mt1",
            "user_id": 1,
        },
        config=config,
    )

    assert turn1["last_recommendations"]
    assert turn1["last_recommendations"][0]["dish_id"] == 12

    # Turn 2: ordinal add-to-cart, passing last_recommendations from turn 1
    turn2 = graph.invoke(
        {
            "messages": [
                HumanMessage(content="推荐川菜"),
                AIMessage(content=turn1["response_payload"]["message"]),
                HumanMessage(content="第一个加购物车"),
            ],
            "session_id": "mt1",
            "user_id": 1,
            "last_recommendations": turn1["last_recommendations"],
        },
        config=config,
    )

    # Planner should have received last_recommendations in context
    turn2_context = planner.received_contexts[-1]
    assert turn2_context.get("last_recommendations")
    assert turn2_context["last_recommendations"][0]["dish_id"] == 12

    # Planner should have received conversation history
    assert turn2_context.get("conversation_history")
    assert "推荐川菜" in turn2_context["conversation_history"]

    # Action should have been executed with dish_id=12
    assert executor.executed
    assert executor.executed[-1].arguments.get("dish_id") == 12
