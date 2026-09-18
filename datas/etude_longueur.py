#!/usr/bin/env python3
"""Étude de longueur des événements du connecteur csv_events.

Mesure, pour chaque événement réellement envoyé à ragifix par le connecteur
``csv_events`` de ragifix-collector, le nombre de mots, le nombre de
caractères spéciaux et le nombre de lettres du fragment Markdown qui est
poussé vers l'API.

Objectif : se faire une idée de la longueur maximale d'un événement pour
configurer le chunking de ragifix de façon à ne pas le découper en plusieurs
chunks.

Le connecteur est importé tel qu'il est dans le dépôt, afin de mesurer EXACTEMENT
le contenu envoyé (aucun recopil manuel de la logique de construction du fragment).

Usage :
    python etude_longueur [chemin_vers_le_csv]
    (par défaut : events_propres.csv dans ce dossier)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC = _SCRIPT_DIR.parent / "ragifix-collector" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragifix_collector.connectors.csv_events import CsvEventsConnector  # noqa: E402


def _fragments(connector: CsvEventsConnector):
    """Génère (uid, fragment) pour chaque événement qui sera effectivement envoyé.

    Le connecteur n'émet un Change (et n'envoie donc rien) que pour les lignes
    dotées d'un ``uid`` non vide (voir ``CsvEventsConnector._parse``). On lui
    emboîte donc exactement cette sélection.
    """
    rows = connector._parse()
    for uid, row in rows.items():
        yield uid, connector._build_fragment(row)


def _mesurer(fragment: str) -> dict:
    """Renvoie mots, lettres et caractères spéciaux d'un fragment.

    - mots         : tokens séparés par des espaces (``str.split``).
    - lettres      : caractères alphabétiques (``str.isalpha``), y compris
                     les accents.
    - spéciaux     : caractères qui ne sont ni lettres ni espaces (ponctuation,
                     chiffres, symboles).
    """
    mots = len(fragment.split())
    lettres = sum(1 for c in fragment if c.isalpha())
    speciaux = sum(1 for c in fragment if (not c.isalpha() and not c.isspace()))
    return {"mots": mots, "lettres": lettres, "speciaux": speciaux}


def main() -> int:
    csv_path = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else _SCRIPT_DIR / "events_propres.csv"
    if not csv_path.exists():
        print(f"Fichier introuvable : {csv_path}")
        return 1

    connector = CsvEventsConnector(str(csv_path))

    stats_list: list[dict] = []
    for uid, fragment in _fragments(connector):
        if not fragment.strip():
            continue
        stats = _mesurer(fragment)
        stats.update(uid=uid, fragment=fragment)
        stats_list.append(stats)

    # Tri par nombre de caractères décroissant (la « longueur » d'un événement).
    classe = sorted(stats_list, key=lambda s: len(s["fragment"]), reverse=True)

    if not classe:
        print("Aucun événement à analyser.")
        return 0

    par_mots = sorted(classe, key=lambda s: s["mots"], reverse=True)
    par_caracteres = sorted(classe, key=lambda s: len(s["fragment"]), reverse=True)

    print("1. Événement avec le plus de mot (uid: {}) :".format(par_mots[0]["uid"]))
    print("   - nombre de mot : {}".format(par_mots[0]["mots"]))
    print("   - nombre de caractères : {}".format(len(par_mots[0]["fragment"])))
    print()
    print("2. Événement avec le plus de caractère (uid: {}) :".format(par_caracteres[0]["uid"]))
    print("   - nombre de mot : {}".format(par_caracteres[0]["mots"]))
    print("   - nombre de caractères : {}".format(len(par_caracteres[0]["fragment"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
