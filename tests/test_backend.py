"""Chaine ask() : retriever, prompt FR, LLM (mocké), endpoint custom."""
from unittest.mock import patch, MagicMock

import pytest
from langchain_core.runnables import RunnableLambda

import backend
from backend import ask, RagError, RagifixRetriever


def _resp(payload):
    m = MagicMock()
    m.status_code = 200
    m.text = ""
    m.json.return_value = payload
    return m


DOCS = {"results": [
    {
        "chunk_id": "c1", "doc_id": "d1", "text": "Concert jazz à Paris",
        "score": 0.9, "metadata": {"city": "Paris", "date": "2026-01-01"},
        "origin": "test",
    },
    {
        "chunk_id": "c2", "doc_id": "d2", "text": "Expo à Lyon",
        "score": 0.5, "metadata": {"city": "Lyon", "date": "2026-02-01"},
        "origin": "test",
    },
]}


def _fake_llm(text="réponse fake"):
    return RunnableLambda(lambda x: type("O", (), {"content": text})())


def test_ask_question_vide():
    with pytest.raises(ValueError):
        ask("  ")


def test_ask_sans_cle_mistral():
    with patch.object(backend, "MISTRAL_API_KEY", ""):
        with patch.object(backend, "LLM_BASE_URL", ""):
            with pytest.raises(RagError):
                ask("jazz")


def test_ask_sans_docs_sans_llm():
    with patch.object(backend, "MISTRAL_API_KEY", "test-key"):
        with patch.object(backend.httpx, "post", return_value=_resp({"results": []})):
            with patch.object(backend, "ChatMistralAI") as llm:
                res = ask("truc introuvable")
                assert res["sources"] == []
                assert "rien trouv" in res["answer"]
                llm.assert_not_called()


def test_ask_avec_docs():
    with patch.object(backend, "MISTRAL_API_KEY", "test-key"):
        with patch.object(backend.httpx, "post", return_value=_resp(DOCS)):
            with patch.object(backend, "ChatMistralAI", return_value=_fake_llm()):
                res = ask("jazz", city="Paris", top_k=5)
                assert res["answer"] == "réponse fake"
                assert len(res["sources"]) == 2
                assert res["sources"][0].page_content == "Concert jazz à Paris"
                assert res["sources"][0].metadata["chunk_id"] == "c1"
                assert res["sources"][0].metadata["doc_id"] == "d1"
                assert res["sources"][0].metadata["score"] == 0.9
                assert res["sources"][0].metadata["origin"] == "test"


def test_ask_endpoint_custom_sans_cle():
    seen = {}

    def fake_cls(**kwargs):
        seen.update(kwargs)
        return _fake_llm("local ok")

    with patch.object(backend, "MISTRAL_API_KEY", ""):
        with patch.object(backend, "LLM_BASE_URL", "http://localhost:11434/v1"):
            with patch.object(backend, "LLM_MODEL", "local-model"):
                with patch.object(backend.httpx, "post", return_value=_resp(DOCS)):
                    with patch.object(backend, "ChatMistralAI", side_effect=fake_cls):
                        res = ask("jazz")
                        assert res["answer"] == "local ok"
                        assert seen["endpoint"] == "http://localhost:11434/v1"
                        assert seen["model"] == "local-model"
                        assert seen["api_key"] == "not-needed"


def test_retriever_mapping_complet():
    with patch.object(backend.httpx, "post", return_value=_resp(DOCS)):
        docs = RagifixRetriever(top_k=5, city="").invoke("jazz")
        assert len(docs) == 2
        assert docs[1].metadata["city"] == "Lyon"
        assert docs[1].metadata["chunk_id"] == "c2"


def test_retriever_defaults():
    r = RagifixRetriever()
    assert r.top_k == 5
    assert r.city == ""
