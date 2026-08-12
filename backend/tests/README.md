# Tests unitaires de l'assistant

```
cd backend
python -m unittest discover -s tests -t .
```

Aucune base, aucun serveur, aucun modèle : les fonctions éprouvées sont pures,
et celles qui lisent le catalogue passent par le faux entrepôt, qui substitue
les fichiers CSV de `data-pipeline` aux requêtes SQL. Les 46 tests s'exécutent
en moins d'une seconde.

## Ce qui est testé, et pourquoi ce choix

Ces tests ne cherchent pas la couverture. Ils portent sur les quatre fonctions
qui décident de la justesse d'une réponse, et sur elles seules.

| Fichier | Fonction éprouvée | Ce qu'une régression y coûterait |
|---|---|---|
| `test_verification.py` | `_verifier` | un chiffre inventé affiché avec une source officielle |
| `test_gardiens.py` | `garde_temps`, `garde_intention` | une projection ou un calcul présenté comme une donnée publiée |
| `test_intention.py` | `intention` | la mauvaise réponse à la bonne question |
| `test_recherche.py` | `_racine`, `chercher`, `_membre_demande` | une valeur exacte prise au mauvais indicateur |
| `test_definitions.py` | `_definition_redigee` | un nom de colonne servi en guise d'explication |

## Leur place à côté du jeu d'évaluation

Les 270 questions de `evaluer.py` mesurent la chaîne complète : elles notent la
branche empruntée par chaque question. Quand une réponse est fausse, elles ne
disent pas laquelle des quatre couches a échoué.

Ces tests isolent chaque couche. Les deux mesures sont complémentaires et ne se
remplacent pas : lancer les deux avant chaque livraison.

## Ce qu'ils ont trouvé

Deux défauts, dès leur première exécution :

- `révélant` échappait à la détection d'interprétation ajoutée, là où
  `révèle` était bien arrêté — l'accent aigu de la seconde syllabe n'était pas
  prévu par l'expression régulière.
- « Comment calcule-t-on le taux d'urbanisation ? » était refusée comme un
  calcul interdit, alors qu'elle interroge la méthode.

La correction du second a d'abord fait chuter le jeu d'évaluation de 80 % à
79 % : élargir la détection au mot « moyenne » écartait « température
moyenne », « humidité relative moyenne », « distance moyenne des logements » —
des NOMS d'indicateurs. Le signal n'est pas le mot mais sa conjonction avec une
portée territoriale au pluriel : « la moyenne des 8 provinces » est un calcul,
« la température moyenne de Larache » est une lecture.
