"""Frontend Streamlit via AppTest : vide, réponse + sources, erreur 401."""
from unittest.mock import patch

from langchain_core.documents import Document
from streamlit.testing.v1 import AppTest

import backend
from backend import RagError

APP = "../src/app.py"


def _run(question="", city=""):
    at = AppTest.from_file(APP).run()
    at.text_input[0].set_value(question).run()
    at.text_input[1].set_value(city).run()
    at.button[0].click().run()
    return at


def test_vide():
    at = _run(question="   ")
    assert len(at.warning) == 1


def test_ok():
    from backend import RagError  # noqa
    docs = [Document(page_content="Concert jazz", metadata={"city": "Paris", "score": 0.9, "date": "2026-01-01"})]
    with patch.object(backend, "ask", return_value={"answer": "voilà", "sources": docs}):
        at = _run(question="jazz")
    assert any("voilà" in str(m.value) for m in at.markdown) or any("voilà" in str(t.value) for t in at.text)
    assert len(at.caption) >= 1


def test_401():
    with patch.object(backend, "ask", side_effect=RagError("bad", 401)):
        at = _run(question="jazz")
    assert len(at.error) == 1
    assert "401" in at.error[0].value


def test_500():
    with patch.object(backend, "ask", side_effect=RagError("boom", 500)):
        at = _run(question="jazz")
    assert len(at.error) == 1
    assert "500" in at.error[0].value


def test_erreur_generique():
    with patch.object(backend, "ask", side_effect=RagError("injoignable")):
        at = _run(question="jazz")
    assert len(at.error) == 1


def test_value_error_backend():
    with patch.object(backend, "ask", side_effect=ValueError("Question vide.")):
        at = _run(question="jazz")
    assert len(at.warning) == 1


def test_sans_sources():
    with patch.object(backend, "ask", return_value={"answer": "rien", "sources": []}):
        at = _run(question="jazz")
    assert len(at.info) == 1


def test_defauts_filtres():
    import datetime
    at = AppTest.from_file(APP).run()
    assert at.number_input[0].value == 5
    assert at.text_input[1].value == ""
    assert at.date_input[0].value == datetime.date.today()
    assert at.date_input[1].value is None


def test_filtres_transmis_a_ask():
    import datetime
    with patch.object(backend, "ask", return_value={"answer": "ok", "sources": []}) as m:
        at = AppTest.from_file(APP).run()
        at.text_input[0].set_value("jazz").run()
        at.date_input[0].set_value(datetime.date(2026, 1, 1)).run()
        at.button[0].click().run()
    _, kw = m.call_args
    assert kw["date_min"] == "2026-01-01"
    assert kw["date_max"] == ""
    assert kw["top_k"] == 5
