"""
Chapitre 5 — Tests et validation.

TOUS LES CHIFFRES SONT MESURÉS
Aucune valeur de ce chapitre n'est estimée. Les décomptes de tests viennent
de `python -m unittest discover`, les scores de `python evaluer.py
--hors-ligne`, les concordances de `verifier_migration.py`, les cas d'API de
la série de captures. Un chapitre de tests qui arrondirait ses propres
mesures se disqualifierait.

RÈGLE D'ÉCRITURE
Comme le reste du rapport : on décrit le dispositif livré et on justifie ses
choix. Les deux défauts trouvés par les tests unitaires sont rapportés, parce
qu'un dispositif de test se juge à ce qu'il attrape — mais ils le sont comme
un résultat de campagne, pas comme un récit.
"""

import os

import edition as E


# --------------------------------------------------------------------------
# 5.1 — la stratégie
# --------------------------------------------------------------------------
NIVEAUX = [
    ("Validation des données", "entrepôt",
     "chaque valeur écrite correspond-elle à son fichier d'origine, et "
     "l'indicateur mesure-t-il ce que son libellé annonce ?", "automatisé"),
    ("Tests unitaires", "couche déterministe",
     "chaque fonction de décision rend-elle le verdict attendu, isolément ?",
     "automatisé"),
    ("Tests d'intégration", "interface de programmation",
     "chaque route répond-elle correctement, y compris aux cas d'erreur et "
     "aux tentatives d'accès non autorisées ?", "manuel"),
    ("Évaluation fonctionnelle", "assistant complet",
     "sur un jeu de questions représentatif, la question est-elle aiguillée "
     "vers le bon traitement ?", "automatisé"),
    ("Non-régression", "assistant complet",
     "une correction en casse-t-elle une autre ?", "automatisé"),
    ("Performance", "modèle local",
     "le temps de réponse est-il compatible avec un usage interactif ?",
     "automatisé"),
]


def section_strategie():
    p = [E.titre("5.1 Stratégie de test", 2)]
    p.append(E.para(
        "La plateforme réunit trois natures de risque, et chacune appelle un "
        "dispositif propre. Le premier risque porte sur la donnée : une valeur "
        "peut être transférée fidèlement depuis une colonne erronée, et aucun "
        "message d'erreur ne le signalera. Le deuxième porte sur la couche "
        "applicative : une route mal protégée expose des données, une route "
        "mal codée renvoie une erreur serveur là où un message lisible était "
        "attendu. Le troisième porte sur l'assistant : une réponse fausse y "
        "prend l'apparence d'une réponse juste, puisqu'elle est rédigée en "
        "français et accompagnée d'une source."))
    p.append(E.para(
        "Six niveaux de test répondent à ces risques. Leur répartition n'est "
        "pas un choix de forme : chacun couvre ce que les autres ne voient pas."))
    p.append(E.legende_tableau(
        "Niveaux de test et question à laquelle chacun répond"))
    p.append(E.tableau(["Niveau", "Portée", "Question posée", "Exécution"],
                       NIVEAUX, [23, 17, 44, 16]))
    return p


def section_donnees():
    p = [E.titre("5.2 Validation des données", 2)]
    p.append(E.para(
        "Les contrôles de chargement sont décrits au point 3.6 : recomparaison "
        "des valeurs écrites à leur fichier d'origine, contrôle des totaux, "
        "vérification du rattachement territorial. Ils portent sur la fidélité "
        "du transfert."))
    p.append(E.para(
        "Un second contrôle porte sur le sens des indicateurs, et le point "
        "3.6.1 en détaille la méthode sur les données de migration. Son "
        "principe est reproductible : lorsqu'une source publie à la fois un "
        "indice et ses composantes, on retrouve la définition de l'indice en "
        "essayant tous les dénominateurs possibles et en retenant celui qui "
        "reproduit la valeur publiée. Le test porte sur 179 territoires et ne "
        "laisse aucune place à l'interprétation."))
    p.append(E.para(
        "Trois libellés ont été corrigés à l'issue de ce contrôle, dont un qui "
        "désignait l'inverse du contenu de sa colonne. Un libellé faux est "
        "plus dangereux qu'un libellé absent : l'assistant l'énoncerait comme "
        "un fait, accompagné de sa source officielle."))
    return p


# --------------------------------------------------------------------------
# 5.3 — les tests unitaires
# --------------------------------------------------------------------------
UNITAIRES = [
    ("test_verification.py", "_verifier", "7",
     "un chiffre inventé affiché avec une source officielle"),
    ("test_gardiens.py", "garde_temps, garde_intention", "15",
     "une projection ou un calcul présenté comme une donnée publiée"),
    ("test_intention.py", "intention", "8",
     "la mauvaise réponse à la bonne question"),
    ("test_recherche.py", "_racine, chercher, _membre_demande", "11",
     "une valeur exacte prise au mauvais indicateur"),
    ("test_definitions.py", "_definition_redigee", "7",
     "un nom de colonne servi en guise d'explication"),
]


def section_unitaires():
    p = [E.titre("5.3 Tests unitaires de la couche déterministe", 2)]
    p.append(E.para(
        "Quarante-huit tests couvrent les fonctions qui décident de la "
        "justesse d'une réponse. Le choix de ces fonctions, et l'absence "
        "d'autres, obéit à un critère unique : une régression y aurait un coût "
        "nommable pour l'utilisateur. Les fonctions d'affichage ou de mise en "
        "forme n'en font pas partie."))
    p.append(E.para(
        "Les fonctions éprouvées sont pures : elles reçoivent du texte et "
        "rendent une décision. Celles qui lisent le catalogue passent par un "
        "entrepôt de substitution, qui remplace les requêtes SQL par la "
        "lecture des fichiers de préparation. La campagne s'exécute donc sans "
        "base de données, sans serveur et sans modèle, en moins d'une seconde "
        "— condition pratique pour qu'elle soit réellement lancée avant "
        "chaque livraison."))
    p.append(E.legende_tableau(
        "Répartition des tests unitaires et risque couvert par chacun"))
    p.append(E.tableau(["Module", "Fonctions éprouvées", "Tests",
                        "Ce qu'une régression coûterait"],
                       UNITAIRES, [29, 21, 8, 42]))
    p.append(E.para(
        "Ces tests se distinguent de l'évaluation fonctionnelle décrite au "
        "point 4.7 par ce qu'ils isolent. Les trois cents questions notent la "
        "branche empruntée par la chaîne complète ; lorsqu'une réponse est "
        "fausse, elles n'indiquent pas laquelle des quatre couches a failli. "
        "Les tests unitaires répondent à cette question, et les deux mesures "
        "ne se remplacent pas."))
    p.append(E.para(
        "Leur première exécution a mis au jour deux défauts. Le premier "
        "touchait la détection d'interprétation ajoutée : la forme conjuguée "
        "d'un verbe était reconnue quand son participe présent ne l'était pas, "
        "faute d'avoir prévu la variation d'accent de la deuxième syllabe. Une "
        "reformulation pouvait donc ajouter un commentaire d'analyse sans être "
        "rejetée. La détection porte désormais sur le radical, et vingt-deux "
        "formes fléchies ont été vérifiées."))
    p.append(E.para(
        "Le second touchait le gardien de l'intention, qui refusait « comment "
        "calcule-t-on cet indicateur ? » comme une demande de calcul, alors "
        "que cette question interroge la méthode. Sa correction illustre un "
        "risque propre aux campagnes de test : élargir la détection au mot "
        "« moyenne » a fait chuter l'évaluation fonctionnelle de 80 % à 79 %, "
        "en écartant cinq questions légitimes — « température moyenne », "
        "« humidité relative moyenne », « distance moyenne des logements » "
        "sont des noms d'indicateurs publiés. Le signal n'est pas le mot mais "
        "sa conjonction avec une portée territoriale au pluriel : « la moyenne "
        "des huit provinces » demande un calcul, « la température moyenne de "
        "Larache » demande une lecture. Après correction, l'évaluation "
        "fonctionnelle retrouve son niveau et les deux défauts sont couverts "
        "par des tests."))
    return p


# --------------------------------------------------------------------------
# 5.4 — les tests d'intégration
# --------------------------------------------------------------------------
INTEGRATION = [
    ("Authentification", "connexion valide, identifiants erronés, accès sans "
     "jeton, lecture de l'identité", "200, 401, 401, 200"),
    ("Autorisation", "accès administrateur, accès refusé au profil "
     "utilisateur", "200, 403"),
    ("Consultation", "territoires, familles d'indicateurs, valeurs, "
     "comparaison, exploration", "200"),
    ("Cas d'erreur", "territoire inexistant, jeton de réinitialisation "
     "expiré, action de journal hors liste", "404, 400, 400"),
    ("Journalisation", "enregistrement d'une action de consultation", "204"),
    ("Assistant", "accès sans jeton, demande de valeur, mémoire de "
     "conversation, territoire ambigu, refus motivé, mémoire après refus, "
     "avis, classement, comparaison, définition", "401, 200"),
]


# Six cas retenus pour l'illustration, un par famille du tableau : la
# connexion, l'autorisation refusée, la ressource inexistante, le jeton
# expiré, le refus motivé de l'assistant et sa branche définition. Les
# vingt-trois autres cas sont consignés sans être reproduits.
FIGURES_SWAGGER = [
    ("t2_login.png", "Connexion réussie : le jeton est délivré avec sa durée "
     "de validité"),
    ("t5_403.png", "Accès refusé au profil utilisateur sur une route "
     "d'administration"),
    ("t10_404.png", "Territoire inexistant : le code 404 accompagné d'un "
     "message explicite"),
    ("t13bis_reset_400.png", "Jeton de réinitialisation expiré : un code 400 "
     "et un message lisible, non une erreur serveur"),
    ("t21_assistant_refus.png", "Refus motivé de l'assistant : le motif est "
     "porté dans la réponse"),
    ("t26_assistant_definition.png", "Branche définition : le texte du "
     "catalogue est restitué avec sa source"),
]


def section_integration(dossier, captures):
    p = [E.titre("5.4 Tests d'intégration de l'interface de programmation", 2)]
    p.append(E.para(
        "Les trente et une routes ont été éprouvées au moyen de la "
        "documentation interactive engendrée par le cadre applicatif, qui "
        "permet d'exécuter chaque appel avec ses paramètres et d'observer la "
        "réponse complète — code de retour, en-têtes et corps."))
    p.append(E.para(
        "Vingt-neuf cas ont été retenus et consignés. Leur sélection suit une "
        "règle : un cas nominal ne prouve que le fonctionnement attendu, et "
        "c'est le comportement en situation d'erreur qui révèle la solidité "
        "d'une interface. La série comprend donc autant de cas d'échec — "
        "identifiants erronés, jeton absent, profil non autorisé, ressource "
        "inexistante, jeton expiré — que de cas nominaux."))
    p.append(E.legende_tableau(
        "Familles de cas éprouvés sur l'interface de programmation"))
    p.append(E.tableau(["Famille", "Cas éprouvés", "Codes obtenus"],
                       INTEGRATION, [20, 57, 23]))
    p.append(E.para(
        "Deux résultats de cette série ont conduit à des corrections décrites "
        "au point 3.9 : un lien de réinitialisation expiré provoquait une "
        "erreur serveur au lieu d'un message lisible, et la désactivation d'un "
        "compte restait sans effet tant que le jeton en cours n'avait pas "
        "expiré."))

    for nom, texte in FIGURES_SWAGGER:
        chemin = os.path.join(captures, nom)
        if not os.path.exists(chemin):
            continue
        rid = E.ajouter_image(dossier, chemin)
        l, h = E.taille(chemin)
        p.append(E.figure(rid, l, h, 9200 + len(p)))
        p.append(E.legende(texte))
    return p


# --------------------------------------------------------------------------
# 5.5 — non-régression
# --------------------------------------------------------------------------
def section_regression():
    p = [E.titre("5.5 Non-régression", 2)]
    p.append(E.para(
        "L'évaluation fonctionnelle de l'assistant, ses neuf familles de "
        "questions et ses deux scores sont exposés au point 4.7. Le dispositif "
        "décrit ici en est le prolongement : rejouer cette évaluation à "
        "volonté, pour vérifier qu'une correction n'en défait pas une autre."))
    p.append(E.para(
        "L'obstacle était le coût d'exécution. Interroger le modèle local sur "
        "trois cents questions demande plusieurs heures et suppose la base de "
        "données disponible. Un entrepôt de substitution lève les deux "
        "contraintes : il remplace les lectures en base par la lecture des "
        "fichiers de préparation, et rend des valeurs factices aux outils de "
        "lecture. La campagne note la branche empruntée, non le chiffre "
        "restitué ; des valeurs factices n'altèrent donc pas le résultat."))
    p.append(E.para(
        "Les trois cents questions s'exécutent ainsi en cinquante-sept "
        "secondes, soit cent quatre-vingt-dix millisecondes par question, sans "
        "base de données ni modèle. Ce dispositif a détecté une régression de "
        "quatre points introduite par une correction sans rapport apparent, "
        "avant qu'elle n'atteigne l'application."))
    return p


# --------------------------------------------------------------------------
# 5.6 — performance
# --------------------------------------------------------------------------
PERFORMANCE = [
    ("Aiguillage déterministe seul", "190 ms",
     "reconnaissance de l'intention, gardiens, recherche de l'indicateur, "
     "lecture de la valeur"),
    ("Réponse avec rédaction par le modèle", "20 à 45 s",
     "le brouillon est composé en quelques millisecondes ; la durée est "
     "celle de la génération du texte"),
    ("Réponse d'une demande de définition", "immédiate",
     "le texte du catalogue est servi tel quel, sans passer par le modèle"),
    ("Salutation", "immédiate", "réponse fixe, sans appel au modèle"),
]


def section_performance():
    p = [E.titre("5.6 Performance", 2)]
    p.append(E.para(
        "Le temps de réponse de l'assistant se décompose en deux parts très "
        "inégales. L'aiguillage déterministe — reconnaissance de l'intention, "
        "gardiens, recherche de l'indicateur, lecture de la valeur en base — "
        "s'exécute en quelques centaines de millisecondes. La rédaction par le "
        "modèle local représente la quasi-totalité du reste."))
    p.append(E.para(
        "Deux mesures ont guidé les choix de conception. La comparaison des "
        "deux tailles de modèle, rapportée au point 4.3, a écarté le modèle de "
        "sept milliards de paramètres : deux fois et demie plus lent, et moins "
        "fiable sur la tâche. Le maintien du modèle en mémoire entre deux "
        "questions supprime par ailleurs le coût de son chargement initial."))
    p.append(E.para(
        "La conséquence pratique est que toute réponse qui peut être servie "
        "sans le modèle l'est. Une demande de définition restitue le texte du "
        "catalogue tel quel : il est déjà rédigé, et le faire reformuler ne "
        "présenterait que des inconvénients — une attente de plusieurs dizaines "
        "de secondes et un risque de dénaturer une mise en garde soigneusement "
        "formulée."))
    p.append(E.legende_tableau(
        "Temps de réponse observés selon la nature de la question"))
    p.append(E.tableau(["Nature de la question", "Temps observé", "Composition"],
                       PERFORMANCE, [30, 16, 54]))
    return p


# --------------------------------------------------------------------------
# 5.7 — bilan
# --------------------------------------------------------------------------
BILAN = [
    ("Validation des données", "179 territoires, 3 classeurs",
     "3 libellés corrigés, 1 anomalie de source signalée"),
    ("Tests unitaires", "48 tests, 5 modules", "2 défauts corrigés"),
    ("Tests d'intégration", "29 cas sur 31 routes", "2 défauts corrigés"),
    ("Évaluation fonctionnelle", "300 questions, 9 familles",
     "80 % strict, 97 % acceptable"),
    ("Non-régression", "270 questions notées en 57 s",
     "1 régression détectée avant livraison"),
]


def section_bilan():
    p = [E.titre("5.7 Bilan", 2)]
    p.append(E.legende_tableau("Synthèse du dispositif de test et de ses résultats"))
    p.append(E.tableau(["Dispositif", "Étendue", "Résultat"], BILAN, [26, 32, 42]))
    p.append(E.para(
        "Le dispositif présente deux limites, qu'il vaut mieux nommer que "
        "laisser deviner. Les tests d'intégration de l'interface de "
        "programmation restent manuels : ils sont consignés par des captures "
        "et non rejoués automatiquement, si bien qu'une régression sur une "
        "route ne serait détectée qu'à la prochaine campagne. L'interface "
        "utilisateur, quant à elle, n'est éprouvée que par l'usage : aucun "
        "test automatisé ne parcourt les écrans."))
    p.append(E.para(
        "Ces deux limites relèvent du même arbitrage, entre le coût de mise en "
        "place et la fréquence des changements. Les couches automatisées sont "
        "celles qui changent le plus souvent et dont les défauts sont les plus "
        "silencieux ; les couches éprouvées manuellement sont celles dont un "
        "défaut se voit immédiatement à l'écran."))
    p.append(E.para(
        "Sur l'ensemble du dispositif, cinq défauts ont été détectés et "
        "corrigés avant livraison, et une régression a été interceptée. Aucun "
        "de ces défauts n'aurait produit de message d'erreur : tous auraient "
        "affiché une réponse d'apparence normale."))
    return p


# --------------------------------------------------------------------------
def chapitre(dossier, captures, num_id):
    """Le chapitre complet, prêt à insérer."""
    p = [E.para("Chapitre 5 : Tests et validation", style="Heading1")]
    p.append(E.para(
        "Les chapitres précédents décrivent ce que la plateforme fait. "
        "Celui-ci expose comment il a été établi qu'elle le fait "
        "correctement. La question n'est pas seulement de savoir si le code "
        "s'exécute sans erreur : une plateforme de données peut fonctionner "
        "parfaitement et restituer des valeurs fausses. Les dispositifs "
        "présentés ici visent donc autant la justesse de la donnée que la "
        "robustesse du logiciel."))
    p += section_strategie()
    p += section_donnees()
    p += section_unitaires()
    p += section_integration(dossier, captures)
    p += section_regression()
    p += section_performance()
    p += section_bilan()
    return p
