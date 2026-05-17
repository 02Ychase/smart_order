from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AppConfig:

    @dataclass
    class RagConfig:
        cache_max_size: int = 128
        cache_ttl_seconds: int = 300
        recall_limit: int = 50
        cross_encoder_top_k: int = 20
        output_limit_default: int = 5
        output_limit_max: int = 20
        bm25_k1: float = 1.2
        bm25_b: float = 0.75
        intent_weights: dict = field(default_factory=lambda: {
            "recommendation": {
                "dense": 0.15, "lexical": 0.10, "constraint": 0.20,
                "rating": 0.15, "business": 0.10, "user_pref": 0.10, "cross_encoder": 0.20,
            },
            "knowledge": {
                "dense": 0.25, "lexical": 0.20, "constraint": 0.10,
                "rating": 0.10, "business": 0.05, "user_pref": 0.10, "cross_encoder": 0.20,
            },
            "default": {
                "dense": 0.20, "lexical": 0.15, "constraint": 0.15,
                "rating": 0.10, "business": 0.10, "user_pref": 0.10, "cross_encoder": 0.20,
            },
        })

    @dataclass
    class AgentConfig:
        max_iterations: int = 5
        conversation_max_messages: int = 20
        conversation_max_sessions: int = 1000

    @dataclass
    class GuardrailConfig:
        max_input_length: int = 500
        enable_input_guardrail: bool = True
        enable_topic_guardrail: bool = True
        enable_output_guardrail: bool = True

    @dataclass
    class MemoryConfig:
        max_memories_per_user: int = 100

    rag: RagConfig = field(default_factory=RagConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    guardrails: GuardrailConfig = field(default_factory=GuardrailConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)


_app_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _app_config
    if _app_config is None:
        _app_config = AppConfig()
    return _app_config


def set_config(config: AppConfig) -> None:
    global _app_config
    _app_config = config
