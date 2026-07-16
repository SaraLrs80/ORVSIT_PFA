# ORVSIT — Observatoire des disparités territoriales de la région Tanger-Tétouan-Al Hoceïma

Projet de Fin d'Année (PFA) — plateforme d'aide à la décision pour **mesurer, comparer et visualiser les disparités territoriales** de la région TTA, réalisée pour l'**Observatoire Régional de Veille Stratégique et d'Intelligence Territoriale (ORVSIT)** du Conseil régional de Tanger-Tétouan-Al Hoceïma.

La plateforme s'appuie sur un **entrepôt de données territoriales** consolidé à partir de sources officielles (HCP, RGPH 2024, départements sectoriels, Open Data Maroc) et propose des tableaux de bord comparatifs, des fiches territoriales, une cartographie des vulnérabilités et un assistant conversationnel.

---

## Sommaire

- [Objectifs](#objectifs)
- [Architecture](#architecture)
- [Structure du dépôt](#structure-du-dépôt)
- [Sources de données](#sources-de-données)
- [Démarche data (ETL)](#démarche-data-etl)
- [Modèle de données](#modèle-de-données)
- [Indices synthétiques](#indices-synthétiques)
- [Installation & exécution](#installation--exécution)
- [Rôles utilisateurs](#rôles-utilisateurs)
- [Maquette](#maquette)
- [Feuille de route](#feuille-de-route)
- [Auteur](#auteur)

---

## Objectifs

- Recenser et consolider les indicateurs territoriaux disponibles à l'échelle de la région, des provinces/préfectures et des communes.
- Mesurer les écarts entre territoires sur plusieurs dimensions (démographie, social, équipements, mobilité, économie, environnement).
- Construire des **indices synthétiques** de développement et de vulnérabilité territoriale.
- Offrir des **outils visuels d'aide à la décision** : vue d'ensemble, comparaison, fiches, cartographie.
- Fournir une lecture stratégique exploitable par le Conseil régional et l'ORVSIT.

## Architecture

```
                 Sources officielles (HCP, RGPH, ministères, Open Data)
                                    │
                       ┌────────────▼─────────────┐
                       │   Pipeline data (Python)  │   nettoyage · harmonisation · catalogue
                       └────────────┬─────────────┘
                                    │
             ┌──────────────────────▼───────────────────────┐
             │   PostgreSQL — dwh_orvsit  (data warehouse)   │
             │   referential.*  +  schémas par thème (faits) │
             └──────────────────────┬───────────────────────┘
                                    │  (lecture seule)
                       ┌────────────▼─────────────┐        ┌───────────────────────────┐
                       │   Backend API (Python)    │◄──────►│  PostgreSQL — orvsit_app  │
                       └────────────┬─────────────┘        │  utilisateurs · demandes  │
                                    │                       │  assistant IA · usage     │
                       ┌────────────▼─────────────┐        └───────────────────────────┘
                       │   Frontend (React/Vite)   │
                       └───────────────────────────┘
```

Deux bases PostgreSQL distinctes :

- **`dwh_orvsit`** — l'entrepôt analytique (données territoriales TTA). En lecture seule pour l'application.
- **`orvsit_app`** — les données applicatives (comptes, demandes d'accès, conversations de l'assistant IA, journal d'usage).

## Structure du dépôt

```
PROJET_PFA/
├── README.md
├── .gitignore
├── .env.example
├── data-pipeline/              # partie Data (anciennement « TestData »)
│   ├── charger_postgres.py            # chargement du DWH dans PostgreSQL
│   ├── construire_catalogue.py        # construction du catalogue d'indicateurs
│   ├── construire_dim_indicateur_et_faits.py
│   ├── diagnostic_avant_construction.py
│   ├── dim_territoire.csv             # dimension territoire (hiérarchie complète)
│   ├── dim_indicateur.csv             # catalogue des indicateurs
│   ├── dim_etablissement_scolaire.csv
│   ├── faits/                         # tables de faits nettoyées, par thème
│   │   ├── demography/  education/  health/
│   │   ├── infrastructure/  climate/  socio_economic/
│   └── data/                          # sources brutes (Excel) — NON versionné
├── database/                   # base applicative
│   ├── orvsit_app_schema.sql          # DDL : utilisateurs, demandes, IA, usage
│   └── init_app_db.py                 # création + initialisation de orvsit_app
├── backend/                    # API (Python) — à développer
├── frontend/                   # interface React / Vite
└── docs/
    └── maquette/                      # maquette interactive (ORVSIT_Dashboard.html)
```

> **Note** — la partie Data a été réalisée dans un dossier `TestData`. Au démarrage du
> développement, renommez-le `data-pipeline` et placez-le dans ce dépôt (voir plus bas).

## Sources de données

Uniquement des sources officielles et publiques :

- **HCP** — Haut-Commissariat au Plan
- **RGPH 2024** — Recensement Général de la Population et de l'Habitat
- **Départements ministériels sectoriels** — santé, éducation, énergie, agriculture…
- **Open Data Maroc** et indicateurs communaux/provinciaux publics
- **Documents régionaux** — SRAT, PDR, études sectorielles

## Démarche data (ETL)

1. **Collecte** — récupération des jeux de données par thème (démographie, santé, éducation, socio-économique, infrastructure, climat).
2. **Diagnostic** (`diagnostic_avant_construction.py`) — repérage des valeurs manquantes, doublons, formats hétérogènes, libellés non normalisés.
3. **Nettoyage & harmonisation** — normalisation des noms de territoires, typage, gestion des valeurs nulles/aberrantes, mise au format « long ».
4. **Catalogue** (`construire_catalogue.py`, `construire_dim_indicateur_et_faits.py`) — chaque source devient une table de faits rattachée à un thème, reliée à `dim_territoire` via `territoire_id`, et référencée dans `dim_indicateur`.
5. **Chargement** (`charger_postgres.py`) — création de la base `dwh_orvsit`, d'un schéma par thème + `referential`, et chargement des dimensions et des faits (avec index et clés étrangères sur `territoire_id`).

## Modèle de données

### Entrepôt `dwh_orvsit` (approche catalogue par thème)

- **`referential.dim_territoire`** — hiérarchie territoriale complète : région → préfecture/province (8) → cercle (24) → commune (146) / centre urbain → douar (≈ 3 000).
- **`referential.dim_indicateur`** — catalogue des indicateurs (≈ 390) : nom, thème, table de faits, colonne de valeur, unité.
- **`referential.dim_etablissement_scolaire`** — dimension des établissements scolaires.
- **`<theme>.<table>`** — une table de faits par source, dans le schéma de son thème (`demography`, `education`, `health`, `infrastructure`, `climate`, `socio_economic`), reliée à `dim_territoire`.

Couverture par niveau : les 6 thèmes sont disponibles au niveau **province/préfecture** ; démographie, socio-économique et éducation descendent jusqu'à la **commune** (santé, infrastructure et climat restent au niveau province).

### Base applicative `orvsit_app`

| Table | Rôle |
|-------|------|
| `utilisateur` | comptes (analyste, décideur, administrateur, partenaire, chercheur) |
| `demande_acces` | demandes reçues via la landing page, validées par l'admin |
| `conversation` / `message` | historique de l'assistant IA |
| `message_reference` | territoires/indicateurs cités par une réponse IA (référence logique vers le DWH) |
| `message_feedback` | retour utilisateur sur les réponses |
| `journal_usage` | trace des actions pour la supervision de l'usage |

DDL complet : [`database/orvsit_app_schema.sql`](database/orvsit_app_schema.sql).

## Indices synthétiques

L'**Indice de Développement Territorial (IDT)** et l'**indice de vulnérabilité** ne sont pas stockés bruts : ils se **calculent** à partir des indicateurs (normalisation min-max des indicateurs par axe, puis agrégation/moyenne pondérée). Ils sont recalculés à chaque mise à jour des données.

## Installation & exécution

### Prérequis

- Python 3.10+
- Node.js 18+
- PostgreSQL 13+

### 1. Configuration

```bash
cp .env.example .env      # puis renseigner vos identifiants PostgreSQL
```

### 2. Entrepôt de données (dwh_orvsit)

```bash
cd data-pipeline
pip install -r ../backend/requirements.txt   # ou un requirements dédié
python charger_postgres.py                    # crée dwh_orvsit et charge dimensions + faits
```

### 3. Base applicative (orvsit_app)

```bash
python database/init_app_db.py
# ou :  createdb orvsit_app && psql -d orvsit_app -f database/orvsit_app_schema.sql
```

> Après le premier déploiement, remplacez le mot de passe de l'administrateur par défaut.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

## Rôles utilisateurs

- **Analyste / Décideur** — accès aux tableaux de bord : vue d'ensemble, comparaison, fiche territoriale, exploration d'indicateurs, cartographie, assistant IA, export.
- **Administrateur** — en plus : gestion des comptes, validation des demandes d'accès, supervision de l'usage, synchronisation de la base.

## Maquette

Une maquette interactive (HTML) illustre l'interface cible : landing page, authentification, tableaux de bord, assistant IA flottant et espace d'administration. Voir `docs/maquette/ORVSIT_Dashboard.html`.

## Feuille de route

- [x] Collecte, nettoyage et consolidation des données (data warehouse `dwh_orvsit`)
- [x] Modèle de la base applicative `orvsit_app`
- [x] Maquette interactive de l'interface
- [ ] Calcul des indices synthétiques (IDT, vulnérabilité)
- [ ] API backend (authentification, endpoints indicateurs, assistant IA)
- [ ] Développement du frontend React
- [ ] Cartographie SIG (jointure QGIS / GeoJSON)

## Auteur

Projet de Fin d'Année réalisé dans le cadre du stage à l'ORVSIT — Conseil régional de Tanger-Tétouan-Al Hoceïma.
