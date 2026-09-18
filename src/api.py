"""API REST du chatbot (Etape 5 consigne) : POST /ask -> reponse augmentee.

Sans authentification, sans reindexation : le RAG reste independant,
l'API ne fait qu'interroger backend.ask() (RAG lecture seule + LLM).
Lancement depuis ocrproject9/ : uvicorn api:app --app-dir src --port 8000
"""
from backend import RagError, ask
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="ocrproject9 chatbot API")


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    city: str = ""
    top_k: int = Field(default=5, ge=1, le=50)
    date_min: str = ""
    date_max: str = ""


class Source(BaseModel):
    contenu: str = ""
    metadata: dict = {}


class AskResponse(BaseModel):
    reponse: str
    sources: list[Source] = []


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask_question(req: AskRequest):
    try:
        res = ask(req.question, city=req.city, top_k=req.top_k,
                  date_min=req.date_min, date_max=req.date_max)
    except RagError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {
        "reponse": res["answer"],
        "sources": [
            {"contenu": getattr(d, "page_content", str(d)),
             "metadata": dict(getattr(d, "metadata", {}) or {})}
            for d in res.get("sources", [])
        ],
    }
