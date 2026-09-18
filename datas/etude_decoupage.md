# Découpage des données et colonnes envoyées au RAG

Ce document justifie deux choix pour l'ingestion des événements dans ragifix :

1. **comment on découpe les données** : **pas de découpage**, un événement = un fragment ;
2. **quelles colonnes sont réellement envoyées au RAG** : le texte du fragment d'une part, les métadonnées de filtrage d'autre part.

Support : `events_propres.csv` (4 715 événements), colonnes : `uid, title, description, long_description, status, date, city, department, region, address`.


## 1. Principe : un événement = un fragment

On **ne découpe pas** un événement en plusieurs chunks. Chaque événement forme **un seul fragment**.

**Pourquoi ?** Un événement est un petit document structuré et autonome (titre + description + lieu + date). Le découper en morceaux de 512 tokens casserait sa cohérence : un fragment au milieu de la description n'aurait plus de titre ni de sens. À l'inverse, on ne greffe **jamais** plusieurs événements dans un même fragment. On garantit donc :

- **0 événement fragmenté** en plusieurs morceaux ;
- **0 fragment** contenant plusieurs événements.

La cohérence sémantique de l'événement est préservée à 100 %.

> **Note sur le chunking :** la configuration de chunking de ragifix (`token`, 512 tokens, 64 de chevauchement) est le **défaut**, pas une valeur définitive. Le choix « 1 événement = 1 fragment » correspond à un `chunk_size` plus grand que le plus gros événement. Ce point sera réglé plus tard (ajustement de la taille de chunk si nécessaire) — il n'influence pas le présent choix de colonnes.


## 2. Destination des colonnes

| Colonne | Destination | Raison |
|---|---|---|
| `title` | **Fragment** | Court mais ultra-informatif (sujet, lieu, organisateur) ; récupéré sémantiquement. |
| `date` | **Fragment** **+ métadonnées** | Dans le fragment pour le contexte ; en métadonnée pour le filtre exact (« ce weekend »). |
| `address` | **Fragment** | Adresse postale (champ `location_address`) : contexte géographique précis. |
| `long_description` | **Fragment** (préféré) | Corps du texte ; non redondant avec `description` (étude 1). |
| `description` | **Fragment** (fallback) | Utilisée **uniquement si** `long_description` est absente — ne rien perdre. |
| `city` | **Métadonnées (filtre)** | Filtre géographique. |
| `department` | **Métadonnées (filtre)** | Filtre géographique au niveau département. |
| `region` | **Métadonnées (filtre)** | Filtre géographique au niveau région. |
| `status` | **Métadonnées (filtre)** | 4 valeurs (`Programmé`, `Complet`, `Annulé`, `Re-programmé`) ; filtre + exclusion des annulés. |
| `coordinates` | **Exclue** | Coordonnées géographiques (`{"lon":..,"lat":..}`) : n'apportent aucun sens sémantique, cardinalité très élevée. |
| `uid` | **Identifiant** (stocké, pas embarqué) | Référence vers l'origine ; jamais envoyé à l'embedding. |

**Répartition :** le fragment ne contient que du **texte sémantique** (`title`, `date`, `address`, `description`). Les champs structurés de localisation fine (`city`, `department`, `region`, `status`) sont stockés en **métadonnées** sur le fragment et servis comme **filtres exacts** par le chatbot. Ils ne sont **pas** embarqués : ce ne sont pas des textes naturels, on ne veut pas brouiller la recherche sémantique avec des valeurs structurées.


## 3. Template du fragment (Markdown)

Le fragment envoyé à ragifix est un fragment Markdown rempli à partir des données de l'événement :

```md
## Titre de l'évène
{titre de l'évène}

## Date de l'évène
{date de l'évène}

## Adresse de l'évène
{adresse de l'évène}

## Description de l'évène
{description de l'évène}
```

**Règles de construction :**

- **Description : favori `long_description`, fallback `description`.** On utilise `long_description` quand elle est présente ; **si elle est absente, on prend `description`** (jamais de fragment sans description). Dans l'échantillon, 582 événements sur 4 715 n'ont pas de `long_description` — elles ont toutes une `description`.

- La `long_description` (ou la `description`) issue de l'API peut contenir du **HTML** (`<h2>`, `<p>`, `<em>`…) — on le **supprime** pour n'envoyer que du texte clair (remplacement des entités `&nbsp;`, `&amp;`…).

- **Adresse :** issue du champ `location_address` de l'API (ex. `rond point prado, 13008 Marseille`). Elle est présente sur 100 % des événements de l'échantillon. Si elle est absente, on omet la section.

- **Date :** issue du champ `firstdate_begin` (ISO 8601). On peut la formater plus lisiblement (« samedi 4 septembre 2026 à 15h00 ») — voir point 5.

- Chaque section est **optionnelle si sa donnée est absente** : le fragment garde toujours au moins le titre.

**Exemple rempli :**

```md
## Titre de l'évène
Lily Pastré : Mécène au grand cœur

## Date de l'évène
2026-09-20T08:30:00+00:00

## Adresse de l'évène
157 avenue de Montredon, 13008 Marseille

## Description de l'évène
Découverte du parcours d'une femme engagée et d'une famille à travers la visite guidée du parc
Pastré, complétée par la visite de Château Pastré.

RDV : devant les grilles du Parc Pastré
Bus : n°19 (Montredon Pastré)
Vélo : Parc Pastré
Réservation obligatoire - Nombre de places limité
```


## 4. Métadonnées associées (filtres)

Chaque fragment est accompagné, côté ragifix, de ses métadonnées structurées :

```json
{
  "date": "2026-09-20T08:30:00+00:00",
  "city": "Marseille",
  "department": "Bouches-du-Rhône",
  "region": "Provence-Alpes-Côte d'Azur",
  "status": "Programmé",
  "uid": 80686179
}
```

- `date`, `city`, `department`, `region`, `status` → **filtres exacts** (recherche bornée).
   Ex. : « qu'est-ce qui se passe ce weekend à Marseille ? » → filtre `city=Marseille` + `date` dans la fenêtre + recherche sémantique sur le fragment.

- `status` permet d'**exclure** les événements annulés (`Annulé`).

- `uid` est conservé comme identifiant (retourné avec les résultats) mais **n'est pas embarqué**.

> `coordinates` a été **supprimée** du dataset (`events_propres.csv`) et du pipeline : sa cardinalité est très élevée et elle n'ajoute aucun sens sémantique. `address` (champ `location_address`) lui est **intégrée au fragment**.


## 5. Décisions prises (et alternatives possibles)

| Choix | Décision | Alternative |
|---|---|---|
| Découpage intra-événement | **Aucun** (1 événement = 1 fragment) | Chunking 512 tokens — à ajuster plus tard si besoin. |
| `title` | embarqué dans le fragment | possible aussi en métadonnée — mais l'embarquer le rend récupérable sémantiquement. |
| `date` | fragment **+ métadonnée** | seulement métadonnée (filtre) — mais le contexte date aide le modèle. |
| `address` | fragment | possible aussi en métadonnée — trop fine pour un filtre exact. |
| Description favorite/fallback | **`long_description`, sinon `description`** | ne garder que `long_description` (perdrait 12 % des événements). |
| Format `date` | ISO 8601 | formatter en date lisible (fr) pour le fragment. |
| HTML dans la description | **retiré** | garder les balises — bruit pour l'embedding. |
