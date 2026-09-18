"""Tests API REST : TestClient + ask() mocke (aucun service requis)."""
import api
import backend
from fastapi.testclient import TestClient

client = TestClient(api.app)


class FakeDoc:
    def __init__(self, contenu, metadata):
        self.page_content = contenu
        self.metadata = metadata


def _ok(monkeypatch):
    def fake_ask(question, city="", top_k=5, date_min="", date_max=""):
        assert (question, city, top_k, date_min, date_max) == (
            "concert ce week-end ?", "Marseille", 3, "2026-01-01", "2026-12-31")
        return {"answer": "Oui, au Dock des Suds.",
                "sources": [FakeDoc("Concert samedi", {"ville": "Marseille"})]}
    monkeypatch.setattr(api, "ask", fake_ask)


def test_ask_nominal(monkeypatch):
    _ok(monkeypatch)
    r = client.post("/ask", json={"question": "concert ce week-end ?",
                                  "city": "Marseille", "top_k": 3,
                                  "date_min": "2026-01-01", "date_max": "2026-12-31"})
    assert r.status_code == 200
    assert r.json() == {"reponse": "Oui, au Dock des Suds.",
                        "sources": [{"contenu": "Concert samedi",
                                     "metadata": {"ville": "Marseille"}}]}


def test_ask_question_vide_rejetee():
    assert client.post("/ask", json={"question": ""}).status_code == 422
    assert client.post("/ask", json={}).status_code == 422


def test_ask_panne_rag_renvoie_502(monkeypatch):
    def boom(*a, **k):
        raise backend.RagError("RAG injoignable")
    monkeypatch.setattr(api, "ask", boom)
    r = client.post("/ask", json={"question": "x"})
    assert r.status_code == 502
    assert "RAG injoignable" in r.json()["detail"]


def test_ask_sans_auth_ni_cle(monkeypatch):
    # Pas d'authentification : une requete nue aboutit (200, jamais 401/403).
    monkeypatch.setattr(api, "ask", lambda *a, **k: {"answer": "ok", "sources": []})
    assert client.post("/ask", json={"question": "x"}).status_code == 200


def test_health():
    assert client.get("/health").json() == {"status": "ok"}
