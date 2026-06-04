import service.warmup as warmup


# ── should_warmup gating ──────────────────────────────────────────────


def test_should_warmup_disabled_by_env(monkeypatch) -> None:
    for val in ("0", "false", "off", "no", ""):
        monkeypatch.setenv("ASSISTANT_WARMUP", val)
        assert warmup.should_warmup() is False


def test_should_warmup_enabled_by_env(monkeypatch) -> None:
    monkeypatch.setenv("ASSISTANT_WARMUP", "1")
    assert warmup.should_warmup() is True


def test_should_warmup_default_skips_under_pytest(monkeypatch) -> None:
    # No explicit env → default, and we are running under pytest.
    monkeypatch.delenv("ASSISTANT_WARMUP", raising=False)
    assert warmup.should_warmup() is False


# ── run_startup_warmup aggregation + resilience ───────────────────────


def test_run_startup_warmup_aggregates_results(monkeypatch) -> None:
    monkeypatch.setattr(warmup, "_warmup_embedding", lambda: True)
    monkeypatch.setattr(warmup, "_warmup_cross_encoder", lambda: False)
    monkeypatch.setattr(warmup, "_warmup_bm25", lambda: True)

    assert warmup.run_startup_warmup() == {
        "embedding": True,
        "cross_encoder": False,
        "bm25": True,
    }


def test_run_startup_warmup_never_raises(monkeypatch) -> None:
    def boom():
        raise RuntimeError("model load failed")

    monkeypatch.setattr(warmup, "_warmup_embedding", boom)
    monkeypatch.setattr(warmup, "_warmup_cross_encoder", lambda: True)
    monkeypatch.setattr(warmup, "_warmup_bm25", boom)

    result = warmup.run_startup_warmup()

    assert result == {"embedding": False, "cross_encoder": True, "bm25": False}


# ── lifespan wiring ───────────────────────────────────────────────────


def test_app_lifespan_invokes_warmup_when_enabled(monkeypatch) -> None:
    """The FastAPI startup lifespan should call warmup when enabled."""
    monkeypatch.setenv("ASSISTANT_WARMUP", "1")

    calls = {"n": 0}
    monkeypatch.setattr(warmup, "run_startup_warmup", lambda: calls.__setitem__("n", calls["n"] + 1) or {})

    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app):  # entering the context triggers startup lifespan
        pass

    assert calls["n"] == 1
