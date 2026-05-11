from service.observability import MetricsCollector


def test_collector_records_timing():
    collector = MetricsCollector()
    collector.record_timing("rag.recall", 0.15)
    collector.record_timing("rag.rerank", 0.08)

    metrics = collector.get_metrics()
    assert metrics["rag.recall"] == 0.15
    assert metrics["rag.rerank"] == 0.08


def test_collector_records_counter():
    collector = MetricsCollector()
    collector.increment("rag.cache_hit")
    collector.increment("rag.cache_hit")

    metrics = collector.get_metrics()
    assert metrics["rag.cache_hit"] == 2


def test_collector_records_metadata():
    collector = MetricsCollector()
    collector.set_metadata("intent", "recommendation")
    collector.set_metadata("recall_routes", 4)

    assert collector.get_metadata()["intent"] == "recommendation"


def test_collector_to_log_dict():
    collector = MetricsCollector()
    collector.record_timing("total", 0.5)
    collector.set_metadata("intent", "recommendation")
    collector.increment("llm_calls")

    log_dict = collector.to_log_dict()
    assert "timings" in log_dict
    assert "counters" in log_dict
    assert "metadata" in log_dict
