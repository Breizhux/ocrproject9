"""Eval POC : interroge l'API chatbot (POST /ask), fuzzy (thefuzz) + cosinus
d'embeddings locaux (Model2Vec FR). Sortie stdout.

Pré-requis : API lancée (`uvicorn api:app --app-dir src --port 8000`).
"""
import json
import math
import os

import httpx
from model2vec import StaticModel
from thefuzz import fuzz

API = "http://127.0.0.1:8000"

DATA = os.path.join(os.path.dirname(__file__), "dataset.jsonl")
MODEL = "minishlab/M2V_multilingual_output"  # distille de LaBSE, bon en francais


def cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def get_answer(question: str, city: str = "", top_k: int = 5) -> str:
    """Interroge l'API chatbot (POST /ask). Lève httpx.HTTPError en cas d'échec."""
    r = httpx.post(f"{API}/ask", json={"question": question, "city": city,
                                       "top_k": top_k}, timeout=120)
    r.raise_for_status()
    return r.json()["reponse"]


def main():
    try:
        httpx.get(f"{API}/health", timeout=5).raise_for_status()
    except httpx.HTTPError:
        print(f"ERREUR : API chatbot injoignable sur {API}. "
              "Lance-la : uvicorn api:app --app-dir src --port 8000")
        return
    model = StaticModel.from_pretrained(MODEL)
    rows = [json.loads(line) for line in open(DATA, encoding="utf-8") if line.strip()]
    fuzzes, coss = [], []
    for i, row in enumerate(rows, 1):
        try:
            got = get_answer(row["question"], city=row.get("city", ""),
                             top_k=row.get("top_k", 5))
        except Exception as e:
            print(f"[{i}] {row['question'][:60]}... -> ERREUR : {e}")
            continue
        f = fuzz.token_set_ratio(got, row["reponse_attendue"])
        fuzzes.append(f)
        va, vb = model.encode([got[:4000], row["reponse_attendue"]])
        c = cosine(va, vb)
        coss.append(c)
        print(f"[{i}] {row['question'][:60]}...")
        print(f"     fuzzy={f}  cos={c:.2f}")
        print(f"     obtenu : {got[:150]}...")
    print(f"\nMOYENNE fuzzy={sum(fuzzes)/len(fuzzes):.1f} (n={len(fuzzes)})", end="")
    if coss:
        print(f"  cos={sum(coss)/len(coss):.2f} (n={len(coss)})")
    else:
        print("  cos=n/a")


if __name__ == "__main__":
    main()
