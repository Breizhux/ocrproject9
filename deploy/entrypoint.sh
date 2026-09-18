#!/bin/bash
# Orchestration du conteneur tout-en-un (sans superviseur externe) :
#   1. valide la config (deploy/.env via --env-file),
#   2. rend les YAML ragifix/collector depuis les templates,
#   3. démarre ragifix en fond + attente /health,
#   4. lance le collector en one-shot EN FOND (Streamlit ne l'attend pas),
#   5. lance l'API chatbot (uvicorn) EN FOND sur 8000,
#   6. bascule sur Streamlit au premier plan (8501).
set -euo pipefail

# --- 1. Config requise (voir deploy/.env.example) ---
: "${EVENTS_CSV_PATH:?EVENTS_CSV_PATH manquante}"
: "${EMBEDDING_BASE_URL:?EMBEDDING_BASE_URL manquante}"
: "${EMBEDDING_API_KEY:?EMBEDDING_API_KEY manquante}"
: "${EMBEDDING_MODEL:?EMBEDDING_MODEL manquant}"
: "${LLM_API_KEY:?LLM_API_KEY manquante}"
: "${LLM_MODEL:?LLM_MODEL manquant}"

# --- 2. Secrets internes + mapping vers les noms lus par chaque composant ---
# Token ragifix : interne au conteneur, généré à chaque démarrage sauf si fourni.
export RAGIFIX_API_TOKEN="${RAGIFIX_API_TOKEN:-$(python3 -c 'import secrets; print(secrets.token_hex(32))')}"
export EMBEDDING_API_KEY            # lu par ragifix (api_key_env)
export MISTRAL_API_KEY="${LLM_API_KEY}"   # nom lu par src/config.py pour le LLM
export LLM_BASE_URL="${LLM_BASE_URL:-}"
export LLM_MODEL
# RAG_BASE_URL : le défaut de src/config.py (http://127.0.0.1:8421) est déjà bon.

# --- 3. Rendu des configs depuis les templates ---
python3 - <<'EOF'
import os
from string import Template
for tpl, dest in [("/opt/deploy/ragifix.yaml.tpl", "/etc/ragifix/config.yaml"),
                  ("/opt/deploy/collector.yaml.tpl", "/etc/ragifix-collector/config.yaml")]:
    with open(tpl) as f:
        rendered = Template(f.read()).substitute(os.environ)
    with open(dest, "w") as f:
        f.write(rendered)
    print(f"config écrite : {dest}")
EOF

# --- 4. CSV monté ? ---
if [ ! -f "${EVENTS_CSV_PATH}" ]; then
    echo "ERREUR : CSV introuvable : ${EVENTS_CSV_PATH} (monter -v <csv-hôte>:/data:ro)" >&2
    exit 1
fi

# --- 5. ragifix en fond ---
ragifix --config /etc/ragifix/config.yaml &
RAG_PID=$!
trap "kill ${RAG_PID} 2>/dev/null" EXIT

# --- 6. Attente /health (60 s max) ---
for i in $(seq 1 60); do
    if curl -sf -H "Authorization: Bearer ${RAGIFIX_API_TOKEN}" http://127.0.0.1:8421/health >/dev/null; then
        echo "ragifix prêt."
        break
    fi
    if [ "$i" = 60 ]; then
        echo "ERREUR : ragifix ne démarre pas (voir logs ci-dessus)." >&2
        exit 1
    fi
    sleep 1
done

# --- 7. Collector one-shot EN FOND : Streamlit ne l'attend pas ---
# (échec visible uniquement dans /var/log/ocrproject9/collector.log ;
# tant que l'index est vide/partiel, le chatbot répond "rien trouvé")
mkdir -p /var/log/ocrproject9
ragifix-collector --config /etc/ragifix-collector/config.yaml >/var/log/ocrproject9/collector.log 2>&1 &
COL_PID=$!
echo "collector lancé en fond (pid ${COL_PID})."

# --- 8. API chatbot (uvicorn) EN FOND : sans auth, sans réindexation ---
uvicorn api:app --app-dir /opt/chatbot/src --host 0.0.0.0 --port 8000 \
    >/var/log/ocrproject9/api.log 2>&1 &
API_PID=$!
echo "API chatbot lancée en fond sur :8000 (pid ${API_PID})."

# --- 9. Chatbot au premier plan ---
trap "kill ${RAG_PID} ${COL_PID} ${API_PID} 2>/dev/null" EXIT
exec streamlit run /opt/chatbot/src/app.py \
    --server.address 0.0.0.0 --server.port 8501 --server.headless true
