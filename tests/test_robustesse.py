"""Robustesse HTTP du client RAG : erreurs propres, jamais de crash brut."""
from unittest.mock import patch, MagicMock

import httpx
import pytest

import backend
from backend import query_rag, RagError


def _resp(status=200, payload=None, text=""):
    m = MagicMock()
    m.status_code = status
    m.text = text
    m.json.return_value = payload or {"results": []}
    return m


def test_question_vide():
    with pytest.raises(ValueError):
        query_rag("   ")


def test_401_token_invalide():
    with patch.object(backend.httpx, "post", return_value=_resp(401, text="unauthorized")):
        with pytest.raises(RagError) as e:
            query_rag("concerts")
        assert e.value.status_code == 401


def test_500_rag():
    with patch.object(backend.httpx, "post", return_value=_resp(500, text="boom")):
        with pytest.raises(RagError) as e:
            query_rag("concerts")
        assert e.value.status_code == 500


def test_statut_inattendu():
    with patch.object(backend.httpx, "post", return_value=_resp(418, text="teapot")):
        with pytest.raises(RagError) as e:
            query_rag("concerts")
        assert e.value.status_code == 418


def test_rag_injoignable():
    with patch.object(backend.httpx, "post", side_effect=httpx.ConnectError("down")):
        with pytest.raises(RagError) as e:
            query_rag("concerts")
        assert "injoignable" in str(e.value)


def test_filtre_city_envoye():
    with patch.object(backend.httpx, "post", return_value=_resp(200)) as p:
        query_rag("jazz", top_k=3, city="Paris")
        _, kw = p.call_args
        assert kw["json"] == {"query": "jazz", "top_k": 3, "filters": {"city": "Paris"}}


def test_sans_city_pas_de_filtre():
    with patch.object(backend.httpx, "post", return_value=_resp(200)) as p:
        query_rag("jazz", city="   ")
        _, kw = p.call_args
        assert kw["json"]["filters"] == {}


def test_rag_error_sans_status():
    err = RagError("simple")
    assert err.status_code is None
    assert str(err) == "simple"
