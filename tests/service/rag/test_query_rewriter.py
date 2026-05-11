from service.rag.query_rewriter import QueryRewriter


class FakeLLM:
    def __init__(self, response: str):
        self.response = response
        self.called_with = None

    def call(self, query, system_instruction):
        self.called_with = query
        return self.response


def test_rewriter_returns_expansion_queries():
    fake_llm = FakeLLM('{"queries": ["辣的湘菜推荐", "湖南特色辣味菜品", "湘菜 辣 推荐"]}')
    rewriter = QueryRewriter(llm=fake_llm)

    result = rewriter.rewrite("来几个辣的湘菜")

    assert len(result) == 3
    assert "辣的湘菜推荐" in result


def test_rewriter_fallback_on_llm_failure():
    class FailingLLM:
        def call(self, query, system_instruction):
            raise RuntimeError("LLM unavailable")

    rewriter = QueryRewriter(llm=FailingLLM())
    result = rewriter.rewrite("来几个辣的湘菜")

    assert result == ["来几个辣的湘菜"]


def test_rewriter_deduplicates():
    fake_llm = FakeLLM('{"queries": ["湘菜推荐", "湘菜推荐", "辣味湘菜"]}')
    rewriter = QueryRewriter(llm=fake_llm)

    result = rewriter.rewrite("来几个辣的湘菜")

    assert len(result) == 2
