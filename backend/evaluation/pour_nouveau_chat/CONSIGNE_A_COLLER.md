# À coller dans le nouveau chat

Colle le texte ci-dessous, et joins les deux fichiers `territoires.csv` et
`indicateurs.csv` du même dossier.

**Ne joins rien d'autre.** Ni le code, ni le moteur, ni les questions déjà
écrites. C'est tout l'intérêt de la manœuvre : des questions écrites en
connaissant les données, mais pas la solution.

---

## Le texte

> Je construis un jeu de questions pour évaluer un assistant conversationnel
> qui répond sur des données territoriales officielles de la région
> Tanger-Tétouan-Al Hoceïma, au Maroc.
>
> Je te donne deux fichiers :
>
> - `territoires.csv` — les 154 territoires servis : 8 préfectures et
>   provinces, 146 communes.
> - `indicateurs.csv` — les 105 familles d'indicateurs disponibles, avec leur
>   unité, leur millésime, et les niveaux territoriaux où chacune est publiée.
>
> **Ce que fait la plateforme :** elle restitue des valeurs officielles déjà
> publiées, telles quelles. Elle ne calcule rien, ne projette rien, ne note
> rien, ne classe pas les territoires selon un score global.
>
> **Trois règles de fond, qui gouvernent ce qu'elle peut répondre :**
>
> 1. Une donnée peut manquer pour trois raisons différentes, et il ne faut
>    jamais les confondre : elle n'est pas publiée à ce niveau territorial ;
>    elle est publiée mais absente pour ce territoire ; ou sa valeur est
>    réellement zéro, ce qui est une information.
> 2. Aucun calcul n'est permis : pas de moyenne pondérée, pas d'indice
>    composite, pas de projection, pas de jugement du type « le meilleur
>    territoire ».
> 3. Une comparaison ne se fait qu'entre territoires de même niveau. Comparer
>    une commune à une province mesurerait une différence de taille, pas une
>    disparité.
>
> **Un piège important à exploiter :** cinq noms désignent à la fois une
> province et une commune — Al Hoceïma, Chefchaouen, Larache, Ouezzane,
> Tétouan. L'écart peut être considérable : la province de Chefchaouen affiche
> 12,4 % de pauvreté, la commune du même nom 2,5 %.
>
> **Ce que je te demande.** Écris-moi **300 questions** telles que de vrais
> utilisateurs les poseraient : agents du Conseil régional, chargés d'études,
> journalistes, étudiants, élus. Certains sont pressés, certains écrivent mal,
> certains ne connaissent rien aux statistiques.
>
> Répartis-les ainsi :
>
> | part | type de question |
> |---|---|
> | 25 % | une valeur précise pour un territoire précis |
> | 15 % | questions impossibles : donnée absente, hors région, projection, calcul demandé |
> | 10 % | territoires ambigus, sans préciser le niveau |
> | 10 % | langage familier, fautes d'orthographe, phrases sans ponctuation |
> | 10 % | classements et superlatifs |
> | 10 % | comparaisons entre territoires |
> | 8 %  | « qu'est-ce que tu as sur… », questions de couverture |
> | 7 %  | définitions et sources |
> | 5 %  | conversation : bonjour, merci, qui es-tu, es-tu sûr |
>
> **Format.** Un fichier CSV, séparateur point-virgule, encodage UTF-8, avec
> exactement ces colonnes :
>
> ```
> id;famille;question;comportement_attendu;commentaire
> ```
>
> - `id` : un identifiant court et unique
> - `famille` : une seule catégorie parmi celles du tableau ci-dessus
> - `question` : la question telle qu'elle serait tapée, fautes comprises
> - `comportement_attendu` : en français, en une phrase, ce que l'assistant
>   devrait faire — répondre une valeur, refuser en expliquant pourquoi,
>   demander une précision, lister ce qui existe…
> - `commentaire` : pourquoi cette question mérite d'être dans le jeu
>
> **Trois exigences :**
>
> 1. Chaque question qui attend une valeur doit porter sur un indicateur et un
>    territoire qui **existent réellement** dans les fichiers joints.
> 2. Chaque question impossible doit l'être pour une raison **précise et
>    identifiable** — pas seulement « ça n'existe pas ».
> 3. Ne te répète pas : varie les formulations, les tons, les longueurs. Une
>    question posée en cinq mots et la même en trois lignes sont deux cas
>    différents.

---

## Ce qu'il ne faut surtout PAS lui dire

- que l'assistant fonctionne avec un modèle local
- qu'il y a une recherche par mots-clés, des « gardiens », un « moteur »
- comment les questions sont ensuite notées

S'il connaît la mécanique, il écrira des questions taillées pour la réussir.
On veut l'inverse : des questions écrites depuis le besoin, qu'on confrontera
ensuite à ce qu'on a construit.

## Ce qu'on fera de son fichier

Il rend la question, sa famille et le comportement attendu **en français**.
C'est ici, dans le chat du projet, qu'on traduira en colonnes techniques —
`branche_attendue`, `outil_attendu`, `indicateur_attendu` — pour que la
notation devienne automatique. L'indépendance de l'examen est ainsi préservée
sans rien perdre en rigueur.
