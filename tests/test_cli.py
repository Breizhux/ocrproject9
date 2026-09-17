"""CLI backend.main() : affichage réponse + sources, erreurs propres."""
from unittest.mock import patch

from langchain_core.documents import Document

import backend


def test_cli_ok(capsys):
    fake = {"answer": "hello", "sources": [Document(page_content="x" * 200, metadata={"score": 0.1})]}
    with patch.object(backend, "ask", return_value=fake) as m:
        backend.main(["question?", "--city", "Paris", "--top-k", "2",
                      "--date-min", "2026-01-01", "--date-max", "2026-12-31"])
    _, kw = m.call_args
    assert kw["date_min"] == "2026-01-01" and kw["date_max"] == "2026-12-31"
    out = capsys.readouterr().out
    assert "hello" in out
    assert "Sources" in out


def test_cli_erreur_propre(capsys):
    with patch.object(backend, "ask", side_effect=ValueError("Question vide.")):
        backend.main(["   "])
    assert "Erreur" in capsys.readouterr().out
