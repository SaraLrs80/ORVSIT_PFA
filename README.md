# ORVSIT — Observatoire des disparités territoriales (région TTA)

Projet de Fin d'Année (PFA) réalisé pour l'**Observatoire Régional de Veille Stratégique et d'Intelligence Territoriale (ORVSIT)** du Conseil régional de Tanger-Tétouan-Al Hoceïma.

L'objectif est de **mesurer, comparer et visualiser les disparités territoriales** de la région TTA (démographie, social, équipements, mobilité, économie, environnement) à partir d'un entrepôt de données territoriales, afin d'aider la décision publique.

## Origine des données

La **collecte et la consolidation initiale** de la base de données territoriale ont été réalisées dans le cadre d'un **projet de fin d'études (PFE) par deux étudiantes**. Le présent projet **reprend cette base** et l'**enrichit** de quelques indicateurs et sources complémentaires trouvés en plus.

Sources : HCP, RGPH 2024, départements ministériels sectoriels, Open Data Maroc, documents régionaux (SRAT, PDR).

## Architecture

Deux bases PostgreSQL distinctes :

- **`dwh_orvsit`** — l'entrepôt analytique (données territoriales TTA), en lecture seule pour l'application.
- **`orvsit_app`** — les données applicatives : comptes utilisateurs, demandes d'accès, assistant IA, journal d'usage.

Un backend (Python) expose les données à un frontend (React / Vite).

## Structure du dépôt

```
PROJET_PFA/
├── data-pipeline/          # partie Data (nettoyage, catalogue, chargement du DWH)
│   ├── charger_postgres.py
│   ├── construire_catalogue.py
│   ├── dim_territoire.csv / dim_indicateur.csv / dim_etablissement_scolaire.csv
│   ├── faits/              # tables de faits nettoyées, par thème
│   └── data/               # sources brutes (Excel) — NON versionné
├── database/               # base applicative
│   ├── orvsit_app_schema.sql
│   └── init_app_db.py
├── backend/                # API (à développer)
└── frontend/               # interface React / Vite
```

## Modèle de données

**`dwh_orvsit`** — dimensions dans le schéma `referential` (`dim_territoire` : région → province/préfecture → cercle → commune → douar ; `dim_indicateur` ; `dim_etablissement_scolaire`) et une table de faits par source, rangée dans le schéma de son thème (`demography`, `education`, `health`, `infrastructure`, `climate`, `socio_economic`).

**`orvsit_app`** — `utilisateur`, `demande_acces`, `conversation` / `message` (assistant IA), `message_reference`, `message_feedback`, `journal_usage`. DDL : [`database/orvsit_app_schema.sql`](database/orvsit_app_schema.sql).

## Installation

Prérequis : Python 3.10+, Node.js 18+, PostgreSQL 13+.

```bash
cp .env.example .env                     # renseigner les identifiants PostgreSQL

# Entrepôt de données
cd data-pipeline && python charger_postgres.py

# Base applicative
python database/init_app_db.py

# Frontend
cd frontend && npm install && npm run dev
```

## Rôles

- **Analyste / Décideur** — tableaux de bord : vue d'ensemble, comparaison, fiche territoriale, exploration d'indicateurs, cartographie, assistant IA.
- **Administrateur** — en plus : gestion des comptes, validation des demandes d'accès, supervision de l'usage, synchronisation de la base.

## Feuille de route

- [x] Base de données territoriale consolidée (`dwh_orvsit`)
- [x] Modèle de la base applicative (`orvsit_app`)
- [ ] Calcul des indices synthétiques (développement, vulnérabilité)
- [ ] API backend (authentification, indicateurs, assistant IA)
- [ ] Frontend React
- [ ] Cartographie SIG
