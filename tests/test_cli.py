"""CLI backend.main() : affichage réponse + sources, erreurs propres."""
from unittest.mock import patch

from langchain_core.documents import Document

import backend


def test_cli_ok(capsys):
    fake = {"answer": "hello", "sources": [Document(page_content="x" * 200, metadata={"score": 0.1})]}
    with patch.object(backend, "ask", return_value=fake):
        backend.main(["question?", "--city", "Paris", "--top-k", "2"])
    out = capsys.readouterr().out
    assert "hello" in out
    assert "Sources" in out


def test_cli_erreur_propre(capsys):
    with patch.object(backend, "ask", side_effect=ValueError("Question vide.")):
        backend.main(["   "])
    assert "Erreur" in capsys.readouterr().out
