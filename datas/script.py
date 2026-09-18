import json
import requests
import pandas as pd

# --- Authentification : les headers remplacent la clé d'API ---
HEADERS = {
    "Host": "hub.huwise.com",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
    "Referer": "https://hub.huwise.com/explore/assets/evenements-publics-openagenda/api/",
    "X-CSRFToken": "gacEKPbHmxKkDFPbjrzgajgkW5w3RqHw",
    "Cookie": "csrftoken=gacEKPbHmxKkDFPbjrzgajgkW5w3RqHw",
}

BASE_URL = "https://hub.huwise.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/records"

# --- Paramètres de filtrage (à adapter) ---
CITY = "Marseille"     # ex: "Marseille"  ->  None = toutes les villes
DEPARTMENT = None      # ex: "Bouches-du-Rhone" -> None = tous les départements
START_DATE = "2025-09-04"   # il y a 1 an
END_DATE = "2027-12-31"     # événements à venir
PAGE_SIZE = 100


def years_in_period():
    """Retourne la liste des années couvertes par la période de filtrage."""
    start_year = int(START_DATE[:4])
    end_year = int(END_DATE[:4])
    return list(range(start_year, end_year + 1))


def build_refine():
    """Construit les critères de filtrage serveur (ville / département)."""
    refine = []
    if CITY:
        refine.append(f"location_city:{CITY}")
    if DEPARTMENT:
        refine.append(f"location_department:{DEPARTMENT}")
    return refine


def fetch_events(refine, offset=0, limit=PAGE_SIZE):
    """Récupère une page d'événements filtrés depuis l'API."""
    params = {"lang": "fr", "limit": limit, "offset": offset, "refine": refine}
    response = requests.get(BASE_URL, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()["results"]


def fetch_paged(refine):
    """Pagine une seule requête filtrée et renvoie tous les résultats."""
    events = []
    offset = 0
    while True:
        batch = fetch_events(refine, offset, PAGE_SIZE)
        if not batch:
            break
        events.extend(batch)
        offset += PAGE_SIZE
        if len(batch) < PAGE_SIZE:
            break
    return events


def fetch_all(refine_base):
    """Récupère tous les événements, une année filtrée à la fois."""
    events = []
    for year in years_in_period():
        refine = refine_base + [f"firstdate_begin:{year}"]
        events.extend(fetch_paged(refine))
    return events


def in_period(event):
    """Vérifie que la date de l'événement est dans la période souhaitée."""
    date_str = event.get("firstdate_begin")
    if not date_str:
        return False
    date = date_str[:10]
    return START_DATE <= date <= END_DATE


def clean_event(event):
    """Extrait les champs utiles et nettoie le statut (format JSON de l'API)."""
    status = event.get("status")
    if isinstance(status, str):
        try:
            status = json.loads(status).get("label", {}).get("fr", status)
        except Exception:
            pass
    return {
        "uid": event.get("uid"),
        "title": event.get("title_fr"),
        "description": event.get("description_fr"),
        "long_description": event.get("longdescription_fr"),
        "status": status,
        "date": event.get("firstdate_begin"),
        "city": event.get("location_city"),
        "department": event.get("location_department"),
        "region": event.get("location_region"),
        "address": event.get("location_address"),
    }


def main():
    print("Récupération des événements...")
    refine = build_refine()
    raw = fetch_all(refine)
    print(f"{len(raw)} événements bruts récupérés.")

    filtered = [e for e in raw if in_period(e)]
    print(f"{len(filtered)} événements après affinage client des dates.")

    records = [clean_event(e) for e in filtered]
    df = pd.DataFrame(records)

    if "address" in df.columns:
        df["address"] = df["address"].apply(
            lambda a: " ".join(str(a).split()) if a else None
        )

    df.to_csv("events_propres.csv", index=False)
    print(f"Dataset propre enregistré : events_propres.csv ({len(df)} lignes)")
    return df


if __name__ == "__main__":
    main()
