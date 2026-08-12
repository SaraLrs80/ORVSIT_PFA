"""
Rétrécir le catalogue avant de parler au modèle.

POURQUOI CE FICHIER EXISTE
La mesure du 6 août est sans appel : avec les 254 indicateurs dans l'invite,
qwen2.5:3b n'appelle plus l'outil (0 fois sur 3) ; avec 13 indicateurs, il
l'appelle systématiquement (3 fois sur 3). La consigne était identique. Seule
la longueur changeait.

On ne montre donc jamais le catalogue entier au modèle. On cherche d'abord,
ici, en Python, et on ne lui présente qu'une poignée de candidats.

DEUX RÈGLES DE CONCEPTION, ÉTABLIES PAR LA MESURE

1. LA COUVERTURE D'ABORD.
   Un candidat qui couvre deux mots de la question bat toujours un candidat qui
   n'en couvre qu'un, peu importe où le mot a été trouvé. Sans cette règle, un
   mot-clé « habitants » posé sur Population légale lui faisait gagner
   « habitants par médecin » et « habitants par lit » — mesuré, pas supposé.
   Les mots-clés ne départagent que les candidats à couverture ÉGALE.

2. ON CHERCHE DES FAMILLES, PAS DES LIGNES.
   « Type de logement » occupe 6 lignes du catalogue, « Âge quinquennal » 16.
   Une recherche ligne à ligne renverrait six fois la même notion et mangerait
   toutes les places. En familles : 109 notions au lieu de 254 lignes, et
   chaque candidat apporte quelque chose de différent.

CE QUE CE FICHIER N'EST PAS
Ce n'est pas de l'intelligence artificielle. C'est une comparaison de mots.
Le résultat est reproductible : la même question donne toujours les mêmes
candidats, ce qu'aucun modèle ne garantit.
"""

import re
import unicodedata

from sqlalchemy import text

from ..referentiel import SECTEURS, cle_famille, millesime_famille

# Mots qui n'aident pas à distinguer un indicateur d'un autre. Les noms de
# niveaux en font partie : le niveau est traité ailleurs, par le paramètre.
VIDES = set("""
le la les l de des du d un une et ou a au aux en dans pour par sur que qui quoi
quel quelle quels quelles est sont ce c cette ces il elle on je tu me moi toi
combien y t donne dis plus moins tres pas ne n s sais es svp bonjour merci avec
sans son sa ses leur leurs mon ma mes territoire territoires province provinces
prefecture prefectures commune communes region regions veux voudrais savoir
peux aide aider chiffre chiffres valeur rapport contient indicateur indicateurs
regional regionale nombre total
""".split())

# Le pont entre le mot de l'utilisateur et le mot de la statistique.
# Ce n'est pas de la donnée : c'est du vocabulaire français, il vit donc dans
# le code. Les termes propres à UN indicateur, eux, vivent dans la colonne
# mots_cles du catalogue.
#
# CETTE TABLE A ÉTÉ RÉDUITE DE MOITIÉ après la mesure du 7 août, et chaque
# retrait a une raison :
#   - « gens », « personnes », « pauvre » : la colonne mots_cles fait mieux,
#     puisqu'elle désigne un indicateur précis au lieu d'injecter des mots
#     dans toutes les questions ;
#   - « medecin » injectait « habitants », ce qui faisait répondre la
#     population à « combien de médecins dans la commune de Bab Berred ? » ;
#   - « ordinateur » et « analphabete » n'apportaient rien : une fois tronqués
#     à six lettres, le mot de l'utilisateur et celui du libellé ont déjà la
#     même racine.
#
# Un synonyme est global et aveugle : il s'applique à toutes les questions.
# Il ne doit donc porter que du vocabulaire dont l'équivalence est vraie
# partout, jamais une préférence entre deux indicateurs.
SYNONYMES = {
    "travail": "chomage",
    "travaille": "chomage",
    "chome": "chomage",
    "ecole": "etablissement scolaire",
    "lycee": "qualifiant etablissement",
    "college": "collegial etablissement",
    "hopital": "lit hospitalier",
    "lire": "analphabetisme",
    # Relevés dans les trois cents questions : ce sont les mots que les gens
    # emploient là où la statistique en emploie d'autres.
    "peupl": "population",
    "habite": "population",
    "chaud": "temperature maximale",
    "froid": "temperature minimale",
    "pluie": "humidite",
}

LONGUEUR_RACINE = 7   # « ordinateurs » et « ordinateur » -> « ordinat »
#
# Sept et non six : à six lettres, « internet » et « international » donnaient
# la même racine « intern », et la question « taux d'utilisation d'Internet
# dans la commune de Bab Taza » recevait pour réponse le nombre de migrants
# internationaux. Une valeur exacte, du mauvais indicateur — pire qu'un refus.

# En dessous de ce score, aucun candidat n'est retenu.
#
# Le score pèse chaque mot par sa RARETÉ : un mot présent dans onze familles
# ne distingue rien, un mot présent dans une seule désigne. « Taux » vaut donc
# 1/11, « chômage » vaut 1. Sans ce seuil, « taux d'urbanisation » trouvait
# « Taux de chômage » sur le seul mot « taux », et « espérance de vie moyenne »
# trouvait « Température moyenne ».
SEUIL_PERTINENCE = 0.40

# Part de la question qu'un candidat doit expliquer pour être retenu malgré un
# mot courant. Une question courte — « combien de ménages à Ouezzane ? » — ne
# contient que le mot cherché et le nom du territoire : la moitié.
PART_MINIMALE = 0.50


def _sans_accents(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _racine(mot):
    """La racine d'un mot : marques de pluriel et de féminin retirées d'abord.

    La troncature seule ne suffit pas. « privé » et « privées » donnaient
    « prive » et « privee » — deux racines différentes pour le même mot, et le
    bon indicateur perdait un point au profit de la modalité « Voiture privée »
    d'une famille sans rapport. Tout mot court au féminin ou au pluriel était
    concerné, pas seulement celui-là.

    On retire donc UN « s » de pluriel, puis AU PLUS DEUX « e » :
        privées -> privee -> prive -> priv
        privé   -> prive  -> priv
        écoles  -> ecole  -> ecol
        urbanisée -> urbanise -> urbanis   (= urbanisation tronquée)

    Le bornage n'est pas cosmétique. Une boucle sans limite dépouillait
    « urbanis » de son « s » final et rendait « urbani », qui ne rejoignait
    plus « urbanisation ». Une racinisation trop gourmande manque autant de
    correspondances qu'une racinisation trop timide.

    La garde `len(mot) > 3` évite de réduire un mot court à rien : « vie » et
    « ans » restent entiers. C'est grossier — un vrai racineur ferait mieux —
    et c'est suffisant pour des libellés statistiques.
    """
    if len(mot) > 3 and mot.endswith("s"):
        mot = mot[:-1]
    for _ in range(2):
        if len(mot) > 3 and mot.endswith("e"):
            mot = mot[:-1]
    return mot[:LONGUEUR_RACINE]


def _racines(texte):
    """L'ensemble des racines utiles d'un texte.

    Les nombres comptent, même courts. « Population de 7 à 12 ans » et
    « Population de 10 ans et plus » ne se distinguent que par eux : en les
    écartant comme des mots trop brefs, la première question recevait la
    seconde en réponse.
    """
    return {_racine(m)
            for m in re.findall(r"[a-z0-9]+", _sans_accents(texte))
            if (len(m) > 2 or m.isdigit()) and m not in VIDES}


def _enrichir(question):
    """Ajoute à la question les mots de la statistique correspondants."""
    base = _sans_accents(question)
    ajouts = [v for k, v in SYNONYMES.items() if k in base]
    return question + " " + " ".join(ajouts)


def _lignes(dwh, niveau):
    """Les indicateurs publiés au niveau demandé. Rien d'autre."""
    condition = ""
    if niveau == "commune":
        condition = "AND dispo_commune IS TRUE"
    elif niveau == "prefecture_province":
        condition = "AND dispo_province IS TRUE"

    return dwh.execute(text(f"""
        SELECT indicateur_id, libelle_court, unite, secteur, annee, source,
               COALESCE(mots_cles, '') AS mots_cles
        FROM referential.dim_indicateur
        WHERE secteur = ANY(:secteurs)
          AND (dispo_province IS TRUE OR dispo_commune IS TRUE)
        {condition}
        ORDER BY secteur, indicateur_id
    """), {"secteurs": SECTEURS}).mappings().all()


def secteur_demande(question):
    """Le secteur nommé dans la question, ou None.

    Une question qui nomme un secteur sans nommer d'indicateur — « parle-moi
    de la santé », « de quoi disposes-tu sur l'emploi ? » — ne porte pas sur
    un indicateur mais sur le secteur entier. Chercher un indicateur y répond
    par trois indicateurs pris au hasard parmi ceux du secteur, puisque le mot
    « santé » figure dans le secteur de tous.

    Le moteur bascule alors sur lister_indicateurs, qui dit ce qui existe.
    """
    mots = _racines(question)
    for secteur in SECTEURS:
        racines_secteur = _racines(secteur)
        if racines_secteur and racines_secteur <= mots:
            return secteur
    return None


def familles(dwh, niveau=None):
    """Le catalogue regroupé en notions, avec le texte sur lequel on cherche."""
    groupes = {}
    for ligne in _lignes(dwh, niveau):
        cle, _typ, etiquette = cle_famille(ligne["libelle_court"], ligne["secteur"])
        famille = groupes.setdefault(cle, {
            "nom": cle[1],
            "secteur": cle[0],
            "unite": ligne["unite"],
            "source": ligne["source"],
            "membres": [],
            "_annees": [],
            "_mots_cles": [],
        })
        famille["_annees"].append(ligne["annee"])
        # Les mots-clés sont posés sur chaque membre : un membre peut manquer
        # à un niveau territorial, la famille ne doit pas perdre son
        # vocabulaire pour autant. On réunit donc ceux de tous les membres.
        famille["_mots_cles"].append(ligne.get("mots_cles") or "")
        famille["membres"].append({
            "indicateur_id": ligne["indicateur_id"],
            "etiquette": etiquette,
            "annee": ligne["annee"],
        })

    for famille in groupes.values():
        famille["annee"] = millesime_famille(famille.pop("_annees"))
        # Les étiquettes des membres font partie du texte cherché : « villa »
        # doit mener à « Type de logement », alors que le mot n'est pas dans
        # le nom de la famille.
        etiquettes = " ".join(m["etiquette"] for m in famille["membres"])
        famille["_cles"] = _racines(" ".join(famille.pop("_mots_cles")))
        # Le nom du SECTEUR n'entre pas dans les mots de l'indicateur. Il y
        # figurait, et « Conditions de vie » donnait le mot « vie » à
        # trente-trois familles : « espérance de vie moyenne » trouvait alors
        # « Température moyenne », deux mots partagés, aucun rapport.
        # Les questions qui portent sur un secteur entier sont reconnues
        # ailleurs, par secteur_demande.
        famille["_mots_nom"] = _racines(famille["nom"])
        famille["_mots"] = (famille["_mots_nom"]
                            | _racines(etiquettes)
                            | famille["_cles"])

    liste = list(groupes.values())

    # La rareté de chaque mot, mesurée sur le catalogue lui-même. Rien n'est
    # écrit à la main : le poids d'un mot se déduit du nombre de familles qui
    # l'emploient, et il se met à jour tout seul quand le catalogue change.
    frequence = {}
    for f in liste:
        for mot in f["_mots"]:
            frequence[mot] = frequence.get(mot, 0) + 1
    for f in liste:
        f["_frequence"] = frequence

    return liste


def _pertinence(demandes, famille):
    """Le poids des mots partagés, chaque mot pesé par sa rareté.

    Un mot présent dans onze familles vaut 1/11 ; un mot présent dans une
    seule vaut 1. Un mot-clé écrit à la main vaut 1 quoi qu'il arrive : il a
    été posé exprès sur cet indicateur.
    """
    freq = famille.get("_frequence") or {}
    total = 0.0
    for mot in demandes & famille["_mots"]:
        if mot in famille["_cles"]:
            total += 1.0
        else:
            total += 1.0 / max(1, freq.get(mot, 1))
    return total


def chercher(dwh, question, niveau=None, k=8):
    """
    Les k familles d'indicateurs dont les mots ressemblent le plus à la question.

    Renvoie une liste vide quand rien ne correspond — et c'est un résultat,
    pas un échec : cela signifie que la donnée demandée n'existe pas dans le
    catalogue, et l'assistant doit alors refuser sans interroger le modèle.

    Le classement suit la règle de la couverture :
        1. le nombre de mots de la question effectivement couverts ;
        2. à couverture égale, ceux couverts par un MOT-CLÉ écrit à la main —
           c'est ce qui désigne « Population légale » comme l'indicateur qu'on
           entend par « population » ;
        3. puis ceux couverts par le NOM de la famille plutôt que par une
           étiquette de modalité ;
        4. à égalité encore, la part du nom couverte, qui pénalise les libellés
           fourre-tout ;
        5. en dernier ressort, le millésime le plus récent.

    La couverture reste devant, et c'est ce qui rend les mots-clés sûrs :
    « habitants par médecin » couvre deux mots pour « Habitants par médecin »
    contre un seul pour « Population légale ». Aucun mot-clé ne peut renverser
    cet écart.
    """
    demandes = _racines(_enrichir(question))
    if not demandes:
        return []

    resultats = []
    for f in familles(dwh, niveau):
        touches = demandes & f["_mots"]
        if not touches:
            continue
        # Un candidat qui ne tient qu'à UN SEUL mot doit se justifier autrement.
        # Sans cette règle, « taux d'urbanisation » trouvait « Taux de
        # chômage » et « espérance de vie moyenne » trouvait « Température
        # moyenne » : des valeurs exactes, prises au mauvais indicateur.
        #
        # Deux justifications suffisent, et chacune répond à un cas réel :
        #   - le mot est RARE : « chômage » n'existe que dans une famille ;
        #   - le mot explique une bonne PART de la question : « combien de
        #     ménages à Ouezzane ? » ne contient que « ménages » et le nom du
        #     territoire. Un mot sur deux, c'est la moitié de la demande — le
        #     candidat n'a rien laissé de côté.
        # « Mosquées recensées à Al Hoceïma » échoue aux deux : « recensé »
        # n'est pas rare, et il laisse « mosquées » sans réponse.
        if len(touches) == 1:
            part = len(touches) / max(1, len(demandes))
            if (_pertinence(demandes, f) < SEUIL_PERTINENCE
                    and part < PART_MINIMALE):
                continue
        touches_nom = demandes & f["_mots_nom"]
        touches_cles = demandes & f["_cles"]
        recence = max((str(a) for a in (m["annee"] for m in f["membres"])), default="")
        resultats.append((
            (len(touches),                                   # 1. couverture
             len(touches_cles),                              # 2. mots-clés
             len(touches_nom),                               # 3. nom plutôt que modalité
             len(touches_nom) / max(1, len(f["_mots_nom"])),  # 4. précision du nom
             recence),                                       # 5. millésime
            f,
        ))

    resultats.sort(key=lambda r: r[0], reverse=True)
    retenues = []
    for score, f in resultats[:k]:
        garde = {k2: v for k2, v in f.items() if not k2.startswith("_")}
        # La couverture est rendue au moteur : c'est elle qui lui dit si un
        # candidat se détache nettement — auquel cas il n'a pas besoin de
        # demander au modèle de choisir.
        garde["couverture"] = score[0]
        retenues.append(garde)
    return retenues


def vedettes(dwh, niveau=None, k=5):
    """Les indicateurs les plus courants, à proposer quand la question n'en
    nomme aucun.

    Ce sont exactement ceux qui portent des mots-clés : la colonne a été
    remplie pour les notions que les gens nomment spontanément — population,
    chômage, pauvreté. Elle sert donc deux fois, et la liste s'enrichit d'elle-
    même à mesure que le catalogue est complété.
    """
    retenues = [f for f in familles(dwh, niveau) if f["_cles"]]
    retenues.sort(key=lambda f: -len(f["_cles"]))
    return [{k2: v for k2, v in f.items() if not k2.startswith("_")}
            for f in retenues[:k]]


def ligne_pour_le_modele(f):
    """Une famille rendue en une seule ligne, telle que le modèle la lira.

    Format :  nom | unité | secteur | millésime | membres
    Les membres portent leur identifiant, car c'est lui que le modèle devra
    recopier dans l'appel d'outil — il n'a jamais à deviner un nom.
    """
    if len(f["membres"]) == 1:
        membres = str(f["membres"][0]["indicateur_id"])
    else:
        membres = ", ".join(f"{m['etiquette']}={m['indicateur_id']}"
                            for m in f["membres"])
    return (f"{f['nom']} | {f['unite'] or 'sans unité'} | {f['secteur']} "
            f"| {f['annee'] or 'millésime inconnu'} | {membres}")
