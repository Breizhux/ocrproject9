# ocrproject9 — chatbot Étape 4 (POC)

Chatbot RAG minimaliste (POC, pas de mise en prod).
Le vrai RAG tourne déjà en local (`ragifix` + `ragifix-collector` + `ragifix-mcp`) :
ce dépôt l'utilise **en lecture seule via HTTP**, sans jamais le modifier.

- Base RAG : `http://127.0.0.1:8421`
- `GET /health` sans auth, `POST /query` avec `Authorization: Bearer $RAGIFIX_API_TOKEN`
- Stack : `langchain, langchain-mistralai, httpx, streamlit, python-dotenv, pytest`

## Structure POC (tout dans `src/`)

- `src/config.py` : lit `.env` (`MISTRAL_API_KEY`, `RAGIFIX_API_TOKEN`, `RAG_BASE_URL`)
- `src/backend.py` : client `/query` + `RagifixRetriever` (BaseRetriever) + `ask(question, city, top_k)` (ChatMistralAI `mistral-small-latest` + prompt FR)
- `src/app.py` : Streamlit minimal (question + ville + top_k, réponse + Sources). Pas d'historique.

## Lancer (sans sortir de `ocrproject9/`)

```bash
cd ocrproject9
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # puis renseigner les vraies clés
streamlit run src/app.py
```

CLI rapide :

```bash
python src/backend.py "Quels concerts à Paris ?" --city Paris --top-k 5
```

## Justification 4 dépôts (résumé soutenance)

Consigne sous-entend un seul dépôt, mais le RAG existait déjà chez Niji en 3 briques (`ragifix` : API ingestion/recherche, `ragifix-collector` : ETL, `ragifix-mcp` : pont MCP). Ce dépôt `ocrproject9` est uniquement le chatbot Étape 4 qui les réutilise en lecture seule. Détail complet : voir README final (à venir avec `eval/resultats.md`).
