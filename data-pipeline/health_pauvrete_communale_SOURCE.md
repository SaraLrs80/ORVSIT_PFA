# Source — faits/health/health_pauvrete_communale.csv

## Origine
Extrait de `hcp_pauvrete_communale_TTA.csv` (déjà en base, thème socio_economic),
lui-même issu de « La base de données (Excel) de la Cartographie de la pauvreté
multidimensionnelle... Mai 2025 » (HCP), filtré région TTA, niveau commune, 2024.

**Aucun calcul de notre part** : les 3 colonnes sont reprises telles quelles.

## Colonnes reprises
- `priv_mortalite_infantile` — taux de privation lié à la mortalité infantile
  (une des composantes officielles de la dimension « Santé » de l'indice de
  pauvreté multidimensionnelle HCP/Alkire-Foster).
- `priv_handicap` — taux de privation lié au handicap (seconde composante
  officielle de la dimension « Santé » du même indice).
- `contrib_sante` — contribution (%) de la dimension santé à l'indice de
  pauvreté multidimensionnelle (MPI) de la commune.

## Jointure territoire_id
Faite par `code` (HCP) == `code_hcp` (dim_territoire), PAS par nom — évite
tout risque d'erreur d'orthographe. 146/146 communes du référentiel appariées
exactement.

Point de vigilance résolu : Tanger est découpée en 4 arrondissements dans le
fichier HCP (niveau= »commune » : Bni Makada, Mghogha, Souani, Médina) qui
n'ont pas de territoire_id propre (le référentiel n'a qu'une seule « Commune
de Tanger », id 34). Ces 4 lignes-arrondissement ne sont PAS utilisées :
le fichier HCP contient aussi une ligne agrégée officielle pour Tanger entière,
étiquetée niveau= »préfecture d'arrondissement » (code 1511010, correspond
exactement à code_hcp de la Commune de Tanger, id 34) — c'est cette ligne
officielle qui est utilisée, sans aucune agrégation calculée par nous.

## Unité
Non confirmée dans la documentation HCP disponible à ce jour (probable %,
cohérent avec la méthodologie Alkire-Foster). À vérifier par l'utilisatrice
dans le fichier Excel source si une confirmation exacte est nécessaire.
