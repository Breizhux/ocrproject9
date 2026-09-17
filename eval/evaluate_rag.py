"""Eval (Étape 5, evaluate_rag.py) : cosinus réponse système vs réponse humaine.

Usage : `python eval/evaluate_rag.py` (depuis ocrproject9, venv activé).
Base : `eval/dataset.jsonl` (question/city/top_k/reponse_attendue).
Pré-requis : ragifix lancé + boîte LLM (`ocrproject9/.env`).
NON intégrable au CI GitHub : requiert le RAG local + des clés.

Métrique unique, 100 % mathématique (Étape 4 : « même sens » = correct) :
similarité cosinus entre les embeddings Model2Vec locaux de la réponse
produite par ask() et de la réponse annotée. Pas de LLM-juge, pas de Ragas.
Sortie stdout, exit toujours 0.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from model2vec import StaticModel

from backend import ask

DATA = os.path.join(os.path.dirname(__file__), "dataset.jsonl")
MODEL = "minishlab/M2V_multilingual_output"  # même modèle que eval_qualite.py


def cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def main():
    model = StaticModel.from_pretrained(MODEL)
    rows = [json.loads(line) for line in open(DATA, encoding="utf-8") if line.strip()]
    scores = []
    for i, row in enumerate(rows, 1):
        try:
            got = ask(row["question"], city=row.get("city", ""),
                      top_k=row.get("top_k", 5))["answer"]
        except Exception as e:
            print(f"[{i}] {row['question'][:60]}... -> ERREUR : {e}")
            continue
        va, vb = model.encode([got[:4000], row["reponse_attendue"]])
        c = cosine(va, vb)
        scores.append(c)
        print(f"[{i}] {row['question'][:60]}... -> cos={c:.2f}")
    print(f"\nMOYENNE cos={sum(scores)/len(scores):.2f} (n={len(scores)})")


if __name__ == "__main__":
    main()
