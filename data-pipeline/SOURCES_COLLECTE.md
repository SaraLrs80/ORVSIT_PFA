# Feuille de route — Collecte de données ORVSIT (définitive)

Objectif : lister **exactement** les sources officielles restantes, ciblées sur
tes manques réels, pour clôturer la collecte sans re-chercher à chaque fois.

---

## 1. État des lieux de ta base (vérifié)

**Niveau province (8/8)** — complet et fiable sur tous les thèmes utiles :
éducation, démographie, santé (capacités), infrastructure (routes), socio-économique
(emploi, numérique, habitat), climat.

**Niveau commune** (146 communes dans `dim_territoire`) :

| Thème | Commune ? | Détail |
|---|---|---|
| Démographie | ✅ | 54 indicateurs, jusqu'à 146 communes |
| Éducation | ✅ | 17 indicateurs, 146 communes |
| Socio-économique | ✅ | 46 indicateurs, 146 communes (emploi, habitat, numérique) |
| **Santé** | ❌ | **0 au niveau commune** → manque |
| **Infrastructure / routes** | ❌ | **0 au niveau commune** → manque |
| Climat | ❌ | régional seulement (non bloquant) |

➡️ **Tes deux seuls vrais trous : santé et infrastructure au niveau commune.**

---

## 2. Sources prioritaires pour combler les manques

### 🥇 A. HCP — Cartographie de la pauvreté multidimensionnelle communale (Mai 2025)
**LA source à récupérer en premier.** Base Excel **par commune**, mêmes 3
dimensions que ton IDT (éducation, santé, conditions de vie), pondération **égale**,
seuil 33 %. Te donne (a) une **référence communale prête** pour valider/comparer
ton IDT, (b) le déficit par dimension pour chaque commune.

- Base de données Excel (commune) : https://www.hcp.ma/file/245096/
- Rapport intégral (PDF) : https://www.hcp.ma/file/244249/
- Page de présentation : https://www.hcp.ma/Synthese-Cartographie-de-la-pauvrete-multidimensionnelle-paysage-territorial-et-dynamique-Mai-2025_a4103.html
- Format : `.xlsx` — **téléchargement direct, exploitable immédiatement**.

### 🥈 B. Ministère de la Santé — Carte Sanitaire
Comble le trou **santé au niveau commune** : établissements de soins (ESSP,
hôpitaux) **géolocalisés, par commune**, secteur public et privé.

- Tableau de bord : http://cartesanitaire.sante.gov.ma/dashboard/pages2/index.html
- Établissements géolocalisés : http://cartesanitaire.sante.gov.ma/dashboard/pages2/etab_geoloc.html
- Liste par commune : http://cartesanitaire.sante.gov.ma/dashboard/pages2/ds_com.html
- ⚠️ C'est un **tableau de bord JavaScript** : les données ne se téléchargent pas
  directement en CSV. Extraction possible via le navigateur (ou via son point de
  données interne). → je peux te l'extraire proprement si tu veux.

### 🥉 C. data.gov.ma (Agence de Développement du Numérique)
~400 jeux de données, 300+ en CSV/Excel. Utile pour **infrastructure/transport**
et fonds de carte communes.

- Portail : https://data.gov.ma
- Contient : localisation des gares/points de transport, limites des communes
  (GeoJSON/Shapefile), jeux santé/éducation/transport.

### D. RGPH 2024 — application de résultats + open data HCP
Pour **compléter/valider** le niveau commune (population, conditions d'habitation :
eau, électricité, assainissement ; scolarisation ; activité/chômage).

- Résultats RGPH 2024 : https://resultats2024.rgphapps.ma
- Micro-données / open data HCP : https://www.hcp.ma/Micro-donnees-Open-data_r632.html
- Base de données statistiques régionale (TTA) : http://bds-tanger.hcp.ma

### E. PRDTS — Programme de Réduction des Disparités Territoriales et Sociales
Programme (2017-2023) ciblant **1 253 communes rurales** : routes/pistes, eau,
électricité, écoles, santé. Données d'accès aux services **au niveau commune rurale**
— très aligné sur l'enclavement. Publié via le Ministère de l'Intérieur ; données
souvent dans des rapports (à demander/extraire).

### F. Monographies régionale et provinciales — HCP DR Tanger
Indicateurs consolidés par province/préfecture (utile pour recouper).

- Monographies : https://www.hcp.ma/region-tanger/Monographies_r18.html

---

## 3. Compléments par thème (si besoin)

| Besoin | Source officielle |
|---|---|
| Réseaux eau / électricité (desserte) | ONEE — www.onee.ma |
| Numérique / couverture télécom | ANRT — www.anrt.ma (tu as déjà internet/ordinateur via RGPH) |
| Santé — effectifs & capacités (province) | « Santé en chiffres » (déjà utilisé) |
| Fonds de carte communal (cartographie) | data.gov.ma / geoBoundaries (niveau 3) |

---

## 4. Recommandation de granularité

La santé et les routes ne sont **pas publiées commune par commune** dans les
statistiques primaires (elles le sont au niveau province). Donc pour un IDT
**communal** fiable, la voie pragmatique est :

1. Récupérer la **base Excel de la cartographie de pauvreté HCP** (A) → référence
   communale multidimensionnelle prête.
2. Ajouter la **Carte Sanitaire** (B) pour la desserte santé communale.
3. Compléter routes/accès via **PRDTS** (E) et data.gov.ma (C).

Sinon, garder l'IDT au **niveau province** (fiable, complet) et présenter le
communal comme **perspective**, appuyée sur la cartographie HCP.

---

*Sources vérifiées le 22/07/2026. Liens directs testés (sauf tableaux de bord JS).*
