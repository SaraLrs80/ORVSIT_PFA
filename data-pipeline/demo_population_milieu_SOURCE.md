# Provenance — Population par milieu (urbain / rural)

**Table produite :** `faits/demography/demo_population_milieu.csv`
→ chargée dans PostgreSQL comme `demography.demo_population_milieu`.

## Source
Haut-Commissariat au Plan (HCP) — **RGPH 2024**, « Population légale du Royaume
du Maroc selon les résultats du Recensement Général de la Population et de
l'Habitat de 2024 », répartition par milieu de résidence (urbain / rural).

Cette donnée était **déjà présente** dans l'entrepôt, dans le fichier
`faits/demography/demography_demography_population_population_legale_2025_urba.csv`
(colonne `milieu` : Ensemble / Urbain / Rural). Le présent script en extrait
simplement une table dérivée, propre et déjà filtrée.

## Pourquoi cette table
L'application lisait auparavant l'urbain/rural depuis les indicateurs **santé**
163 / 164 / 165 (« Population totale — Ensemble/Rural/Urbain », issus des
*populations cibles des programmes de santé*). Ces valeurs sous-estiment la
population urbaine (≈ 62 % contre 65,48 % officiels) et ont donc été retirées du
catalogue. La population par milieu provient désormais de la seule source
démographique officielle.

## Contrôle de cohérence (RGPH 2024)
| Niveau | Urbain | Rural | Total | Taux urbanisation |
|---|---|---|---|---|
| **Région TTA** | 2 638 815 | 1 391 407 | 4 030 222 | 65,48 % |
| Tanger-Assilah | 1 402 668 | 91 745 | 1 494 413 | 93,86 % |
| M'diq-Fnideq | 240 745 | 13 319 | 254 064 | 94,76 % |
| Tétouan | 440 054 | 171 874 | 611 928 | 71,91 % |
| Fahs-Anjra | 3 763 | 97 026 | 100 789 | 3,73 % |
| Larache | 275 450 | 234 761 | 510 211 | 53,99 % |
| Al Hoceïma | 138 977 | 232 550 | 371 527 | 37,41 % |
| Chefchaouen | 62 632 | 350 081 | 412 713 | 15,18 % |
| Ouezzane | 74 526 | 200 051 | 274 577 | 27,14 % |

La somme des 8 provinces redonne **exactement** le total régional
(2 638 815 urbain / 1 391 407 rural). Le taux de Chefchaouen (15,18 %) est
identique à celui publié dans la note provinciale HCP du RGPH 2024 —
double validation.

## Indicateurs ajoutés au catalogue (dim_indicateur)
| filtre_indicateur | libellé | unité |
|---|---|---|
| pop_urbain | Population urbaine (RGPH 2024) | hab |
| pop_rural | Population rurale (RGPH 2024) | hab |
| taux_urbanisation | Taux d'urbanisation | % |

Table = `demo_population_milieu`, mode `long`, colonne valeur = `valeur`.
