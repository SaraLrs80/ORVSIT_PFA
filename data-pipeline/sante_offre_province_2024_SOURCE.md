# Source — sante_offre_province_2024.csv

## Origine
Fichier `Indicateurs_officiels_TTA_2024.xlsx`, feuille « Indicateurs officiels 2024 »,
fourni par l'utilisatrice dans le dossier `Santé_2025`.

**Aucun calcul de notre part** : les 20 ratios sont extraits tels quels du
Tableau de Bord Interactif (TBI) de la Carte Sanitaire du Ministère de la
Santé et de la Protection Sociale. Voir la feuille « Source & lecture » du
fichier original.

- Source : Carte Sanitaire — Ministère de la Santé et de la Protection Sociale.
  cartesanitaire.sante.gov.ma/dashboard/pages2/indicateur_2025.html
- Périmètre : région Tanger-Tétouan-Al Hoceïma, niveau provinces sanitaires,
  période 2024.
- Population de référence : RGPH 2024 (HCP), projection utilisée par le site.

## Remplace
Les 7 anciens indicateurs `health_capacite_province` (ids 395-401 : nb_essp,
nb_hopitaux, nb_medecins_public, nb_paramedical_public + 3 taux per-capita
« secteur public seul »), retirés du catalogue car méthodologiquement
défaillants : ils ne comptaient que le secteur public et créaient un biais
« per-capita » favorisant les petites provinces rurales à nombreux petits
dispensaires (ESSP), masquant la concentration réelle de l'offre spécialisée
(CHU, cliniques privées) à Tanger-Assilah.

## Lecture
Chaque colonne = nombre d'habitants pour 1 unité d'offre (médecin, lit, ESSP,
officine...). **Plus la valeur est élevée, plus l'accès est faible** (sens
négatif : -1 dans la normalisation IDT).

Cellule vide = structure absente ou non renseignée dans cette province
(ex. aucun scanner public à Tétouan/Fahs-Anjra ; aucun lit hospitalier
recensé à Fahs-Anjra qui n'a pas d'hôpital).

## Non dupliqué
La population (totale/urbaine/rurale) présente dans le fichier original
n'a pas été reprise ici : elle existe déjà, vérifiée, dans
`demography.demo_population_milieu` (RGPH 2024, 65.48% urbanisation région).

## Périmètre de correction
Cette correction porte uniquement sur les indicateurs d'**offre de soins**
(offre/capacité : médecins, lits, ESSP, infirmiers, dentistes, pharmacies,
scanner). Les indicateurs de **demande/couverture et résultats** (consultations,
accouchements, vaccination, contraception, occupation des lits, maladies sous
surveillance — 60 indicateurs déjà catalogués sous health_sante_16 à 27)
ne sont pas concernés : l'utilisatrice a confirmé qu'ils sont fiables et déjà
correctement en base.
