"""Eval sources POC : interroge le RAG (POST /query) et compare les uids
obtenus aux sources attendues du dataset. Sortie stdout.

Pré-requis : RAG lancé (GET /health) + token dans RAGIFIX_API_TOKEN.
"""
import json
import os

import httpx

RAG = os.environ.get("RAG_BASE_URL", "http://127.0.0.1:8421")
TOKEN = os.environ.get("RAGIFIX_API_TOKEN", "")

DATA = os.path.join(os.path.dirname(__file__), "dataset.jsonl")


def get_sources(question: str, city: str = "", top_k: int = 5) -> list:
    """Interroge le RAG (POST /query), renvoie les uids obtenus."""
    filters = {"city": city} if city.strip() else {}
    r = httpx.post(f"{RAG}/query",
                   json={"query": question, "top_k": top_k, "filters": filters},
                   headers={"Authorization": f"Bearer {TOKEN}"},
                   timeout=120)
    r.raise_for_status()
    return [str(res["metadata"]["uid"]) for res in r.json().get("results", [])]


def main():
    if not TOKEN:
        print("ERREUR : RAGIFIX_API_TOKEN manquant dans l'environnement.")
        return
    try:
        httpx.get(f"{RAG}/health", timeout=5).raise_for_status()
    except httpx.HTTPError:
        print(f"ERREUR : RAG injoignable sur {RAG}.")
        return
    rows = [json.loads(line) for line in open(DATA, encoding="utf-8") if line.strip()]
    total_ok, total_exp = 0, 0
    for i, row in enumerate(rows, 1):
        exp = row.get("sources", [])
        try:
            # top_k = nb de sources attendues, plafonné au max accepté par le RAG (100)
            got = get_sources(row["question"], city=row.get("city", ""),
                              top_k=min(len(exp), 100) or row.get("top_k", 5))
        except Exception as e:
            print(f"[{i}] {row['question'][:60]}... -> ERREUR : {e}")
            continue
        ok = len([u for u in exp if u in got])
        total_ok += ok
        total_exp += len(exp)
        print(f"[{i}] {row['question'][:60]}... -> {ok}/{len(exp)}")
    pct = 100 * total_ok / total_exp if total_exp else 0
    print(f"\nNOTE GLOBALE sources={total_ok}/{total_exp} ({pct:.0f}%)")


if __name__ == "__main__":
    main()
