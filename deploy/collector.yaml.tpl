# Template de config ragifix-collector pour le conteneur (repris de la config actuelle).
# Variables d'environnement substituées au démarrage par entrypoint.sh.
# Non exposé : type de source forcément `csv_events` (consigne), one-shot,
# URL ragifix interne, chemins internes.

ragifix:
  base_url: "http://127.0.0.1:8421"
  api_token_env: RAGIFIX_API_TOKEN
  timeout_seconds: 60

sync:
  interval_seconds: 0                # one-shot : un seul cycle puis arrêt
  max_retries: 5

sources:
  - name: events
    type: csv_events
    enabled: true
    description: "Événements (CSV monté dans le conteneur)"
    path: ${EVENTS_CSV_PATH}

state_store:
  backend: sqlite
  sqlite:
    path: /var/lib/ragifix-collector/state.db

logging:
  level: INFO
