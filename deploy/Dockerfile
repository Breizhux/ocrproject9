# Image tout-en-un : ragifix + ragifix-collector + chatbot ocrproject9.
# Contexte de build = racine du dépôt ocrproject9 :
#   docker build -f deploy/Dockerfile -t ocrproject9 .
# ragifix et ragifix-collector sont TOUJOURS pris sur la branche `ocr`
# de leurs dépôts GitHub (seule branche compatible avec ce projet).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- RAG : ragifix + collector depuis GitHub @ocr (jamais en local) ---
RUN pip install --no-cache-dir \
    "ragifix @ git+https://github.com/ragifix/ragifix.git@ocr" \
    "ragifix-collector @ git+https://github.com/ragifix/ragifix-collector.git@ocr"

# --- Chatbot : dépendances runtime seules (sans pytest/eval) ---
COPY deploy/requirements.chatbot.txt /tmp/requirements.chatbot.txt
RUN pip install --no-cache-dir -r /tmp/requirements.chatbot.txt \
    && rm /tmp/requirements.chatbot.txt

# --- Chatbot : code + scripts d'orchestration ---
COPY src/ /opt/chatbot/src/
COPY deploy/entrypoint.sh deploy/ragifix.yaml.tpl deploy/collector.yaml.tpl /opt/deploy/
RUN chmod +x /opt/deploy/entrypoint.sh \
    && mkdir -p /etc/ragifix /etc/ragifix-collector /var/lib/ragifix /var/lib/ragifix-collector /data

# 8421 = ragifix, interne au conteneur (jamais publié).
# 8501 = Streamlit, 8000 = API chatbot (uvicorn).
EXPOSE 8501 8000

ENTRYPOINT ["/opt/deploy/entrypoint.sh"]
