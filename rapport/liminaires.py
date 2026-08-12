"""
Pages liminaires, introduction générale, conclusion et bibliographie.

L'ORDRE NORMALISÉ D'UN RAPPORT TECHNIQUE
    page de garde · remerciements · résumé · abstract · sommaire ·
    liste des figures · liste des tableaux · liste des abréviations ·
    introduction générale · corps du rapport · conclusion générale ·
    bibliographie

La page de garde reste le document séparé fourni par l'auteure ; tout le reste
est engendré ici.

LES TROIS TABLES SONT DES CHAMPS, NON DU TEXTE
Le sommaire, la liste des figures et la liste des tableaux sont insérés comme
champs Word portant l'attribut « dirty ». Word les recalcule à l'ouverture,
avec les bons numéros de page. Les écrire à la main serait faux dès la
première correction de mise en page.

LES CHIFFRES DU RÉSUMÉ
Ils reprennent, sans les arrondir, les mesures du corps du rapport : 224
indicateurs servis, 154 territoires, 300 questions d'évaluation, 48 tests
unitaires.
"""

import edition as E


# --------------------------------------------------------------------------
def remerciements():
    p = [E.para("Remerciements", style="Heading1")]
    p.append(E.para(
        "Je tiens à exprimer ma sincère reconnaissance à Madame Rajae "
        "ELBOUHALI, mon encadrante au sein du Conseil de la Région "
        "Tanger-Tétouan-Al Hoceïma, pour la confiance qu'elle m'a accordée en "
        "me confiant ce projet, pour la clarté de ses orientations et pour la "
        "disponibilité dont elle a fait preuve tout au long du stage. Ses "
        "remarques ont orienté des choix déterminants, en particulier sur la "
        "rigueur attendue dans le traitement de la donnée publique."))
    p.append(E.para(
        "Mes remerciements s'adressent également à l'ensemble de l'équipe de "
        "la Direction de la planification et du développement régional et de "
        "l'Observatoire Régional de Veille Stratégique et d'Intelligence "
        "Territoriale, pour leur accueil et pour le temps qu'ils ont consacré "
        "à répondre à mes questions sur les sources statistiques régionales."))
    p.append(E.para(
        "Je remercie le corps professoral de l'École Nationale des Sciences "
        "Appliquées de Tanger, et particulièrement la filière Génie "
        "Informatique, pour la formation reçue, qui a rendu ce travail "
        "possible."))
    p.append(E.para(
        "J'exprime enfin ma gratitude à ma famille et à mes proches pour leur "
        "soutien constant."))
    p.append(E.saut_de_page())
    return p


# --------------------------------------------------------------------------
def resume():
    p = [E.para("Résumé", style="Heading1")]
    p.append(E.para(
        "Ce rapport présente la conception et la réalisation d'une plateforme "
        "d'intelligence territoriale pour le Conseil de la Région "
        "Tanger-Tétouan-Al Hoceïma. Le projet répond à une difficulté "
        "concrète de l'Observatoire Régional de Veille Stratégique et "
        "d'Intelligence Territoriale : les indicateurs de la région sont "
        "publiés par des organismes différents, dans des formats "
        "hétérogènes et selon des codifications territoriales qui ne se "
        "correspondent pas, ce qui rend toute comparaison entre territoires "
        "longue et incertaine."))
    p.append(E.para(
        "La solution repose sur un entrepôt de données territorial en schéma "
        "en étoile, alimenté par une chaîne de préparation reproductible, et "
        "gouverné par un catalogue d'indicateurs qui pilote l'ensemble de "
        "l'application : 224 indicateurs servis sur 5 secteurs, pour 8 "
        "préfectures et provinces et 146 communes. Une interface web permet "
        "de consulter la fiche d'un territoire, de comparer des territoires "
        "de même niveau et d'explorer un secteur, avec restitution "
        "cartographique et exports."))
    p.append(E.para(
        "La plateforme est complétée par un assistant conversationnel fondé "
        "sur un modèle de langage exécuté localement. Son architecture répond "
        "à une exigence posée dès l'origine : aucune valeur ne doit être "
        "produite par le modèle. La reconnaissance de l'intention, la "
        "sélection de l'indicateur et la lecture en base sont assurées par du "
        "code déterministe ; le modèle n'intervient qu'en dernier, pour "
        "mettre en français une réponse déjà rédigée et exacte, et une "
        "vérification automatique rejette toute reformulation qui ajoute ou "
        "perd un chiffre."))
    p.append(E.para(
        "Le dispositif de validation comprend la vérification des données "
        "chargées, 48 tests unitaires sur la couche déterministe, 29 cas "
        "d'intégration sur l'interface de programmation et une évaluation "
        "fonctionnelle de l'assistant sur 300 questions."))
    p.append(E.para(
        "Mots-clés : intelligence territoriale, entrepôt de données, schéma "
        "en étoile, catalogue d'indicateurs, disparités territoriales, "
        "assistant conversationnel, modèle de langage local, traçabilité de "
        "la donnée.", italique=True))
    p.append(E.saut_de_page())
    return p


def abstract():
    p = [E.para("Abstract", style="Heading1")]
    p.append(E.para(
        "This report presents the design and implementation of a territorial "
        "intelligence platform for the Regional Council of "
        "Tanger-Tétouan-Al Hoceïma. The project addresses a concrete "
        "difficulty faced by the Regional Observatory for Strategic "
        "Monitoring and Territorial Intelligence: regional indicators are "
        "published by different institutions, in heterogeneous formats and "
        "under territorial coding systems that do not match one another, "
        "making any comparison between territories slow and unreliable."))
    p.append(E.para(
        "The solution rests on a territorial data warehouse designed as a "
        "star schema, fed by a reproducible preparation pipeline and governed "
        "by an indicator catalogue that drives the entire application: 224 "
        "indicators served across 5 sectors, for 8 prefectures and provinces "
        "and 146 municipalities. A web interface allows users to consult a "
        "territory profile, compare territories of the same administrative "
        "level and explore a sector, with cartographic rendering and data "
        "exports."))
    p.append(E.para(
        "The platform is completed by a conversational assistant built on a "
        "locally executed language model. Its architecture answers a "
        "requirement set from the outset: no value may be produced by the "
        "model. Intent recognition, indicator selection and database reading "
        "are handled by deterministic code; the model intervenes only at the "
        "final step, to phrase in natural language an answer that is already "
        "written and exact, and an automatic verification rejects any "
        "rewording that adds or loses a figure."))
    p.append(E.para(
        "The validation process includes verification of the loaded data, 48 "
        "unit tests on the deterministic layer, 29 integration cases on the "
        "application programming interface, and a functional evaluation of "
        "the assistant over 300 questions."))
    p.append(E.para(
        "Keywords: territorial intelligence, data warehouse, star schema, "
        "indicator catalogue, territorial disparities, conversational "
        "assistant, local language model, data traceability.", italique=True))
    p.append(E.saut_de_page())
    return p


# --------------------------------------------------------------------------
def tables():
    p = [E.para("Sommaire", style="Heading1")]
    p.append(E.champ('TOC \\o "1-3" \\h \\z \\u'))
    p.append(E.saut_de_page())

    p.append(E.para("Liste des figures", style="Heading1"))
    p.append(E.champ('TOC \\h \\z \\c "Figure"'))
    p.append(E.saut_de_page())

    p.append(E.para("Liste des tableaux", style="Heading1"))
    p.append(E.champ('TOC \\h \\z \\c "Tableau"'))
    p.append(E.saut_de_page())
    return p


# --------------------------------------------------------------------------
# Les abréviations relevées dans le corps du rapport, et elles seules.
ABREVIATIONS = [
    ("API", "Application Programming Interface — interface de programmation "
     "applicative"),
    ("CRTTA", "Conseil de la Région Tanger-Tétouan-Al Hoceïma"),
    ("CSV", "Comma-Separated Values — format de fichier tabulaire"),
    ("ENSA", "École Nationale des Sciences Appliquées"),
    ("HCP", "Haut-Commissariat au Plan"),
    ("JSON", "JavaScript Object Notation — format d'échange de données"),
    ("JWT", "JSON Web Token — jeton d'authentification"),
    ("MPI", "Multidimensional Poverty Index — indice de pauvreté "
     "multidimensionnelle"),
    ("ORVSIT", "Observatoire Régional de Veille Stratégique et d'Intelligence "
     "Territoriale"),
    ("PFA", "Projet de Fin d'Année"),
    ("RGPH", "Recensement Général de la Population et de l'Habitat"),
    ("SGBD", "Système de Gestion de Base de Données"),
    ("SQL", "Structured Query Language — langage d'interrogation des bases de "
     "données"),
    ("TTA", "Tanger-Tétouan-Al Hoceïma"),
]


def abreviations():
    p = [E.para("Liste des abréviations", style="Heading1")]
    p.append(E.tableau(["Sigle", "Signification"], ABREVIATIONS, [14, 86]))
    p.append(E.saut_de_page())
    return p


# --------------------------------------------------------------------------
def introduction():
    p = [E.para("Introduction générale", style="Heading1")]
    p.append(E.para(
        "La régionalisation avancée confère aux conseils régionaux marocains "
        "des compétences élargies en matière de planification et "
        "d'aménagement du territoire. Exercer ces compétences suppose de "
        "disposer d'une connaissance fine des écarts entre territoires : "
        "identifier les communes en retard d'équipement, mesurer les "
        "contrastes d'accès aux services de base, suivre les dynamiques "
        "démographiques et économiques. C'est à ce besoin que répond "
        "l'Observatoire Régional de Veille Stratégique et d'Intelligence "
        "Territoriale, créé par le Conseil de la Région "
        "Tanger-Tétouan-Al Hoceïma."))
    p.append(E.para(
        "La difficulté n'est pas l'absence de données. Le Haut-Commissariat "
        "au Plan, le ministère de la Santé et de la Protection Sociale et "
        "plusieurs autres organismes publient régulièrement des indicateurs "
        "sur la région. Elle tient à leur dispersion : chaque publication "
        "possède son format, sa périodicité, son découpage territorial et sa "
        "codification propre. Rapprocher deux indicateurs issus de deux "
        "sources différentes suppose un travail manuel de mise en "
        "correspondance, à refaire à chaque nouvelle publication. La donnée "
        "existe, mais elle n'est pas exploitable en l'état pour une lecture "
        "comparative du territoire."))
    p.append(E.para(
        "Le présent projet consiste à concevoir et à réaliser une plateforme "
        "qui lève cette difficulté. Il s'articule autour de trois objectifs. "
        "Le premier est de constituer un entrepôt de données territorial "
        "unifié, alimenté par une chaîne de préparation reproductible, dans "
        "lequel toute valeur reste rattachée à sa source et à son millésime. "
        "Le deuxième est de mettre cet entrepôt à disposition par une "
        "interface de consultation permettant la lecture par territoire, la "
        "comparaison entre pairs et l'exploration thématique. Le troisième "
        "est d'ouvrir l'accès à cette information par un assistant "
        "conversationnel, afin qu'un élu ou un chargé d'études puisse obtenir "
        "une valeur officielle sans connaître au préalable la structure du "
        "catalogue."))
    p.append(E.para(
        "Une exigence gouverne l'ensemble de ces objectifs et se retrouve "
        "dans chaque choix technique du rapport : la plateforme ne produit "
        "aucune donnée nouvelle. Elle restitue des valeurs déjà publiées, "
        "telles qu'elles figurent dans leur source, sans agrégation ni "
        "estimation. Cette exigence est ce qui permet à une valeur affichée "
        "d'être reprise dans un document administratif, et elle explique "
        "plusieurs décisions qui auraient pu sembler restrictives, notamment "
        "au chapitre consacré à l'assistant."))
    p.append(E.para(
        "Le rapport suit la progression du travail. Le premier chapitre "
        "présente l'organisme d'accueil, le contexte du projet et la "
        "problématique. Le deuxième expose l'analyse des besoins et la "
        "conception de la solution, de la modélisation de l'entrepôt à celle "
        "des écrans. Le troisième décrit la réalisation : collecte, "
        "préparation et chargement des données, développement de la couche "
        "applicative et de l'interface. Le quatrième est consacré à "
        "l'assistant conversationnel, à l'architecture qui garantit "
        "l'exactitude de ses réponses et aux mesures qui l'ont établie. Le "
        "cinquième expose le dispositif de test et ses résultats. La "
        "conclusion dresse le bilan du travail et ouvre sur les prolongements "
        "envisageables."))
    p.append(E.saut_de_page())
    return p


# --------------------------------------------------------------------------
def conclusion():
    p = [E.para("Conclusion générale", style="Heading1")]
    p.append(E.para(
        "Ce projet a conduit à la mise en place d'une plateforme "
        "d'intelligence territoriale complète, depuis la collecte des "
        "publications officielles jusqu'à leur restitution par une interface "
        "web et par un assistant conversationnel. Les trois objectifs posés "
        "en introduction sont atteints."))
    p.append(E.para(
        "L'entrepôt de données territorial réunit 342 lignes de catalogue, "
        "dont 224 indicateurs effectivement servis par l'application, "
        "rattachés à un référentiel de 3 220 territoires qui réconcilie "
        "quatre systèmes de codification. Chaque valeur reste liée à sa "
        "source et à son millésime, et la vérification des données chargées a "
        "porté aussi bien sur la fidélité du transfert que sur le sens des "
        "indicateurs — un contrôle qui a conduit à corriger trois libellés "
        "dont l'un désignait l'inverse du contenu de sa colonne."))
    p.append(E.para(
        "L'interface de consultation couvre la lecture par territoire, la "
        "comparaison entre pairs de même niveau et l'exploration thématique, "
        "avec restitution cartographique et exports. Le pilotage par le "
        "catalogue en est la propriété structurante : ajouter un indicateur "
        "au catalogue suffit à le faire apparaître dans l'application, sans "
        "modification du code."))
    p.append(E.para(
        "L'assistant conversationnel constitue l'apport le plus exigeant du "
        "projet. La mesure qui a orienté son architecture est simple : "
        "soumis au catalogue entier, un modèle de langage cesse d'appeler les "
        "outils mis à sa disposition et répond de lui-même, c'est-à-dire "
        "qu'il invente. Le modèle ne reçoit donc plus le catalogue, ne "
        "choisit plus l'indicateur et n'appelle plus aucun outil : ces "
        "décisions sont prises par du code déterministe, et le modèle "
        "n'intervient qu'en dernier, sur une réponse déjà exacte, sous le "
        "contrôle d'une vérification automatique."))
    p.append(E.para(
        "Le travail comporte des limites, exposées aux points 4.9 et 5.7. "
        "L'assistant ne sait pas classer les modalités d'un indicateur ni "
        "identifier les notions voisines absentes du catalogue ; les tests "
        "d'intégration de l'interface de programmation restent manuels ; "
        "l'interface utilisateur n'est éprouvée que par l'usage. Deux "
        "secteurs du catalogue attendent encore un travail de métadonnées."))
    p.append(E.para(
        "Plusieurs prolongements se dessinent. Le plus immédiat consiste à "
        "achever la rédaction des définitions sur les secteurs restants, "
        "puisque c'est la définition, et non le libellé, qui permet à "
        "l'assistant d'expliquer ce qu'un indicateur ne mesure pas. Un "
        "deuxième prolongement porte sur la recherche d'indicateurs : la "
        "comparaison lexicale actuelle pourrait être confrontée à une "
        "recherche tolérante aux fautes de frappe, sur le modèle du "
        "rapprochement déjà employé pour les noms de territoires, puis "
        "mesurée sur le jeu d'évaluation existant. Un troisième consiste à "
        "exploiter les traces enregistrées à chaque échange : les questions "
        "réellement posées par les utilisateurs sont les meilleures "
        "candidates à l'enrichissement du jeu d'évaluation, et le seul moyen "
        "d'orienter les développements suivants sur des usages constatés "
        "plutôt que supposés."))
    p.append(E.para(
        "Sur le plan personnel, ce stage a permis de mener un projet de bout "
        "en bout, de la donnée brute à l'interface livrée, et d'éprouver une "
        "exigence propre au domaine : dans une plateforme de données "
        "publiques, un logiciel qui fonctionne sans erreur peut néanmoins "
        "restituer des valeurs fausses. C'est cette distinction, entre la "
        "correction du programme et la justesse de l'information, qui a "
        "gouverné les décisions de conception les plus structurantes."))
    p.append(E.saut_de_page())
    return p


# --------------------------------------------------------------------------
SOURCES = [
    "Haut-Commissariat au Plan, Recensement Général de la Population et de "
    "l'Habitat 2024, résultats définitifs. https://resultats2024.rgphapps.ma/",

    "Haut-Commissariat au Plan, Caractéristiques démographiques et "
    "socio-économiques de la région Tanger-Tétouan-Al Hoceïma, RGPH 2024.",

    "Haut-Commissariat au Plan, Base de données de la migration interne selon "
    "les résultats du RGPH 2024, octobre 2025, et son document de "
    "métadonnées.",

    "Haut-Commissariat au Plan, Cartographie de la pauvreté "
    "multidimensionnelle, indices communaux.",

    "Haut-Commissariat au Plan, Annuaire Statistique du Maroc 2024.",

    "Ministère de la Santé et de la Protection Sociale, Carte Sanitaire, "
    "offre de soins par province et préfecture.",

    "Ministère de l'Éducation Nationale, du Préscolaire et des Sports, "
    "annuaire des établissements scolaires, année 2023-2024.",

    "Portail national des données ouvertes du Maroc. https://data.gov.ma/",

    "Observatoire Régional de Veille Stratégique et d'Intelligence "
    "Territoriale, monographie interactive de la région "
    "Tanger-Tétouan-Al Hoceïma. https://orvsit.crtta.ma/",

    "Royaume du Maroc, loi organique n° 111-14 relative aux régions.",

    "Kimball R. et Ross M., The Data Warehouse Toolkit: The Definitive Guide "
    "to Dimensional Modeling, 3e édition, Wiley, 2013.",

    "Documentation de FastAPI, cadre applicatif Python pour interfaces de "
    "programmation. https://fastapi.tiangolo.com/",

    "Documentation de PostgreSQL, système de gestion de base de données "
    "relationnelle. https://www.postgresql.org/docs/",

    "Documentation de React et de Vite, bibliothèque et outil de "
    "construction pour interfaces web. https://react.dev/",

    "Documentation de Leaflet, bibliothèque de cartographie interactive. "
    "https://leafletjs.com/",

    "Documentation d'Ollama, exécution locale de modèles de langage. "
    "https://ollama.com/",

    "Qwen Team, Qwen2.5 Technical Report, Alibaba Group, 2024.",
]


def bibliographie(num_id):
    p = [E.para("Bibliographie et webographie", style="Heading1")]
    p.append(E.para(
        "Les sources de données sont citées dans l'ordre de leur apparition "
        "dans le rapport ; les références techniques suivent. Chaque "
        "indicateur du catalogue porte par ailleurs sa source propre, "
        "consultable dans l'application."))
    for source in SOURCES:
        p.append(E.puce(source, num_id))
    return p


# --------------------------------------------------------------------------
def avant(num_id):
    """Tout ce qui précède le chapitre 1."""
    return (remerciements() + resume() + abstract() + tables()
            + abreviations() + introduction())


def apres(num_id):
    """Tout ce qui suit le chapitre 5."""
    return conclusion() + bibliographie(num_id)
