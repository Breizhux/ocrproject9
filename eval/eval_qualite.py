"""Eval qualité du chatbot via Ragas : fidélité, pertinence, précision et
rappel du contexte — POST /ask sur chaque question du dataset, comparaison à
`reponse_attendue`. Sortie stdout.

LLM juge = Mistral (MISTRAL_API_KEY / LLM_BASE_URL lus dans ocrproject9/.env
via src/config) ; embeddings = model2vec locaux, aucune clé.

Pré-requis : API lancée (`uvicorn api:app --app-dir src --port 8000`) et
ragas + langchain-mistralai installés dans eval/venv.
"""
import json
import os
import sys
from pathlib import Path

import httpx
from langchain_mistralai import ChatMistralAI
from model2vec import StaticModel
from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset
from ragas.embeddings import BaseRagasEmbeddings
from ragas.metrics import (answer_relevancy, context_precision,
                           context_recall, faithfulness)
from ragas.run_config import RunConfig

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from config import LLM_BASE_URL, LLM_MODEL, MISTRAL_API_KEY

API = "http://127.0.0.1:8000"
DATA = os.path.join(os.path.dirname(__file__), "dataset.jsonl")


class Model2VecEmbeddings(BaseRagasEmbeddings):
    """Embeddings Ragas locaux (model2vec FR) : ni clé ni appel réseau."""

    def __init__(self):
        super().__init__()
        self.model = StaticModel.from_pretrained(
            "minishlab/M2V_multilingual_output")

    def embed_query(self, text: str) -> list:
        return self.model.encode([text])[0].tolist()

    def embed_documents(self, texts: list) -> list:
        return self.model.encode(list(texts)).tolist()

    async def aembed_query(self, text: str) -> list:
        return self.embed_query(text)

    async def aembed_documents(self, texts: list) -> list:
        return self.embed_documents(texts)


def main():
    try:
        httpx.get(f"{API}/health", timeout=None).raise_for_status()
    except httpx.HTTPError:
        print(f"ERREUR : API injoignable sur {API} "
              "(lance : uvicorn api:app --app-dir src --port 8000)")
        return
    rows = [json.loads(l) for l in open(DATA, encoding="utf-8") if l.strip()]
    samples = []
    for i, row in enumerate(rows, 1):
        try:
            r = httpx.post(f"{API}/ask", json={
                "question": row["question"],
                "city": row.get("city", ""),
                "top_k": row.get("top_k", 5)}, timeout=None)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as e:
            print(f"[{i}/{len(rows)}] HTTP {e.response.status_code} : "
                  f"{e.response.text[:200]}")
        except Exception as e:
            print(f"[{i}/{len(rows)}] {type(e).__name__} : {e}")
            continue
        samples.append({
            "user_input": row["question"],
            "retrieved_contexts": [s["contenu"] for s in data.get("sources", [])
                                   if s["contenu"]],
            "response": data["reponse"],
            "reference": row["reponse_attendue"],
        })
        print(f"[{i}/{len(rows)}] {row['question'][:60]}...")
    kwargs = {"model": LLM_MODEL, "api_key": MISTRAL_API_KEY or "not-needed",
              "timeout": 300,  # LLM local lent : 120s (defaut) insuffisant
              # Qwen3.6 : coupe la chaine de raisonnement du juge (standard Qwen3)
              "model_kwargs": {"chat_template_kwargs": {"enable_thinking": False}}}
    if LLM_BASE_URL:
        kwargs["endpoint"] = LLM_BASE_URL  # meme construction que backend.py
    res = evaluate(EvaluationDataset.from_list(samples),
                   metrics=[faithfulness, answer_relevancy,
                            context_precision, context_recall],
                   llm=ChatMistralAI(**kwargs),
                   embeddings=Model2VecEmbeddings(),
                   run_config=RunConfig(max_workers=4))  # pas 16 : gateway sature
    print("\nMETRICS RAGAS :", res)


if __name__ == "__main__":
    main()
