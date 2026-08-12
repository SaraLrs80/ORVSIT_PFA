"""
Passages réécrits pour supprimer la narration chronologique.

LA RÈGLE
Un rapport technique décrit la solution livrée et justifie ses choix. Il ne
raconte pas ce qui a été essayé, puis abandonné, puis repris. « La première
version faisait ceci, elle a été remplacée par cela » occupe de la place sans
rien apprendre : le lecteur veut savoir ce que fait la solution et pourquoi
elle est ainsi.

CE QUI RESTE LÉGITIME
Une justification de choix — « l'écran présente ceci plutôt que cela, parce
que… » — est attendue dans un rapport, et c'est même ce qui le distingue
d'une documentation. Une correction ou une amélioration se rapporte
également, mais à sa place : la section 3.9, qui leur est consacrée et les
présente sous forme de tableau difficulté / cause / correction.

Ce qui disparaît, ce sont les passages qui, ailleurs, racontent un état
antérieur du travail au lieu de décrire l'état livré.
"""

import edition as E


# --------------------------------------------------------------------------
# 4.1 — la première règle de fond
#
# Justifiée par ce qu'elle protège, non par ce qu'elle a remplacé.
# --------------------------------------------------------------------------
REGLE_UNE = (
    "La première est que l'assistant ne produit aucune donnée nouvelle. Il "
    "restitue des valeurs déjà publiées, telles qu'elles figurent dans "
    "l'entrepôt : aucune moyenne pondérée, aucun indice composite, aucune "
    "projection. Cette règle protège la traçabilité de chaque réponse. Une "
    "valeur agrégée par la plateforme ne pourrait être rapportée à aucune "
    "publication officielle, et sa pondération relèverait d'un arbitrage "
    "politique qui n'appartient pas à un outil d'observation.")

# La règle d'aiguillage, énoncée comme règle et non comme correction.
REGLE_TERRITOIRE = (
    "Le territoire n'est exigé que des questions qui en appellent un. Une "
    "demande de valeur porte sur un territoire désigné ; un classement porte "
    "sur l'ensemble des territoires d'un niveau et n'en désigne aucun ; une "
    "demande de définition n'en appelle pas du tout. C'est l'intention "
    "reconnue qui détermine ce qu'il faut réunir, et non l'inverse.")


# --------------------------------------------------------------------------
# 4.5 — les mécanismes de la recherche
# --------------------------------------------------------------------------
MECANISMES = (
    "Trois mécanismes complètent cette comparaison de mots. Chacun répond à "
    "un défaut mesuré sur le jeu d'évaluation, et le tableau suivant les "
    "présente avec le défaut qu'il corrige.")

PRINCIPE = (
    "Ce principe gouverne quatre mécanismes de l'assistant. Lorsqu'une liste "
    "de motifs écrite à la main s'allonge sans jamais couvrir les cas, c'est "
    "le signe que le signal cherché n'est pas le bon : les mots-clés du "
    "catalogue remplacent une pondération impossible à régler, la rareté "
    "remplace une liste de mots vides, le décompte des territoires nommés "
    "remplace une liste de tournures comparatives, et la politesse est "
    "reconnue par le contexte plutôt que par une liste de salutations.")


# --------------------------------------------------------------------------
# 4.6 — la rédaction contrôlée
#
# Les deux constats de départ sont conservés parce qu'ils sont MESURÉS et
# qu'ils justifient l'architecture. Ils sont énoncés comme des propriétés du
# modèle, ce qu'ils sont, et non comme deux versions successives du travail.
# --------------------------------------------------------------------------
RISQUE = (
    "La dernière étape confie au modèle la mise en français de la réponse. "
    "C'est là que se joue le risque d'invention, et deux mesures ont conduit "
    "à la conception retenue.")

MESURE_UNE = (
    "Un modèle à qui l'on demande de citer une source qu'on ne lui a pas "
    "transmise en fabrique une. Sur huit réponses obtenues d'une consigne "
    "demandant de mentionner la provenance sans que les faits transmis la "
    "contiennent, trois sources étaient inventées : une décision "
    "gouvernementale imaginaire, l'INSEE — institut français sans rapport "
    "avec le territoire — et un texte à trous. La règle qui en découle "
    "s'applique à tout le chapitre : on ne demande jamais au modèle de citer "
    "ce dont on ne lui a pas donné le contenu.")

MESURE_DEUX = (
    "Une consigne plus contraignante dégrade la réponse au lieu de "
    "l'améliorer. Soumis à six règles dont quatre négatives, le modèle "
    "recopie la fiche de travail, écrit le mot « Source » littéralement et "
    "invente un pourcentage là où les faits n'en contiennent aucun. Un modèle "
    "de petite taille suit mal les interdictions ; il suit bien un exemple et "
    "une tâche simple. La consigne retenue est donc courte, et c'est "
    "l'architecture — non la consigne — qui interdit l'invention.")

CONCEPTION = (
    "Cette architecture renverse le rapport habituel entre le code et le "
    "modèle, et procède en trois temps.")


# --------------------------------------------------------------------------
# 3.8.8 — la vue d'ensemble
# --------------------------------------------------------------------------
def section_vue_ensemble(dossier, capture, figure_id=9101):
    import os
    p = [E.titre("3.8.8 La vue d'ensemble : l'état du catalogue", 3)]
    p.append(E.para(
        "L'écran d'accueil du tableau de bord présente l'état du catalogue "
        "d'indicateurs : le nombre d'indicateurs publiés, les territoires "
        "servis, la part des indicateurs portant une définition rédigée et le "
        "nombre d'organismes producteurs. Il détaille ensuite la couverture de "
        "chaque secteur aux deux échelles territoriales, la répartition des "
        "millésimes et celle des sources. Quatre cartes conduisent vers les "
        "écrans de consultation."))
    p.append(E.para(
        "Ce parti pris demande à être justifié, car un écran d'accueil "
        "présente d'ordinaire le territoire. Deux raisons l'écartent ici. "
        "L'Observatoire publie sur son site une monographie interactive de la "
        "région, qui expose la population, la superficie, l'urbanisation, le "
        "produit intérieur brut et les atouts structurants ; une seconde "
        "présentation des mêmes éléments, accessible seulement après "
        "authentification, n'apporterait rien. Surtout, la couverture "
        "régionale de l'entrepôt est inégale : 159 indicateurs sur 234 portent "
        "une valeur à l'échelle de la région, et le secteur de la santé n'en "
        "compte qu'un sur vingt-quatre, la Carte Sanitaire s'arrêtant à "
        "l'échelon provincial. Un portrait régional serait abondant en "
        "démographie et muet en santé."))
    p.append(E.para(
        "L'écran répond en revanche à une question que ni le site public ni "
        "les autres écrans ne traitent, et qui est la première qu'un chargé "
        "d'études se pose devant une plateforme de données : de quoi dispose-"
        "t-on, à quelles échelles, pour quels millésimes et d'après quelles "
        "sources ?"))

    if os.path.exists(capture):
        rid = E.ajouter_image(dossier, capture)
        l, h = E.taille(capture)
        p.append(E.figure(rid, l, h, figure_id))
        p.append(E.legende("Vue d'ensemble : l'état du catalogue de la plateforme"))

    p.append(E.para(
        "Aucune valeur n'y est agrégée ni recalculée : ce sont des décomptes "
        "de lignes du catalogue, vérifiables un à un dans la table du "
        "référentiel. Deux précisions de lecture figurent sur l'écran. Un "
        "indicateur pouvant être publié à l'échelle provinciale, à l'échelle "
        "communale ou aux deux, les colonnes ne s'additionnent pas. Et la part "
        "des définitions rédigées n'est pas évaluée par une règle propre à cet "
        "écran : elle est obtenue en appelant la fonction dont l'assistant "
        "conversationnel se sert pour décider si une définition apporte "
        "quelque chose. Deux critères pour une même question finiraient par "
        "produire deux réponses différentes devant l'utilisateur."))
    return p


# --------------------------------------------------------------------------
# 2.7.2 — les écrans conçus
# --------------------------------------------------------------------------
ECRANS = [
    ("Page d'accueil publique",
     "présentation de l'observatoire, de sa mission et de ses axes d'analyse, "
     "avec accès à l'authentification et au formulaire de demande d'accès"),
    ("Vue d'ensemble",
     "état du catalogue — couverture par secteur, échelles servies, millésimes "
     "et sources — et accès aux écrans de consultation"),
    ("Fiche territoriale",
     "chiffres clés du territoire, position parmi les territoires de même "
     "niveau, détail par secteur et accès à l'ensemble des données"),
    ("Comparaison",
     "mise en regard de deux à trois territoires du même niveau sur les mêmes "
     "indicateurs"),
    ("Exploration thématique",
     "classement des territoires, représentation cartographique et lecture par "
     "ventilation lorsque la source en publie une"),
    ("Assistant conversationnel",
     "poser une question en français et obtenir une valeur officielle, avec sa "
     "source et son millésime"),
    ("Espace d'administration",
     "gestion des comptes, traitement des demandes d'accès et supervision de "
     "l'usage, réservé au profil administrateur"),
]


def section_ecrans(figures_existantes, num_id):
    p = [E.titre("2.7.2 Les écrans principaux", 3)]
    p.append(E.para("La maquette couvre les écrans suivants :"))
    for indice, (nom, texte) in enumerate(ECRANS):
        fin = "." if indice == len(ECRANS) - 1 else " ;"
        p.append(E.puce(f"{nom} : {texte}{fin}", num_id))
    p.append(E.para(
        "La cartographie n'est pas un écran distinct. La carte est un mode de "
        "lecture, présent dans la fiche territoriale, dans la comparaison et "
        "dans l'exploration thématique ; lui réserver une page séparée "
        "n'apporterait rien qui ne se trouve déjà dans ces trois écrans."))
    p.extend(figures_existantes)
    p.append(E.legende("Maquette de la page d'accueil publique"))
    return p


# --------------------------------------------------------------------------
# 3.6.1 — la vérification du sens des indicateurs
# --------------------------------------------------------------------------
def section_migration():
    p = [E.titre("3.6.1 Vérifier ce qu'un indicateur mesure, et non seulement "
                 "ce qu'il vaut", 3)]
    p.append(E.para(
        "Les contrôles précédents portent sur les valeurs : la donnée écrite "
        "est-elle celle du fichier d'origine ? Les indicateurs de migration "
        "appellent un contrôle d'une autre nature, où la question n'est pas la "
        "fidélité du chargement mais le sens des colonnes."))
    p.append(E.para(
        "Les trois classeurs du Haut-Commissariat au Plan — migration de durée "
        "de vie, à cinq ans et à dix ans — portent des colonnes dont le nom "
        "technique est repris tel quel au nettoyage, tandis que le document de "
        "métadonnées décrit les mêmes notions en français, sans reprendre ces "
        "noms. Rien ne garantit donc que le libellé porté au catalogue "
        "corresponde au contenu de la colonne."))
    p.append(E.para(
        "Le contrôle interroge la donnée plutôt que les intitulés. Les indices "
        "d'entrées et de sorties sont publiés dans la source, à côté de leurs "
        "composantes : il suffit d'essayer tous les dénominateurs possibles et "
        "de retenir celui qui reproduit l'indice publié sur les 179 "
        "territoires du fichier. Aucune interprétation n'intervient."))
    p.append(E.para(
        "Le premier résultat est que les trois horizons n'ont pas le même "
        "dénominateur de sortie. L'indice de durée de vie rapporte les sorties "
        "aux natifs du territoire (178 territoires sur 179) ; les indices à "
        "cinq et à dix ans les rapportent à la population qui y résidait cinq, "
        "respectivement dix ans plus tôt (173 et 179 sur 179). Les indices "
        "d'entrées se rapportent tous à la population sédentaire (179 sur "
        "179). Entrées et sorties n'étant pas rapportées à la même population, "
        "leur différence ne constitue pas un solde migratoire : les "
        "définitions du catalogue l'énoncent explicitement, afin que "
        "l'assistant conversationnel le restitue."))
    p.append(E.para(
        "Le second résultat porte sur trois libellés, corrigés à l'issue du "
        "contrôle. La colonne des « résidents récents » vérifie, sur 178 "
        "territoires sur 179, l'égalité : résidents récents = non-migrants + "
        "sorties. Elle désigne donc l'effectif présent cinq ou dix ans plus "
        "tôt, et non les personnes arrivées depuis. Deux libellés ont été "
        "reformulés en conséquence, et un troisième précisé : la population "
        "sédentaire du classeur à dix ans exclut 18,4 % de la population, part "
        "qui correspond exactement à celle des moins de dix ans publiée par le "
        "recensement, et non à une notion de sédentarité sur dix ans."))
    p.append(E.para(
        "Ce contrôle a par ailleurs signalé une anomalie du fichier source, "
        "sur la commune de Tanger, où la somme des non-migrants et des entrées "
        "dépasse la population de l'unité territoriale. Elle est isolée — un "
        "territoire sur 179 — et relève du producteur de la donnée."))
    return p


# --------------------------------------------------------------------------
# 4.8 — l'interface de l'assistant
# --------------------------------------------------------------------------
FIGURES_ASSISTANT = [
    ("ui_assistant.png",
     "Trois tours de conversation : la précision demandée sur l'indicateur, "
     "puis sur le niveau territorial, enfin la réponse et sa source"),
    ("ui_assistant_refus.png",
     "Deux refus motivés : la projection et le calcul, chacun avec son motif"),
    ("ui_assistant_conversations.png",
     "Historique des conversations : renommer et supprimer"),
    ("ui_assistant_pastille.png",
     "La pastille d'accès, présente sur les autres écrans"),
]


def section_interface(dossier, captures):
    import os
    p = [E.titre("4.8 L'interface de l'assistant", 2)]
    p.append(E.para(
        "L'assistant est accessible par une entrée de la barre de navigation "
        "et par une pastille flottante présente sur les écrans de "
        "consultation. Cette pastille transmet le territoire affiché : depuis "
        "la fiche d'une commune, la question posée porte déjà sur elle."))
    p.append(E.para(
        "L'écran est organisé en deux colonnes. À gauche, l'historique des "
        "conversations, que l'utilisateur peut renommer ou supprimer ; à "
        "droite, le fil des échanges. Chaque réponse porte, sous son texte, le "
        "millésime et la source de la donnée citée, ainsi que deux boutons "
        "d'avis. L'affichage systématique de la provenance n'est pas un "
        "ornement : une réponse rédigée en français ressemble à une opinion, "
        "et c'est la source qui la ramène au statut de donnée officielle."))
    p.append(E.para(
        "Trois choix d'interface méritent d'être justifiés. Le premier "
        "concerne les refus : lorsqu'une question sort du périmètre, le motif "
        "est affiché tel que le moteur l'a produit — donnée absente du "
        "catalogue, millésime non couvert, calcul non autorisé — plutôt qu'un "
        "message d'échec générique. L'utilisateur apprend ainsi ce que la "
        "plateforme contient, au lieu de conclure qu'elle ne fonctionne pas."))
    p.append(E.para(
        "Le deuxième concerne la demande de précision. Lorsqu'une question est "
        "claire mais incomplète — un nom de territoire qui désigne à la fois "
        "une commune et une province — l'assistant la pose plutôt que de "
        "refuser ou de choisir à la place de l'utilisateur. La réponse est "
        "rattachée à la question en attente, et la question initiale est "
        "rejouée telle quelle."))
    p.append(E.para(
        "Le troisième est l'enregistrement de la trace. Chaque échange "
        "conserve en base la branche empruntée, l'indicateur et le territoire "
        "retenus, le motif de refus le cas échéant, l'issue de la vérification "
        "de rédaction et la durée de traitement. Cette trace n'est pas "
        "destinée à l'utilisateur : elle rend l'assistant auditable, ce qui "
        "est la condition d'un usage administratif."))

    for indice, (nom, texte) in enumerate(FIGURES_ASSISTANT):
        chemin = os.path.join(captures, nom)
        if not os.path.exists(chemin):
            continue
        rid = E.ajouter_image(dossier, chemin)
        l, h = E.taille(chemin)
        p.append(E.figure(rid, l, h, 9110 + indice))
        p.append(E.legende(texte))
    return p


# --------------------------------------------------------------------------
# 4.4 — le diagramme de séquence
# --------------------------------------------------------------------------
def diagramme(dossier, chemin, figure_id=9102):
    import os
    if not os.path.exists(chemin):
        return []
    rid = E.ajouter_image(dossier, chemin)
    l, h = E.taille(chemin)
    return [
        E.para(
            "Le parcours complet d'une question, de la saisie à "
            "l'enregistrement de la trace, se lit sur le diagramme suivant. Il "
            "fait apparaître ce que le texte rend mal : la position du modèle, "
            "appelé en avant-dernier, sur une réponse déjà rédigée et déjà "
            "exacte."),
        E.figure(rid, l, h, figure_id),
        E.legende("Parcours d'une question dans l'assistant conversationnel"),
    ]


# --------------------------------------------------------------------------
# 3.7.1 — le tableau des modules de l'API
#
# Relevé sur le code livré : onze modules, trente et une routes. Les deux
# derniers modules développés — l'assistant et le journal d'usage — n'y
# figuraient pas, et le module `fiche` y était désigné par un rang de version
# plutôt que par son rôle. Les deux routeurs de la fiche coexistent parce
# qu'ils répondent à deux besoins distincts : l'un sert l'identité du
# territoire, l'autre le contenu piloté par le catalogue.
# --------------------------------------------------------------------------
MODULES = [
    ("auth", "/auth", "connexion, identité, mot de passe oublié", "4"),
    ("demandes", "/demandes", "dépôt d'une demande d'accès", "1"),
    ("admin", "/admin", "comptes, demandes, statistiques d'usage", "8"),
    ("territoires", "/territoires", "liste des territoires servis", "1"),
    ("fiche", "/fiche, /fiche-nouvelle",
     "fiche territoriale : identité du territoire, familles et valeurs "
     "pilotées par le catalogue", "4"),
    ("comparer", "/comparer", "comparaison de territoires de même niveau", "1"),
    ("explorer", "/explorer", "exploration thématique du catalogue", "4"),
    ("overview", "/overview", "état du catalogue de la plateforme", "1"),
    ("assistant", "/assistant",
     "questions, conversations et avis de l'assistant", "6"),
    ("usage", "/journal", "journalisation des actions de consultation", "1"),
]

PHRASE_MODULES = (
    "L'API compte trente et une routes, réparties en onze modules selon le "
    "domaine fonctionnel. Chaque module est un routeur autonome, monté sur "
    "l'application principale avec son propre préfixe d'adresse, ce qui rend "
    "l'ensemble lisible et permet d'ajouter un domaine sans toucher aux "
    "autres.")


# --------------------------------------------------------------------------
# Les décomptes du catalogue, relevés sur le catalogue livré
#
# UN SEUL FILTRE PARTOUT : secteur servi, disponible à au moins une échelle.
# C'est celui de recherche._lignes, employé par l'assistant, et celui de la
# route /overview. Trois chiffres circulaient auparavant dans le rapport, la
# page publique et le tableau de bord ; un jury les aurait confrontés.
#
#   224  indicateurs servis          221 en province, 136 en commune
#   106  familles au niveau province  58 familles au niveau commune
#   156  portent une définition rédigée, soit 70 %
# --------------------------------------------------------------------------
MESURE_CATALOGUE = (
    "Avec le catalogue entier dans l'invite, aucun des deux modèles n'appelle "
    "plus l'outil : ils répondent d'eux-mêmes, c'est-à-dire qu'ils inventent. "
    "Avec treize indicateurs, tous deux l'appellent systématiquement. La "
    "consigne était identique dans les deux cas ; seule la longueur du "
    "contexte changeait.")

ORIENTATION = (
    "Cette mesure a orienté toute l'architecture. Plutôt que de réduire le "
    "catalogue à une poignée de lignes, le choix a été fait de ne plus rien "
    "lui confier du tout : le modèle ne reçoit pas le catalogue, ne choisit "
    "pas l'indicateur et n'appelle aucun outil. Ces trois décisions sont "
    "prises par du code déterministe. Le modèle n'intervient qu'en dernier, "
    "pour mettre en français une valeur déjà lue.")

FAMILLES = (
    "Elle opère sur les FAMILLES d'indicateurs et non sur les lignes du "
    "catalogue. Les 221 indicateurs servis au niveau provincial ne recouvrent "
    "que 106 notions distinctes : « Type de logement » occupe six lignes, "
    "« Âge quinquennal » seize. Chercher ligne à ligne renverrait six fois la "
    "même notion et saturerait la liste des candidats.")

LIMITE_DEFINITIONS = [
    "Définitions restant à écrire",
    "156 des 224 indicateurs servis portent une définition rédigée ; la "
    "couverture est complète en démographie, en emploi et en santé, partielle "
    "en éducation et en conditions de vie",
    "poursuivre le travail de métadonnées sur les deux secteurs restants, avec "
    "la même exigence : dire ce que l'indicateur ne mesure pas quand la "
    "confusion est probable",
]


# --------------------------------------------------------------------------
# 2.6.1 — le volume du catalogue
#
# Le tableau annonçait 394 indicateurs ; la table en compte 342. Le référentiel
# territorial (3 220) et les établissements scolaires (1 273) sont exacts.
# --------------------------------------------------------------------------
VOLUME_CATALOGUE = "342 indicateurs"


# --------------------------------------------------------------------------
# 3.9 — les difficultés
#
# Le tableau recense les incidents avec leur cause et leur correction ; les
# reprendre ensuite en prose n'ajoute rien. Ce qui manque au tableau, en
# revanche, ce sont les règles de travail que ces incidents ont établies :
# c'est ce que garde la section qui suit.
# --------------------------------------------------------------------------
def section_regles_de_travail():
    p = [E.titre("3.9.1 Règles de travail établies par ces incidents", 3)]
    p.append(E.para(
        "Trois règles se dégagent du tableau précédent et ont gouverné la "
        "suite du développement."))
    p.append(E.para(
        "Les cas d'erreur doivent être éprouvés autant que les cas nominaux. "
        "Trois des défauts recensés ont été découverts en interrogeant "
        "l'interface de programmation avec des valeurs invalides — jeton "
        "expiré, identifiant inexistant, action hors périmètre — et aucun "
        "n'apparaissait en utilisant l'application normalement."))
    p.append(E.para(
        "Après deux corrections successives qui échouent, il faut cesser de "
        "traiter le symptôme et chercher la cause. L'export cartographique en "
        "donne la mesure : quatre tentatives de réglage ont échoué parce que "
        "le principe même était en cause — on photographiait un rendu dont la "
        "géométrie n'était pas maîtrisée. Le remplacement par un tracé "
        "déterministe, qui redessine la planche à partir de la projection "
        "cartographique, a supprimé la question du positionnement au lieu de "
        "la régler."))
    p.append(E.para(
        "Un contrôle qui rassure sans rien établir est plus dangereux qu'un "
        "contrôle absent. Cette règle, déjà énoncée au point 3.6, s'étend à "
        "tout script de vérification : il doit lui-même être éprouvé sur un "
        "cas dont la réponse est connue d'avance."))
    p.append(E.para(
        "Une quatrième leçon relève de la programmation plus que de la "
        "méthode, mais elle a coûté l'accès de tous les comptes à toutes les "
        "routes. Dans une couche de correspondance objet-relationnel, "
        "comparer un attribut de CLASSE à une valeur ne produit pas un "
        "booléen mais un objet représentant un fragment de requête — et tout "
        "objet est vrai dans une condition. Le test doit porter sur "
        "l'instance lue en base, et être placé après cette lecture."))
    return p


# --------------------------------------------------------------------------
# Chapitre 1 — le nombre de communes
#
# Le rapport annonçait 147 communes en deux endroits. Le Haut-Commissariat au
# Plan en publie 146 — 17 urbaines et 129 rurales — et le référentiel
# territorial en compte autant. Les quatre arrondissements de Tanger sont
# rattachés à la commune de Tanger et ne s'ajoutent pas au décompte.
# --------------------------------------------------------------------------
COMMUNES = [("147 communes", "146 communes"),
            ("Nombre de communes 147", "Nombre de communes 146")]
