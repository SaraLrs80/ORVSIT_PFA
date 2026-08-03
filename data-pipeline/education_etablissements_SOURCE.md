# Source — établissements scolaires

## Le problème constaté

La fiche affichait **136** écoles primaires pour Al Hoceïma, alors que la
publication officielle du HCP (« Al Hoceima en chiffres 2024 ») annonce **162**.
Vérification faite, l'écart touchait les trois cycles :

| Cycle | Base ORVSIT | HCP « en chiffres » |
|---|---|---|
| Primaire | 136 | 162 |
| Collégial | 38 | 42 |
| Qualifiant | 27 | 28 |

## Diagnostic

Ce n'était **pas** une erreur de traitement : la liste nominative contenait bien
136 écoles primaires distinctes à Al Hoceïma, sans doublon, avec les 36 communes
correctement rattachées.

Deux causes cumulées, toutes deux vérifiées :

1. **Périmètre** — la source ne couvre que le secteur **public**.
2. **Ancienneté** — le jeu de données a été créé le 15/05/2014 et modifié pour la
   dernière fois le 13/12/2021, soit au moins trois rentrées scolaires de retard
   sur l'Annuaire 2023-2024.

L'arithmétique le confirme exactement, à l'unité près, pour les trois cycles :

| Cycle | Public (Annuaire) | Privé (Annuaire) | Total | HCP « en chiffres » |
|---|---|---|---|---|
| Primaire | 151 | 11 | **162** | 162 |
| Collégial | 38 | 4 | **42** | 42 |
| Qualifiant | 27 | 1 | **28** | 28 |

Le chiffre du HCP correspond donc à **public + privé**. Notre ancienne source
donnait du **public seul, d'avant 2022** — d'où le double écart.

L'Annuaire révèle par ailleurs une distinction absente de notre source : les
**satellites** (unités scolaires rattachées à une école principale, très
fréquentes en milieu rural). Al Hoceïma en compte 327 pour 151 établissements.

## Les deux sources, désormais distinctes

### 1. `faits/education/education_etablissements_officiel.csv` — niveau province

- **Source** : Annuaire Statistique du Maroc 2024 (HCP), Chapitre XI —
  tableaux 11-5, 11-15, 11-17, 11-24, 11-26, 11-32.
- **URL** : https://www.hcp.ma/file/248150/
- **Année scolaire** : 2023-2024.
- **Couverture** : région + 8 provinces. **L'Annuaire ne descend pas à la commune.**
- **Contenu** : public, privé, total et satellites, pour les trois cycles.
- Les colonnes `_total` sont des sommes de deux comptages officiels
  (public + privé), la seule opération effectuée.

### 2. Annuaire nominatif MENPS — niveau commune

- **Source** : Portail Open Data data.gov.ma — MENPS,
  « Liste des établissements scolaires publics ».
- **URL** : https://data.gov.ma/data/fr/dataset/listes-des-etablissements-scolaires-publics
- **Dates** : créé 15/05/2014, dernière modification 13/12/2021.
- **Périmètre** : secteur **public uniquement**.
- **Contenu** : 1 273 établissements nommés avec adresse, commune et cycle.
- C'est la **seule source descendant au niveau commune**, d'où sa conservation.

## Règle d'usage — importante

Les deux sources ne mesurent pas la même chose. En conséquence :

- **La somme des communes ne reconstitue pas le total provincial**, et c'est normal.
- Les deux chiffres ne sont **jamais additionnés ni comparés** dans l'application.
- Chaque valeur est renvoyée par l'API avec un champ `source` affiché à côté,
  pour que le lecteur sache toujours ce qu'il regarde.
- Au niveau commune, l'annuaire nominatif reste pleinement valable pour ce à quoi
  il sert vraiment : la cartographie, la présence/absence d'école par commune et
  le détail des établissements. C'est le **comptage absolu** qui ne doit pas être
  opposé au chiffre officiel.

## Ce qui reste à faire

- Le niveau commune restera daté tant que le MENPS ne publiera pas de liste
  actualisée. À défaut, une demande directe auprès de l'AREF Tanger-Tétouan-Al
  Hoceïma permettrait d'obtenir la répartition communale à jour.
- Les écoles de la commune de Tanger sont réparties dans les arrondissements de
  la source communale et restent à rattacher (comptage actuel : 0).
