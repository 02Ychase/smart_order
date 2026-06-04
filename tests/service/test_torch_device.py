import torch

from service.torch_device import resolve_device


def test_env_override_takes_precedence(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_DEVICE", "cuda:1")
    assert resolve_device("EMBEDDING_DEVICE") == "cuda:1"


def test_blank_env_is_ignored(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_DEVICE", "   ")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert resolve_device("EMBEDDING_DEVICE") == "cpu"


def test_auto_detects_cuda_when_available(monkeypatch) -> None:
    monkeypatch.delenv("EMBEDDING_DEVICE", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert resolve_device("EMBEDDING_DEVICE") == "cuda"


def test_auto_falls_back_to_cpu_when_no_cuda(monkeypatch) -> None:
    monkeypatch.delenv("EMBEDDING_DEVICE", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert resolve_device("EMBEDDING_DEVICE") == "cpu"


def test_no_env_var_argument_still_auto_detects(monkeypatch) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert resolve_device() == "cpu"
