# Template de config ragifix pour le conteneur (repris de la config actuelle).
# Variables d'environnement substituées au démarrage par entrypoint.sh.
# Non exposé : chunking, vectorstore faiss, chemins internes, port.

chunking:
  strategy: token
  chunk_size: 8192
  chunk_overlap: 0

embedding:
  backend: openai_compatible
  openai_compatible:
    base_url: "${EMBEDDING_BASE_URL}"
    api_key_env: EMBEDDING_API_KEY
    model: ${EMBEDDING_MODEL}

vectorstore:
  backend: faiss
  faiss:
    index_path: /var/lib/ragifix/faiss_index

registry:
  backend: sqlite
  sqlite:
    path: /var/lib/ragifix/registry.db

api:
  host: 127.0.0.1
  port: 8421
  auth_token_env: RAGIFIX_API_TOKEN
  default_top_k: 5
  max_document_size_mb: 50

logging:
  level: INFO
