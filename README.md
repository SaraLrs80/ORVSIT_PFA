# ORVSIT — Plateforme d'intelligence territoriale

Plateforme de mesure et de restitution des disparités territoriales de la
région **Tanger-Tétouan-Al Hoceïma**, réalisée pour l'Observatoire Régional de
Veille Stratégique et d'Intelligence Territoriale (ORVSIT) du Conseil régional.

Elle réunit un entrepôt de données territorial, un tableau de bord de
consultation et un assistant conversationnel fondé sur un modèle de langage
exécuté localement.

**224 indicateurs** servis sur 5 secteurs · **8 préfectures et provinces**,
**146 communes** · 7 organismes producteurs, chaque valeur portant sa source
et son millésime.

---

## La règle qui gouverne le projet

**La plateforme ne produit aucune donnée nouvelle.** Elle restitue des valeurs
déjà publiées, telles qu'elles figurent dans leur source : aucune moyenne
pondérée, aucun indice composite, aucune projection.

Cette règle explique plusieurs choix qui pourraient surprendre. En
particulier, l'assistant conversationnel ne laisse pas le modèle de langage
choisir un indicateur, lire la base ou composer un chiffre : ces décisions
sont prises par du code déterministe, et le modèle n'intervient qu'en dernier,
pour mettre en français une réponse déjà rédigée et exacte.

---

## Démarrage

### Prérequis

| | Version | Pourquoi |
|---|---|---|
| Python | 3.10 ou plus | pipeline de données et API |
| Node.js | 18 ou plus | interface web |
| PostgreSQL | 13 ou plus | entrepôt et base applicative |
| Ollama | facultatif | assistant conversationnel (modèle local) |

Sans Ollama, tout fonctionne sauf la mise en forme des réponses de
l'assistant : celui-ci sert alors ses réponses telles que le code les compose,
sans reformulation.

### 1. Configuration

```bash
cp .env.example .env
```

Renseigner les identifiants PostgreSQL, puis engendrer une clé de signature
pour les jetons :

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Reporter le résultat dans `JWT_SECRET`.

### 2. Bases de données

```bash
# Base applicative : comptes, demandes d'accès, conversations, journal
python database/init_app_db.py

# Entrepôt territorial : référentiel, catalogue et tables de faits
cd data-pipeline
python charger_postgres.py
```

Le chargement lit les fichiers préparés du dossier `data-pipeline/` et écrit
dans `dwh_orvsit`. Les sources brutes (classeurs Excel) ne sont pas versionnées.

### 3. API

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux et macOS
pip install -r requirements.txt

python creer_admin.py          # crée le premier compte administrateur
uvicorn app.main:app --reload
```

L'API écoute sur `http://localhost:8000`. Sa documentation interactive est à
`http://localhost:8000/docs`.

### 4. Interface

```bash
cd frontend
npm install
npm run dev
```

L'interface est servie sur `http://localhost:5173`.

### 5. Assistant conversationnel (facultatif)

```bash
ollama pull qwen2.5:3b
ollama serve
```

Le modèle de 3 milliards de paramètres est celui retenu : mesuré deux fois et
demie plus rapide que celui de 7 milliards, et plus fiable sur cette tâche.

---

## Vérifier que tout fonctionne

```bash
cd backend

# 48 tests unitaires sur la couche déterministe de l'assistant
python -m unittest discover -s tests -t .

# 300 questions rejouées sans base de données ni modèle
python evaluer.py --hors-ligne
```

Les deux campagnes s'exécutent hors ligne, sans PostgreSQL ni Ollama : un
entrepôt de substitution remplace les requêtes par la lecture des fichiers
préparés. La première prend moins d'une seconde, la seconde une minute.

Résultats attendus : 48 tests au vert, et 80 % de réussite stricte / 97 % de
réussite acceptable sur le jeu de questions.

---

## Organisation du dépôt

```
PROJET_PFA/
├── data-pipeline/       préparation des données et chargement de l'entrepôt
│   ├── construire_catalogue.py     construction du catalogue d'indicateurs
│   ├── charger_postgres.py         chargement dans PostgreSQL
│   ├── verifier_migration.py       contrôle du sens des indicateurs
│   ├── dim_territoire.csv          référentiel territorial unifié
│   ├── dim_indicateur.csv          catalogue des indicateurs
│   └── faits/                      tables de faits, rangées par thème
│
├── database/            base applicative
│   ├── orvsit_app_schema.sql
│   └── init_app_db.py
│
├── backend/             API FastAPI
│   ├── app/routers/     11 modules, 31 routes
│   ├── app/assistant/   moteur, gardiens, recherche, outils
│   ├── tests/           48 tests unitaires
│   ├── evaluation/      jeu de 300 questions et entrepôt de substitution
│   └── essais/          scripts de mesure (débit des modèles, recherche…)
│
├── frontend/            interface React et Vite
│   └── src/pages/       vue d'ensemble, fiche, comparer, explorer, assistant
│

```

---

## Deux bases distinctes

**`dwh_orvsit`** — l'entrepôt analytique, en lecture seule pour l'application.
Modélisé en schéma en étoile : les dimensions dans le schéma `referential`
(`dim_territoire`, `dim_indicateur`, `dim_etablissement_scolaire`), et une
table de faits par source, rangée dans le schéma de son thème (`demography`,
`education`, `health`, `infrastructure`, `climate`, `socio_economic`).

**`orvsit_app`** — les données applicatives : `utilisateur`, `demande_acces`,
`conversation`, `message`, `message_reference`, `message_feedback`,
`journal_usage`.

Les deux bases sont séparées : l'application ne peut pas modifier l'entrepôt.

---

## Le catalogue gouverne l'application

`referential.dim_indicateur` décrit chaque indicateur — son libellé, son
unité, sa source, son millésime, sa table de faits, ses échelles de
publication, ses mots-clés et sa définition.

L'application ne code en dur aucun nom d'indicateur. Les routes lisent le
catalogue, en déduisent quelles tables interroger, quelle forme graphique
convient et quel libellé afficher. **Ajouter un indicateur au catalogue suffit
à le faire apparaître dans l'interface, sans modification du code.**

---

## Sources des données

Haut-Commissariat au Plan (RGPH 2024, cartographie de la pauvreté
multidimensionnelle, base de la migration interne, Annuaire Statistique du
Maroc) · Ministère de la Santé et de la Protection Sociale (Carte Sanitaire) ·
Ministère de l'Éducation Nationale (annuaire des établissements scolaires) ·
Portail national des données ouvertes.

Chaque indicateur porte sa source et son millésime dans le catalogue, et les
deux sont affichés à côté de chaque valeur dans l'interface.

---

## Auteure

Laaroussi Sara — Projet de Fin d'Année, filière Génie Informatique,
École Nationale des Sciences Appliquées de Tanger, Université Abdelmalek
Essaâdi, 2025-2026.

Encadrante : Mme Rajae ELBOUHALI, Conseil de la Région
Tanger-Tétouan-Al Hoceïma, Direction de la planification et du développement
régional.
