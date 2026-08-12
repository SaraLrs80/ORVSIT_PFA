# Jeu d'évaluation de l'assistant

Ce dossier contient l'instrument qui mesure l'assistant conversationnel. Il a
été écrit **avant** l'installation du modèle, pour que le choix du modèle soit
tranché par des mesures et non par une impression.

## Ce qu'on note, et ce qu'on ne note pas

On ne note **pas la formulation**. Deux réponses correctes peuvent être écrites
différemment, et juger le style demanderait un lecteur humain à chaque essai.

On note trois choses vérifiables automatiquement :

1. **Le bon outil a-t-il été appelé ?** — colonne `outil_attendu`
2. **La réponse contient-elle ce qu'elle doit contenir ?** — colonne `doit_contenir`
3. **Rien d'inventé ni de confondu ?** — colonne `ne_doit_pas_contenir`

Le troisième critère est le plus important. Un assistant qui répond « je ne sais
pas » à une question difficile reste utilisable ; un assistant qui avance un taux
de chômage plausible mais faux ne l'est pas.

## Format du fichier `questions.csv`

Séparateur `;`, encodage UTF-8. Une ligne par cas.

| colonne | contenu |
|---|---|
| `id` | identifiant stable, préfixe = famille |
| `famille` | catégorie de test |
| `question` | la question posée, telle qu'un utilisateur l'écrirait |
| `outil_attendu` | outil qui devrait être appelé ; vide si aucun appel n'est légitime |
| `doit_contenir` | chaînes attendues dans la réponse, alternatives séparées par `\|` |
| `ne_doit_pas_contenir` | chaînes dont la présence signale une erreur |
| `commentaire` | pourquoi ce cas figure au jeu |

Une alternative est satisfaite dès qu'**une** des chaînes séparées par `|` est
présente. Cela laisse au modèle sa liberté de formulation tout en contrôlant le
fond.

## Les dix familles

| famille | ce qu'elle éprouve |
|---|---|
| `valeur` | lecture d'une valeur exacte, mise en forme des nombres |
| `ambigu` | cinq noms désignent à la fois une province et une commune : l'assistant doit **demander**, jamais choisir |
| `orthographe` | tolérance aux noms mal écrits, sans invention |
| `hors_niveau` | l'indicateur n'est pas publié à cette échelle : il faut le dire, pas répondre zéro |
| `zero` | un vrai zéro est une information : il ne doit pas devenir « non renseigné » |
| `classement` | ordre correct selon le sens de l'indicateur ; un dénombrement n'a pas de sens favorable |
| `comparaison` | comparaison entre pairs de même niveau, refus sinon |
| `couverture` | ce qui existe, avant de demander une valeur qui n'existe pas |
| `definition` | définition et traçabilité, y compris les mises en garde |
| `impossible` | **un quart du jeu** : hors périmètre, donnée absente, projection, calcul composite |

## Pourquoi la famille `impossible` pèse un quart

C'est la seule qui éprouve ce qui sera demandé en soutenance : que se passe-t-il
quand on pose une question à laquelle l'assistant ne peut pas répondre ? La règle
retenue est le **refus motivé** — dire que la donnée n'existe pas dans la base,
qu'elle n'est pas publiée à ce niveau, ou que la question demande un calcul que
la plateforme ne fait pas. Un refus sans motif effacerait précisément la
distinction entre les trois absences que tout le traitement des données cherche à
préserver.

## Provenance des valeurs attendues

Chaque valeur inscrite en colonne `doit_contenir` a été relue dans les fichiers
de faits du dossier `data-pipeline/`, jamais recopiée de mémoire. Quelques
exemples et leur raison d'être :

- **Chefchaouen** : 12,38 % de pauvreté en province, 2,53 % en commune. Un facteur
  cinq entre deux territoires de même nom — c'est ce qui justifie que l'assistant
  refuse de trancher seul.
- **Unité UMP** : cinq établissements en province de Chefchaouen, zéro dans la
  commune d'Abdelghaya Souahel, un à Bab Berred. Le zéro est réel, il vient d'un
  registre exhaustif, et il ne doit pas être présenté comme une absence de donnée.
- **Santé au niveau communal** : sept indicateurs seulement. C'est la mesure de la
  profondeur territoriale réelle, et elle explique pourquoi une famille de
  questions entière porte sur la couverture.
