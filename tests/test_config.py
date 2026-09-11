"""Config : valeurs par défaut + surcharge via env."""
import importlib


def test_defaults(monkeypatch):
    import dotenv
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    for k in ("MISTRAL_API_KEY", "RAGIFIX_API_TOKEN", "RAG_BASE_URL", "LLM_BASE_URL", "LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)
    import config
    importlib.reload(config)
    assert config.RAG_BASE_URL == "http://127.0.0.1:8421"
    assert config.LLM_BASE_URL == ""
    assert config.LLM_MODEL == "mistral-small-latest"
    importlib.reload(config)


def test_env_surcharge(monkeypatch):
    monkeypatch.setenv("RAG_BASE_URL", "http://example:9999/")
    monkeypatch.setenv("LLM_BASE_URL", "http://local:11434/v1/")
    monkeypatch.setenv("LLM_MODEL", "local-model")
    import config
    importlib.reload(config)
    assert config.RAG_BASE_URL == "http://example:9999"
    assert config.LLM_BASE_URL == "http://local:11434/v1"
    assert config.LLM_MODEL == "local-model"
    importlib.reload(config)
