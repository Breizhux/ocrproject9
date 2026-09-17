"""Test fonctionnel de l'API RAG (ragifix) via HTTP — Étape 5.

Usage : `python eval/api_test.py` (depuis ocrproject9, venv activé).
Pré-requis : ragifix lancé (`RAG_BASE_URL`) + `.env` renseigné.
NON intégrable au CI GitHub : requiert le RAG local + des clés.

Vérifie : /health, POST /query nominal, question vide,
token invalide (401), filtre ville inexistante (vide, sans erreur).
Sortie : lignes [OK]/[KO] sur stdout, exit 0 si tout passe, 1 sinon.
"""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from config import RAG_BASE_URL, RAGIFIX_API_TOKEN  # noqa: E402

TIMEOUT = 20.0


def check(name, cond, detail="", failures=None):
    print(f"[{'OK' if cond else 'KO'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        failures.append(name)


def headers(token=RAGIFIX_API_TOKEN):
    return {"Authorization": f"Bearer {token}"}


def main():
    failures = []

    # 1. Health
    try:
        r = httpx.get(f"{RAG_BASE_URL}/health", timeout=TIMEOUT)
        check("GET /health -> 200", r.status_code == 200, f"status={r.status_code}",
              failures)
    except httpx.ConnectError:
        print(f"[KO] RAG injoignable ({RAG_BASE_URL}). Il est bien lancé ?")
        return 1

    # 2. Requête nominale : question -> fragments
    r = httpx.post(
        f"{RAG_BASE_URL}/query",
        json={"query": "concerts de musique classique", "top_k": 3,
              "filters": {"city": "Marseille"}},
        headers=headers(), timeout=TIMEOUT,
    )
    results = r.json().get("results", []) if r.status_code == 200 else []
    check("POST /query -> 200 + fragments", r.status_code == 200 and len(results) > 0,
          f"status={r.status_code}, n={len(results)}", failures)
    if results:
        res = results[0]
        check("fragment = text + metadata",
              bool(res.get("text")) and isinstance(res.get("metadata"), dict),
              f"keys={sorted(res.keys())}", failures)

    # 3. Question vide : le serveur ne doit pas exploser (200/400/422 acceptés)
    r = httpx.post(f"{RAG_BASE_URL}/query", json={"query": "", "top_k": 3, "filters": {}},
                   headers=headers(), timeout=TIMEOUT)
    check("POST /query vide -> pas de 500", r.status_code in (200, 400, 422),
          f"status={r.status_code}", failures)

    # 4. Token invalide -> 401
    r = httpx.post(f"{RAG_BASE_URL}/query", json={"query": "test", "top_k": 1, "filters": {}},
                   headers=headers("mauvais-token"), timeout=TIMEOUT)
    check("POST /query mauvais token -> 401", r.status_code == 401,
          f"status={r.status_code}", failures)

    # 5. Ville inexistante -> 200 + zéro résultat (filtre best-effort serveur)
    r = httpx.post(
        f"{RAG_BASE_URL}/query",
        json={"query": "concert", "top_k": 3, "filters": {"city": "VilleInexistanteXYZ"}},
        headers=headers(), timeout=TIMEOUT,
    )
    n = len(r.json().get("results", [])) if r.status_code == 200 else -1
    check("POST /query ville inconnue -> 200 + vide", r.status_code == 200 and n == 0,
          f"status={r.status_code}, n={n}", failures)

    print(f"\n{5 - len(failures)}/5 checks OK.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
