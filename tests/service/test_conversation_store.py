from langchain_core.messages import AIMessage, HumanMessage

from service.conversation_store import InMemoryConversationStore


def test_store_and_retrieve_messages():
    store = InMemoryConversationStore()

    store.append("session_1", HumanMessage(content="你好"))
    store.append("session_1", AIMessage(content="你好！有什么可以帮你的？"))
    store.append("session_1", HumanMessage(content="推荐湘菜"))

    history = store.get_history("session_1")

    assert len(history) == 3
    assert history[0].content == "你好"
    assert history[2].content == "推荐湘菜"


def test_max_history_length():
    store = InMemoryConversationStore(max_messages=4)

    for i in range(6):
        store.append("s1", HumanMessage(content=f"msg_{i}"))

    history = store.get_history("s1")
    assert len(history) == 4
    assert history[0].content == "msg_2"


def test_empty_session():
    store = InMemoryConversationStore()
    assert store.get_history("nonexistent") == []
