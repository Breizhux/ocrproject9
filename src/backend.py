"""Backend POC : client /query + Retriever + chaine ask(). Moche mais minimal."""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import argparse
import httpx
from typing import List
from pydantic import Field
from datetime import date, datetime

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_mistralai import ChatMistralAI

from config import MISTRAL_API_KEY, RAGIFIX_API_TOKEN, RAG_BASE_URL, LLM_BASE_URL, LLM_MODEL


class RagError(Exception):
    def __init__(self, message: str, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def _parse_day(value):
    """Jour civil depuis datetime/date/ISO. None si inexploitable."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value or "").strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _in_range(meta_date, date_min: str, date_max: str) -> bool:
    """Filtre date client : le RAG ne sait faire que de l'egalite exacte (best-effort)."""
    if not date_min and not date_max:
        return True
    day = _parse_day(meta_date)
    if day is None:
        return True  # pas de date exploitable : on garde (best-effort)
    dmin = _parse_day(date_min)
    dmax = _parse_day(date_max)
    if dmin and day < dmin:
        return False
    if dmax and day > dmax:
        return False
    return True


def query_rag(query: str, top_k: int = 5, city: str = "", date_min: str = "", date_max: str = "") -> list:
    """Appel direct POST /query (lecture seule, on ne touche jamais au RAG)."""
    if not query.strip():
        raise ValueError("Question vide.")
    filters = {}
    if city.strip():
        filters = {"city": city.strip()}
    fetch_k = top_k * 3 if (date_min or date_max) else top_k
    try:
        r = httpx.post(
            f"{RAG_BASE_URL}/query",
            json={"query": query, "top_k": fetch_k, "filters": filters},
            headers={"Authorization": f"Bearer {RAGIFIX_API_TOKEN}"},
            timeout=20.0,
        )
    except httpx.ConnectError:
        raise RagError("RAG injoignable (http://127.0.0.1:8421). Il est bien lancé ?")
    if r.status_code == 401:
        raise RagError("Token RAG invalide (401). Vérifie RAGIFIX_API_TOKEN.", 401)
    if r.status_code >= 500:
        raise RagError(f"Le RAG a renvoyé une erreur {r.status_code}. Réessaie plus tard.", r.status_code)
    if r.status_code != 200:
        raise RagError(f"Erreur RAG inattendue ({r.status_code}) : {r.text[:200]}", r.status_code)
    data = r.json()
    results = data.get("results", [])
    results = [res for res in results
               if _in_range((res.get("metadata") or {}).get("date"), date_min, date_max)]
    return results[:top_k]


class RagifixRetriever(BaseRetriever):
    top_k: int = Field(default=5)
    city: str = Field(default="")
    date_min: str = Field(default="")
    date_max: str = Field(default="")

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        results = query_rag(query, top_k=self.top_k, city=self.city,
                            date_min=self.date_min, date_max=self.date_max)
        docs = []
        for res in results:
            meta = res.get("metadata", {}) or {}
            meta.update({
                "chunk_id": res.get("chunk_id", ""),
                "doc_id": res.get("doc_id", ""),
                "score": res.get("score", 0),
                "origin": res.get("origin", ""),
            })
            docs.append(Document(page_content=res.get("text", ""), metadata=meta))
        return docs


PROMPT_FR = ChatPromptTemplate.from_messages([
    ("system", "Tu es un assistant qui recommande des événements. Réponds en français, uniquement à partir du contexte. Si le contexte est vide, dis que tu n'as rien trouvé."),
    ("human", "Question : {question}\n\nContexte :\n{context}"),
])


def ask(question: str, city: str = "", top_k: int = 5, date_min: str = "", date_max: str = "") -> dict:
    """Chaine RAG : retrieve puis ChatMistralAI (ou endpoint custom via LLM_BASE_URL)."""
    if not question.strip():
        raise ValueError("Question vide.")
    if not LLM_BASE_URL and not MISTRAL_API_KEY:
        raise RagError("MISTRAL_API_KEY manquante (voir .env).")
    retriever = RagifixRetriever(top_k=top_k, city=city, date_min=date_min, date_max=date_max)
    docs = retriever.invoke(question)
    if not docs:
        return {"answer": "Je n'ai rien trouvé pour cette recherche.", "sources": []}
    date = datetime.now().strftime("Nous sommes le %d %h %Y")
    context = date+"\n\n---\n\n".join(d.page_content for d in docs)
    kwargs = {"model": LLM_MODEL, "api_key": MISTRAL_API_KEY or "not-needed"}
    if LLM_BASE_URL:
        kwargs["endpoint"] = LLM_BASE_URL
    llm = ChatMistralAI(**kwargs)
    chain = PROMPT_FR | llm
    out = chain.invoke({"question": question, "context": context})
    return {"answer": out.content, "sources": docs}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("--city", default="")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--date-min", default="")
    p.add_argument("--date-max", default="")
    a = p.parse_args(argv)
    try:
        res = ask(a.question, city=a.city, top_k=a.top_k, date_min=a.date_min, date_max=a.date_max)
        print(res["answer"])
        print("\n--- Sources ---")
        for d in res["sources"]:
            m = d.metadata
            print(f"- [{m.get('score', 0):.2f}] {m.get('city', '?')} | {d.page_content[:120]}...")
    except (ValueError, RagError) as e:
        print(f"Erreur : {e}")


if __name__ == "__main__":
    main()
