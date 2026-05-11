from service.config import AppConfig


def test_default_config():
    config = AppConfig()
    assert config.rag.cache_max_size == 128
    assert config.rag.cache_ttl_seconds == 300
    assert config.agent.max_iterations == 5
    assert config.guardrails.max_input_length == 500


def test_config_override():
    config = AppConfig(
        rag=AppConfig.RagConfig(cache_max_size=256),
        agent=AppConfig.AgentConfig(max_iterations=10),
    )
    assert config.rag.cache_max_size == 256
    assert config.agent.max_iterations == 10
