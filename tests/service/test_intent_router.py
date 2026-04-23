from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.intent_router import IntentRouter, RoutingResult


def test_route_classifies_greeting() -> None:
    router = IntentRouter()
    result = router.route("Hi")
    assert result.intent == "greeting"
    assert result.requires_retrieval is False
    assert result.future_tool is None


def test_route_classifies_recommendation() -> None:
    router = IntentRouter()
    result = router.route("推荐几种川菜")
    assert result.intent == "recommendation"
    assert result.requires_retrieval is True
    assert result.likely_needs_clarification is False


def test_route_classifies_comparison() -> None:
    router = IntentRouter()
    result = router.route("比较兰姨小炒和午后豆房")
    assert result.intent == "comparison"
    assert result.requires_retrieval is True


def test_route_classifies_knowledge() -> None:
    router = IntentRouter()
    result = router.route("这家店几点营业")
    assert result.intent == "knowledge"
    assert result.requires_retrieval is True


def test_route_classifies_action_intent() -> None:
    router = IntentRouter()
    result = router.route("帮我加入购物车")
    assert result.intent == "action_intent"
    assert result.requires_retrieval is False
    assert result.future_tool == "add_to_cart"
