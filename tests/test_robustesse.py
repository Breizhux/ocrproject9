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


def _doc(uid, day):
    return {"chunk_id": uid, "doc_id": "d", "text": "t",
            "score": 0.5, "metadata": {"city": "Paris", "date": day}, "origin": "test"}


def test_dates_surfetch_et_filtre():
    payload = {"results": [_doc("vieux", "2025-01-01"), _doc("bon", "2026-06-01"),
                           _doc("futur", "2027-01-01"), _doc("sans-date", "")]}
    with patch.object(backend.httpx, "post", return_value=_resp(200, payload)) as p:
        out = query_rag("x", top_k=2, date_min="2026-01-01", date_max="2026-12-31")
        _, kw = p.call_args
        assert kw["json"]["top_k"] == 6  # surfetch x3 pour compenser le filtre client
        assert [r["chunk_id"] for r in out] == ["bon", "sans-date"]


def test_sans_dates_pas_de_surfetch():
    with patch.object(backend.httpx, "post", return_value=_resp(200)) as p:
        query_rag("x", top_k=4)
        _, kw = p.call_args
        assert kw["json"]["top_k"] == 4


def test_in_range_formats():
    import datetime
    from backend import _in_range
    assert _in_range("2026-06-03T16:30:00+00:00", "2026-01-01", "2026-12-31") is True
    assert _in_range("2025-01-01", "2026-01-01", "") is False
    assert _in_range(datetime.datetime(2026, 6, 3, 16, 30), "2026-01-01", "") is True
    assert _in_range(datetime.date(2025, 1, 1), "2026-01-01", "") is False
    assert _in_range("pas-une-date", "2026-01-01", "") is True
    assert _in_range(None, "2026-01-01", "") is True
    assert _in_range("2026-06-03", "", "") is True
