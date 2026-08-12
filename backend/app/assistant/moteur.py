"""
L'aiguilleur de l'assistant.

SON RÔLE
Il ne sait rien lui-même. Il écoute la question, décide quoi en faire, appelle
les outils qu'il faut, et ne dérange le modèle qu'à la fin, pour la phrase.

    recherche.py  = le bibliothécaire : on lui donne un mot, il rend la liste
                    des indicateurs qui en parlent. Il ne décide rien.
    moteur.py     = l'accueil : il écoute, il refuse, il demande, il va voir le
                    bibliothécaire quand c'est utile — et parfois il n'y va pas
                    du tout, comme pour « bonjour » ou « merci ».
    Ollama        = celui qui met la réponse en jolie phrase, tout à la fin.

SON PARCOURS
    1. reconnaître l'INTENTION de la question
    2. les gardiens : temps, intention interdite
    3. réunir ce dont cette intention a besoin — un territoire, deux, ou aucun
    4. appeler l'outil correspondant
    5. le modèle rédige

POURQUOI L'INTENTION D'ABORD
Une première version demandait un territoire à toutes les questions. Elle
répondait « de quel territoire s'agit-il ? » à « quelle province a le taux de
chômage le plus élevé ? » — alors que cette question les classe tous. Toutes
les questions n'ont pas les mêmes besoins, et c'est l'intention qui le dit.

    intention      exemple                             a besoin de
    valeur         « le chômage à Tétouan »            un territoire
    classement     « quelle province a le plus… »      aucun : tous les pairs
    comparaison    « compare Tétouan et Larache »      au moins deux
    definition     « que mesure cet indicateur ? »     aucun
    couverture     « que sais-tu sur la santé ? »      aucun
    conversation   « bonjour », « merci »              rien du tout

LA TRACE
Chaque réponse dit par où elle est passée : branche, refus, candidats, outils
appelés avec leurs arguments. C'est ce qui rend une campagne de trois cents
questions notable automatiquement, sur des faits et non sur la formulation.
"""

import re

from sqlalchemy.orm import Session

from .gardiens import garde_intention, garde_temps
from .outils import (
    _territoires, classer, cle, comparer, decrire, lire_valeur,
    lister_indicateurs, niveau_demande, resoudre_territoire,
)
from .recherche import chercher, secteur_demande, vedettes, _racines

MODELE = "qwen2.5:3b"
GARDE_EN_MEMOIRE = "30m"
PLAFOND_JETONS = 220

# --------------------------------------------------------------------------
# 1. Reconnaître l'intention
# --------------------------------------------------------------------------
# Les motifs sont essayés dans l'ordre : le premier qui répond gagne. L'ordre
# n'est pas arbitraire — « compare le taux le plus élevé de X et Y » est une
# comparaison avant d'être un classement.

# Une salutation ne compte que si elle est TOUTE la phrase. « Bonjour je
# voudrais savoir combien de gens ne travaillent pas » est une vraie question :
# le premier mot ne doit pas emporter le reste.
_POLITESSE_SEULE = re.compile(
    r"^\s*(bonjour|bonsoir|salut|coucou|merci( beaucoup)?|au revoir|ok|"
    r"d'accord|super|parfait)\s*[!.?]*\s*$", re.I)

# Un mot de politesse n'importe où. Seul, il ne décide de rien — « Bonjour, je
# voudrais le taux de chômage » est une vraie question. Il ne fait basculer en
# conversation que si, par ailleurs, aucun indicateur et aucun territoire n'ont
# été trouvés : c'est alors qu'il n'y a rien à chercher.
_POLITESSE_MOT = re.compile(
    r"\b(bonjour|bonsoir|salut|coucou|merci|au revoir|comment [çc]a va|"
    r"[çc]a va|bonne journ[ée]e|de rien|super|parfait|bravo)\b", re.I)

# Les questions sur l'assistant lui-même, où qu'elles se trouvent.
# La liste s'est allongée avec le jeu de trois cents questions : les gens
# demandent bien plus souvent « t'es un robot ? » que « qui es-tu ? ».
_META = re.compile(
    r"\b(qui es[- ]?tu|qui t'?a (cr[ée][ée]|fait|programm)|"
    r"que fais[- ]?tu|que fait[- ]?utu|tu peux m'aider|peux[- ]?tu m'aider|"
    r"comment [çc]a marche|[àa] quoi sers[- ]?tu|"
    r"t'?es (un |une |qui|quoi)|tu es (un |une )(robot|machine|humain|ia|"
    r"intelligence|vraie|programme)|robot ou|"
    r"tu fonctionnes? comment|comment tu fonctionnes|quel (systeme|système)|"
    r"c'?est quoi comme (systeme|système)|"
    r"(t'?es|tu es) fiable|fiable [àa] quel point|"
    r"es[- ]?tu s[uû]re?|tu es (vraiment )?(s[uû]re?|certaine?)|"
    r"pas d'?erreur possible)\b", re.I)

_COUVERTURE = re.compile(
    r"\b(que sais[- ]?tu|qu'?as[- ]?tu|de quoi disposes?[- ]?tu|"
    r"quels? (indicateurs?|donn[ée]es?)|quelles donn[ée]es|"
    r"que peux[- ]?tu (me )?(dire|donner)|liste[rz]?|"
    r"(as[- ]?tu|avez[- ]?vous|vous avez|tu as) (des |comme |quelles? )?"
    r"(donn[ée]es|indicateurs?|informations?|infos?|chiffres?)|"
    r"comme (donn[ée]es|infos?)|quoi comme|"
    # Les tournures relevées dans le jeu de trois cents questions : les gens
    # demandent « ce qui existe », « ce qui est disponible », « ce qui est
    # publié » bien plus souvent que « quels indicateurs ».
    r"(ce )?qui (est )?(disponible|publi[ée]|existe)|tout ce qui (existe|touche)|"
    r"est[- ]ce que (vous|tu) couvre[zs]?|je cherche tout)\b", re.I)

# Attention aux frontières de mot : « comment est calcul\b » ne correspondait
# jamais à « comment est calculé », parce que le « é » qui suit est une lettre
# et qu'aucune frontière ne s'y trouve. Les radicaux tronqués portent donc un
# \w* explicite.
_DEFINITION = re.compile(
    r"\b(que mesure|que veut dire|qu'?est[- ]ce que|c'?est quoi|"
    r"d[ée]finition|d[ée]finiss\w*|d[ée]finit\b|d'?o[uù] vien(t|nent)|"
    r"quelle (est la )?source|quelle enqu[êe]te|comment (est |on )?calcul\w*|"
    r"datent de|sur quoi se base|quel organisme|c'?est comparable|"
    # « Vos chiffres viennent du HCP ou d'ailleurs ? » : le possessif désigne
    # la plateforme elle-même, pas un territoire. C'est une question sur la
    # provenance, quelle que soit la suite.
    r"(vos|tes|ses) (chiffres|donn[ée]es|sources|statistiques) "
    r"(vien(nen)?t|proviennent|sortent|datent)|"
    # « Quelle différence entre le taux d'activité et le taux de chômage ? »
    # oppose deux INDICATEURS, pas deux territoires : c'est une question de
    # définition. Quand ce sont des territoires, la règle des deux territoires
    # nommés reprend la main plus loin.
    r"(quelle est la |quelle )?diff[ée]rence entre)", re.I)

_COMPARAISON = re.compile(
    r"\b(compare[rz]?|comparaison|par rapport [àa]|versus|vs)\b", re.I)

_CLASSEMENT = re.compile(
    r"\b(class(e|er|ement|ez)|(le|la|les) (plus|moins)|premi[eè]re?s?|"
    r"derni[eè]re?s?|top \d+|meilleure?s?|pires?|"
    r"num[ée]ro (un|1)|en t[êe]te|arrive (en|premier))\b", re.I)

# Les mots qui déclarent un niveau territorial, pour reconstruire « province
# de Chefchaouen » à partir d'une phrase entière.
# « communal » et « provincial » doivent compter autant que « commune » et
# « province » : « au niveau communal » désignait le niveau provincial faute
# de reconnaître l'adjectif.
_MOT_NIVEAU = re.compile(
    r"\b(communes?|communal|communaux|municipalites?|"
    r"prefectures?|provinces?|provincial|provinciaux)\b")

# Les échelles dont la plateforme ne publie rien. Les nommer, c'est demander
# une donnée qui n'existe à aucun niveau servi — et il vaut mieux le dire que
# répondre la valeur du territoire qui les contient. « La population du
# quartier Val Fleuri à Tanger » recevait la population de Tanger.
_NIVEAU_NON_SERVI = re.compile(
    r"\b(quartiers?|douars?|cercles?|arrondissements?|"
    r"circonscriptions?|villages?|douar)\b")


def _niveau_du_mot(mot: str) -> str:
    return "commune" if mot.startswith(("commun", "municipal")) \
        else "prefecture_province"


def intention(question: str) -> str:
    if _POLITESSE_SEULE.match(question) or _META.search(question):
        return "conversation"
    if _COUVERTURE.search(question):
        return "couverture"
    if _DEFINITION.search(question):
        return "definition"
    if _COMPARAISON.search(question):
        return "comparaison"
    if _CLASSEMENT.search(question):
        return "classement"
    return "valeur"


# --------------------------------------------------------------------------
# Trouver les territoires dans une phrase
# --------------------------------------------------------------------------

RESSEMBLANCE_MINIMALE = 0.80   # en deçà, on ne devine pas


def _approchants(texte: str, connus: list[dict], dejaVus=frozenset()):
    """TOUS les groupes de mots qui ressemblent à un nom connu, pas seulement
    le meilleur.

    Une première version n'en rendait qu'un. « Compare tetouane et larche »
    contient deux noms fautés : seul le plus ressemblant était retrouvé, et
    l'assistant redemandait « quels territoires voulez-vous comparer ? » alors
    que l'utilisateur venait de les nommer tous les deux.

    Le seuil reste haut : mieux vaut demander que désigner le mauvais
    territoire. `dejaVus` écarte les noms déjà reconnus exactement, sans quoi
    un nom juste serait reproposé comme approchant de lui-même.
    """
    from difflib import SequenceMatcher

    mots = texte.split()
    trouvailles = []          # (position, cle, ressemblance)
    for taille in (1, 2, 3):
        for i in range(len(mots) - taille + 1):
            fenetre = " ".join(mots[i:i + taille])
            if len(fenetre) < 4:
                continue
            if any(v in fenetre or fenetre in v for v in dejaVus):
                continue
            meilleur, score = None, RESSEMBLANCE_MINIMALE
            for t in connus:
                if t["cle"] in dejaVus:
                    continue
                r = SequenceMatcher(None, fenetre, t["cle"]).ratio()
                if r > score:
                    meilleur, score = t["cle"], r
            if meilleur:
                trouvailles.append((texte.find(fenetre), meilleur, score))

    # Une même position ne désigne qu'un territoire : on garde la meilleure
    # correspondance, et on écarte les doublons de nom.
    trouvailles.sort(key=lambda x: -x[2])
    retenus, pris_pos, pris_nom = [], set(), set()
    for pos, c, _r in trouvailles:
        if c in pris_nom or any(abs(pos - p) < 3 for p in pris_pos):
            continue
        retenus.append((pos, c))
        pris_pos.add(pos)
        pris_nom.add(c)
    return retenus


def extraire_territoires(dwh: Session, question: str) -> list[str]:
    """Les noms de territoires contenus dans la question, dans l'ordre.

    resoudre_territoire attend un NOM, pas une phrase : il faut d'abord
    repérer lesquels des 154 territoires servis apparaissent dans le texte.

    Deux précautions, apprises d'une première version qui échouait :

    1. Le nom le PLUS LONG gagne, et les recouvrements sont écartés. Sans
       cela « Tanger » l'emporterait sur « Tanger-Assilah » et désignerait un
       autre territoire.
    2. On ne garde le mot qui précède QUE s'il déclare un niveau. La première
       version prenait les trois mots précédents sans regarder, et cherchait
       un territoire nommé « de pauvrete a chefchaouen ».
    """
    texte = " " + cle(question) + " "

    # Le nom de la région contient ceux de deux provinces : « Tanger-Tétouan-Al
    # Hoceïma » renfermait « Tétouan », et la question sur la région répondait
    # sur la province. La région n'étant pas un territoire servi, on la retire
    # du texte avant de chercher.
    texte = texte.replace(cle("Tanger-Tétouan-Al Hoceima"), " ")

    connus = _territoires(dwh)
    trouves = []
    for t in connus:
        motif = " " + t["cle"] + " "
        pos = texte.find(motif)
        if pos >= 0:
            trouves.append((pos, t["cle"]))

    # Les noms mal orthographiés — « Tetouane », « Al Hoceyma », « Chaouen ».
    # On cherche l'approchant même quand un AUTRE nom a été reconnu
    # exactement : « comparer les communes tetouane et larache » contient un
    # nom juste et un nom fauté, et ne chercher que si tout a échoué faisait
    # perdre le second.
    trouves.extend(_approchants(texte, connus,
                                dejaVus={c for _, c in trouves}))

    # Écarter les recouvrements : à position égale ou incluse, le plus long
    # l'emporte.
    trouves.sort(key=lambda x: (x[0], -len(x[1])))
    retenus = []
    for pos, c in trouves:
        if any(c in autre for _, autre in retenus if autre != c):
            continue
        if any(pos >= p and pos + len(c) <= p + len(autre)
               for p, autre in retenus):
            continue
        retenus.append((pos, c))

    # Un nom entre parenthèses précise le précédent, il n'en ajoute pas un
    # second : « Issaguen (Ketama) » désigne UN territoire. Sans cette règle,
    # la question était prise pour une comparaison entre deux territoires.
    dans_parentheses = set()
    brut = _sans_accents_question(question)
    for ouvrante in (i for i, ch in enumerate(brut) if ch == "("):
        fermante = brut.find(")", ouvrante)
        if fermante > 0:
            dans_parentheses.add(cle(brut[ouvrante + 1:fermante]))

    noms = []
    for pos, c in sorted(retenus):
        if c in dans_parentheses and noms:
            continue
        avant = texte[max(0, pos - 40):pos]
        mot = _MOT_NIVEAU.findall(avant)
        noms.append(f"{mot[-1]} de {c}" if mot else c)
    return noms


def _sans_accents_question(question):
    import unicodedata
    s = unicodedata.normalize("NFD", (question or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# --------------------------------------------------------------------------
# La réponse et sa trace
# --------------------------------------------------------------------------

def _sortie(branche, reponse, trace, **extra):
    trace.update(extra)
    trace["branche"] = branche
    trace["reponse"] = reponse
    return trace


def _niveau(question, defaut="prefecture_province"):
    """Le niveau territorial visé par la question."""
    # Même précaution : cle() amputerait « commune de Bab Berred » du mot qui
    # nous intéresse quand la question commence par lui.
    mot = _MOT_NIVEAU.search(_sans_accents_question(question))
    return _niveau_du_mot(mot.group(1)) if mot else defaut


def _repond_a_une_attente(question: str, attente: dict):
    """L'utilisateur répond-il à une précision qu'on lui a demandée ?

    Quand l'assistant demande « la province ou la commune ? » ou « sur quel
    indicateur ? », le message suivant est une RÉPONSE, pas une nouvelle
    question. Sans cette lecture, « communes » était traité comme une question
    isolée et recevait « cette donnée ne figure pas au catalogue » — puis la
    même demande revenait, indéfiniment.

    Deux attentes, deux façons de reprendre :

      niveau      on rejoue la question d'origine en imposant le niveau à TOUS
                  les territoires qu'elle nomme. C'est ce qui règle d'un coup
                  une question citant deux noms ambigus.
      indicateur  on ajoute la réponse à la question d'origine et on rejoue :
                  « compare Tétouan et Larache » + « population ».
    """
    if not attente or not attente.get("question"):
        return None
    initiale = attente["question"]

    if attente.get("type") == "indicateur":
        # Une réponse d'un ou deux mots complète la question ; une phrase
        # entière est une nouvelle question et doit être traitée comme telle.
        if len(question.split()) > 6:
            return None
        return {"question": f"{initiale} {question}", "niveau_force": None}

    # Surtout pas cle() ici : elle retire le mot de niveau en tête de chaîne,
    # ce qui est son rôle pour un NOM de territoire — « commune de Larache »
    # devient « larache » — mais fait disparaître la réponse qu'on cherche.
    mot = _MOT_NIVEAU.search(_sans_accents_question(question))
    if not mot:
        return None
    return {"question": initiale, "niveau_force": _niveau_du_mot(mot.group(1))}


def repondre(dwh: Session, question: str, etat: dict | None = None,
             modele_actif: bool = True, niveau_force: str | None = None) -> dict:
    etat = dict(etat or {})
    trace = {"question": question, "branche": None, "refus": None,
             "intention": None, "candidats": [], "outils": [], "etat": etat}

    # Une précision attendue est lue AVANT tout le reste : la question à
    # traiter n'est pas celle qu'on vient de recevoir, c'est celle d'avant.
    reprise = _repond_a_une_attente(question, etat.get("attente"))
    if reprise and not niveau_force and not etat.get("_repris"):
        trace["reprise_apres_precision"] = question
        # `_repris` interdit à une reprise d'en déclencher une autre : sans
        # cette garde, une réponse qui laisserait la question encore
        # incomplète relancerait la boucle indéfiniment.
        etat = {**etat, "_repris": True, "attente": None}
        return repondre(dwh, reprise["question"], etat, modele_actif,
                        niveau_force=reprise["niveau_force"])

    trace["intention"] = quoi = intention(question)
    niveau = _niveau(question)

    # Deux territoires nommés dans une même question, c'est une comparaison —
    # quelle que soit la tournure. Les formulations sont innombrables :
    # « différence entre X et Y », « laquelle des deux », « plus élevé à X ou
    # à Y », « X et Y, lequel… ». Allonger la liste des motifs serait sans fin ;
    # compter les territoires ne l'est pas.
    noms_cites = extraire_territoires(dwh, question)
    if len(noms_cites) >= 2 and quoi in ("valeur", "classement", "conversation",
                                         "definition"):
        # « Quelle différence entre le taux d'activité et le taux de chômage ? »
        # oppose deux indicateurs : c'est une définition. La même tournure avec
        # deux territoires — « différence entre Fnideq et M'diq » — est une
        # comparaison. Ce sont les territoires qui tranchent, pas les mots.
        trace["intention"] = quoi = "comparaison"

    # Une salutation ou un « tu peux m'aider ? » collé à une vraie question ne
    # doit pas emporter la question. Si un territoire est nommé, ce n'est plus
    # du bavardage.
    if quoi == "conversation" and noms_cites:
        trace["intention"] = quoi = "valeur"

    # --- conversation : aucun outil, aucun chiffre -------------------------
    if quoi == "conversation":
        return _sortie("conversation", _bavarder(question, etat)
                       if modele_actif else "", trace)

    secteur = secteur_demande(question)
    candidats = chercher(dwh, question, niveau)
    trace["candidats"] = [c["nom"] for c in candidats]

    # Un superlatif appliqué à un SECTEUR, sans indicateur précis, demande un
    # score global — c'est-à-dire l'indicateur composite écarté du projet.
    if quoi == "classement" and secteur and not _plus_precis_que(question, secteur):
        return _sortie("refus", (
            "Il n'existe pas d'indicateur global pour un secteur entier : "
            "agréger plusieurs dimensions en un score unique supposerait une "
            "pondération qu'aucune source ne publie. Précisez l'indicateur."),
            trace, refus="composite")

    # --- une échelle que la plateforme ne sert pas --------------------------
    if _NIVEAU_NON_SERVI.search(cle(question)):
        return _sortie("refus", (
            "La plateforme publie ses données pour les 8 préfectures et "
            "provinces et les 146 communes de la région. Les quartiers, douars, "
            "cercles et arrondissements ne sont pas servis : je ne peux pas "
            "répondre à cette échelle."), trace, refus="niveau_non_servi")

    # --- la mémoire de la conversation --------------------------------------
    # « Et pour Larache ? » ne contient aucun mot d'indicateur : la recherche
    # ne trouve rien et le moteur refusait, alors que l'échange précédent
    # portait sur le taux de chômage. On reprend donc l'indicateur du dernier
    # message dès que la question nomme un territoire sans nommer d'indicateur.
    #
    # La condition est double, et c'est ce qui la rend sûre : sans territoire
    # nommé, la question ne reprend rien du contexte et doit être traitée pour
    # elle-même ; avec un indicateur nommé, c'est lui qui prime.
    indicateur_repris = None
    if (not candidats and noms_cites and etat.get("indicateur_id")
            and quoi in ("valeur", "comparaison")):
        indicateur_repris = etat["indicateur_id"]
        trace["indicateur_repris"] = indicateur_repris

    # --- 2. les gardiens ----------------------------------------------------
    # Les gardiens reçoivent aussi le NOM de l'indicateur retenu : « Population
    # de 7 à 12 ans » porte sa tranche d'âge dans son nom, et « Taux de
    # scolarisation en 2023/2024 » son année scolaire. Sans cette information,
    # ils refusaient des questions qui nommaient exactement l'indicateur voulu.
    tete = candidats[0] if candidats else None
    millesimes = {m["annee"] for m in tete["membres"]} if tete else None
    etiquettes = [m["etiquette"] for m in tete["membres"]] if tete else None
    libelle = tete["nom"] if tete else None
    refus = (garde_temps(question, millesimes, libelle)
             or garde_intention(question, etiquettes, libelle))
    if refus:
        return _sortie("refus", refus["message"], trace, refus=refus["refus"])

    # « C'est quoi le taux de scolarisation à Al Hoceima ? » n'est pas une
    # demande de définition mais une demande de valeur, formulée familièrement.
    # Le repère est le territoire : on ne nomme pas un territoire pour demander
    # ce qu'un indicateur signifie.
    if quoi == "definition" and extraire_territoires(dwh, question):
        trace["intention"] = quoi = "valeur"

    # --- couverture : que sais-tu sur… -------------------------------------
    if quoi == "couverture":
        resultat = lister_indicateurs(dwh, secteur=secteur, niveau=niveau)
        trace["outils"].append({"nom": "lister_indicateurs",
                                "args": {"secteur": secteur, "niveau": niveau}})
        # On passe par le modèle comme les autres branches : le champ `message`
        # des outils contient des consignes destinées au modèle — « ne pas en
        # citer d'autres » — qui n'ont rien à faire sous les yeux d'un
        # utilisateur.
        return _rendre("couverture", question, resultat, trace, etat,
                       modele_actif)

    # À partir d'ici, toutes les intentions ont besoin d'un indicateur.
    if not candidats and not indicateur_repris:
        # Un mot de politesse, aucun indicateur, aucun territoire : il n'y a
        # rien à chercher. « Salut, comment ça va ? » et « Merci beaucoup pour
        # l'info ! » recevaient « cette donnée ne figure pas au catalogue ».
        # Le motif de politesse seul ne suffisait pas — il exigeait que la
        # formule occupe toute la phrase.
        if _POLITESSE_MOT.search(question) and not noms_cites:
            return _sortie("conversation",
                           _bavarder(question, etat) if modele_actif else "",
                           trace)
        # « Vos chiffres viennent du HCP ou d'ailleurs ? », « vos données sur
        # le logement datent de quand ? » : des questions sur les sources en
        # général, sans indicateur précis. Refuser serait absurde — c'est
        # exactement ce que le catalogue sait dire.
        if quoi == "definition":
            resume = lister_indicateurs(dwh, secteur=secteur, niveau=niveau)
            trace["outils"].append({"nom": "lister_indicateurs",
                                    "args": {"secteur": secteur,
                                             "niveau": niveau}})
            return _rendre("definition", question, {
                "libelle": "les données de la plateforme",
                "definition": (
                    "Toutes les données proviennent de sources officielles "
                    "publiées : le Recensement Général de la Population et de "
                    "l'Habitat 2024 du Haut-Commissariat au Plan, la "
                    "Cartographie de la pauvreté multidimensionnelle du HCP, "
                    "la Carte Sanitaire du ministère de la Santé et de la "
                    "Protection Sociale, et l'Annuaire Statistique du Maroc. "
                    "Chaque indicateur porte sa source et son millésime."),
                "couverture": {"phrase": resume.get("message", "")},
            }, trace, etat, modele_actif)
        # NE JAMAIS REFUSER QUAND ON PEUT DEMANDER.
        # « Compare Tétouan et Larache » ne nomme aucun indicateur, mais la
        # question est parfaitement claire par ailleurs : c'est une
        # comparaison, et les deux territoires sont connus. Répondre « cette
        # donnée ne figure pas au catalogue » était un mur ; il manquait
        # seulement une précision, et on la demande.
        if noms_cites or quoi in ("comparaison", "classement"):
            propositions = vedettes(dwh, niveau, k=5)
            noms = ", ".join(f["nom"] for f in propositions)
            sujet = (" pour " + " et ".join(noms_cites)) if noms_cites else ""
            return _sortie("question", (
                f"Sur quel indicateur{sujet} ? Les plus demandés sont : "
                f"{noms}. Vous pouvez aussi me demander ce qui existe pour un "
                f"secteur — démographie, emploi, éducation, santé, conditions "
                f"de vie."), trace,
                attente={"question": question, "type": "indicateur"},
                propositions=[f["nom"] for f in propositions])

        return _sortie("refus", (
            "Cette donnée ne figure pas au catalogue de la plateforme. Je peux "
            "vous dire ce qui existe pour un territoire ou un secteur donné."),
            trace, refus="indicateur")

    indicateur_id = (_membre_demande(candidats[0], question) if candidats
                     else indicateur_repris)
    trace["indicateur"] = indicateur_id

    # --- définition : aucun territoire nécessaire --------------------------
    if quoi == "definition":
        resultat = decrire(dwh, indicateur_id)
        trace["outils"].append({"nom": "decrire",
                                "args": {"indicateur_id": indicateur_id}})
        return _rendre(quoi, question, resultat, trace, etat, modele_actif)

    # --- classement : tous les pairs, aucun territoire à désigner ----------
    if quoi == "classement":
        resultat = classer(dwh, indicateur_id, niveau=niveau)
        trace["outils"].append({"nom": "classer",
                                "args": {"indicateur_id": indicateur_id,
                                         "niveau": niveau}})
        return _rendre(quoi, question, resultat, trace, etat, modele_actif)

    # --- les deux dernières intentions ont besoin de territoires -----------
    # `niveau_force` vient d'une précision déjà donnée par l'utilisateur : il
    # s'applique à TOUS les noms de la question, ce qui règle d'un coup le cas
    # où plusieurs d'entre eux sont ambigus.
    resolus, ambigus = [], []
    for nom in noms_cites:
        r = resoudre_territoire(dwh, nom, niveau_force or niveau_demande(nom))
        trace["outils"].append({"nom": "resoudre_territoire", "args": {"nom": nom}})
        if r["action"] == "demander":
            ambigus.append(r)
        elif r["action"] == "utiliser":
            resolus.append(r["candidats"][0])

    if ambigus:
        # On énonce les choix au lieu de renvoyer la consigne interne de
        # l'outil, et on traite d'un coup TOUS les noms ambigus : demander
        # deux fois de suite la même chose donnait une conversation en boucle.
        noms_ambigus = []
        niveaux_offerts = set()
        for r in ambigus:
            noms_ambigus.append(r["candidats"][0]["nom"].split(" de ")[-1]
                                if " de " in r["candidats"][0]["nom"]
                                else r["candidats"][0]["nom"])
            for c in r["candidats"]:
                niveaux_offerts.add(c["niveau"])

        lisibles = {"commune": "la commune", "prefecture_province": "la province"}
        choix = " ou ".join(lisibles.get(n, n) for n in sorted(niveaux_offerts))
        sujets = " et ".join(dict.fromkeys(noms_ambigus))
        message = (f"« {sujets} » désigne à la fois une commune et une "
                   f"préfecture ou province, et les valeurs y sont très "
                   f"différentes. Souhaitez-vous {choix} ?")
        return _sortie("question", message, trace,
                       attente={"question": question, "type": "niveau"},
                       candidats_territoire=[c["nom"] for r in ambigus
                                             for c in r["candidats"]])

    # --- comparaison --------------------------------------------------------
    if quoi == "comparaison":
        if len(resolus) < 2:
            return _sortie("question", (
                "Quels territoires voulez-vous comparer ? Il en faut au moins "
                "deux, de même niveau."), trace)
        niveaux = {t["niveau"] for t in resolus}
        if len(niveaux) > 1:
            return _sortie("refus", (
                "La comparaison ne se fait qu'entre territoires de même "
                "niveau : comparer une commune à une province mesurerait une "
                "différence de taille, pas une disparité."),
                trace, refus="niveaux")
        resultat = comparer(dwh, [indicateur_id],
                            [t["territoire_id"] for t in resolus])
        trace["outils"].append({"nom": "comparer",
                                "args": {"indicateur_ids": [indicateur_id],
                                         "territoire_ids": [t["territoire_id"]
                                                            for t in resolus]}})
        return _rendre(quoi, question, resultat, trace, etat, modele_actif)

    # --- valeur : un territoire ---------------------------------------------
    if not resolus:
        if etat.get("territoire_id"):          # « et pour Larache ? »
            resolus = [{"territoire_id": etat["territoire_id"],
                        "nom": etat.get("territoire_nom", ""),
                        "niveau": etat.get("niveau")}]
        else:
            return _sortie("question", (
                "De quel territoire s'agit-il ? Précisez une commune, une "
                "préfecture ou une province de la région."), trace)

    territoire = resolus[0]
    etat.update({"territoire_id": territoire["territoire_id"],
                 "territoire_nom": territoire["nom"],
                 "niveau": territoire["niveau"]})

    # Le niveau du territoire retenu peut écarter des candidats : un indicateur
    # publié en province seulement n'a rien à faire dans une réponse communale.
    # S'il ne reste rien, c'est un refus — surtout pas un repli sur la liste
    # non filtrée, qui répondrait une valeur provinciale pour une commune.
    #
    # On ne refait pas cette recherche quand l'indicateur vient de la mémoire :
    # la question ne le nomme pas, donc chercher à nouveau ne rendrait rien.
    if not indicateur_repris:
        candidats = chercher(dwh, question, territoire["niveau"])
        trace["candidats"] = [c["nom"] for c in candidats]
        if not candidats:
            return _sortie("refus", (
                f"Cet indicateur n'est pas publié au niveau "
                f"{'communal' if territoire['niveau'] == 'commune' else 'provincial'}."),
                trace, refus="hors_niveau")
        indicateur_id = _membre_demande(candidats[0], question)

    trace["indicateur"] = indicateur_id
    resultat = lire_valeur(dwh, indicateur_id, territoire["territoire_id"])
    trace["outils"].append({"nom": "lire_valeur",
                            "args": {"indicateur_id": indicateur_id,
                                     "territoire_id": territoire["territoire_id"]}})
    trace["territoire"] = territoire["nom"]
    etat["indicateur_id"] = indicateur_id

    # Les candidats à couverture égale deviennent le « je peux aussi ».
    autres = [c["nom"] for c in candidats[1:4]
              if c["couverture"] == candidats[0]["couverture"]] if candidats else []
    if autres:
        resultat = dict(resultat)
        resultat["message"] = (resultat.get("message", "")
                               + " Autres indicateurs disponibles sur le même "
                                 "sujet : " + ", ".join(autres) + ".")
    return _rendre("valeur", question, resultat, trace, etat, modele_actif)


def _plus_precis_que(question, secteur):
    """La question nomme-t-elle autre chose que le secteur lui-même ?"""
    from .recherche import _racines
    reste = _racines(question) - _racines(secteur) - _racines(
        "quelle quel plus moins faible eleve territoire province commune")
    return bool(reste)


LONGUEUR_DEFINITION_UTILE = 40

# Ce qui, dans une « définition », ne définit rien : les mots de liaison, les
# mentions d'échelle et de millésime, et surtout le vocabulaire de provenance.
# « La base de données excel de la migration — entrees » décrit d'où vient le
# chiffre, pas ce qu'il mesure.
_MOTS_SANS_INFORMATION = set("""
le la les l de des du d un une et ou a au aux en dans pour par sur avec
niveau niveaux commune communes province provinces prefecture region
2014 2020 2021 2022 2023 2024 2025
base donnee donnees excel fichier fichiers export exports feuille onglet csv
tableau tableaux source sources extrait extraction brute brutes
""".split())


def _membre_demande(famille, question):
    """Dans une famille à plusieurs ventilations, celle que la question nomme.

    Une famille réunit les déclinaisons d'un même indicateur : l'étiquette
    entre parenthèses est justement ce qui les distingue — « durée de vie »,
    « 5 ans », « 10 ans ». Le premier membre était pris d'office, ce qui ne se
    voyait pas tant que les déclinaisons partageaient une définition commune.
    Depuis que les trois horizons migratoires ont chacun leur dénominateur, le
    premier membre serait une réponse fausse : l'indice de sorties à cinq ans
    se rapporte aux résidents d'il y a cinq ans, celui de durée de vie aux
    natifs.

    Quand la question ne nomme aucune étiquette, on garde le premier membre :
    le comportement antérieur est intact.
    """
    membres = famille["membres"]
    if len(membres) == 1:
        return membres[0]["indicateur_id"]
    demandes = _racines(question)
    meilleur, score_max = membres[0], 0
    for m in membres:
        etiquette = _racines(m["etiquette"] or "")
        commun = len(etiquette & demandes)
        if etiquette and commun > score_max:
            meilleur, score_max = m, commun
    return meilleur["indicateur_id"]


def _definition_redigee(definition, libelle):
    """La définition dit-elle quelque chose de plus que le libellé ?

    La colonne `definition` du catalogue n'est pas toujours une définition.
    Selon l'indicateur elle contient une vraie explication, une note de
    provenance (« la base de données excel de la migration »), ou le nom brut
    de la colonne d'origine (« temp_moyenne »).

    On ne cherche pas à classer les 254 définitions : trois tentatives de
    classement automatique ont échoué, aucune règle générale ne sépare
    proprement ces trois cas. On tranche donc AU MOMENT DE RÉPONDRE, sur une
    règle simple et vérifiable : une fois retirés le libellé, le thème, la
    traçabilité et les mentions de niveau, reste-t-il assez de texte pour
    apprendre quelque chose ?

    Mieux vaut dire « aucune définition rédigée » que renvoyer un nom de
    colonne en guise d'explication.
    """
    if not definition:
        return None
    texte = re.split(r"\[Traçabilité", definition, flags=re.S)[0]
    texte = re.sub(r"Thème\s*:\s*[\w_]+\.?", "", texte)
    texte = re.sub(r"Renommé\s*:.*", "", texte, flags=re.S)
    texte = " ".join(texte.split()).strip(" .")
    if not texte:
        return None

    # Un identifiant technique n'est pas une phrase.
    if "_" in texte or " " not in texte:
        return None

    # On soustrait MOT À MOT, et non d'un seul tenant : « Taux de pauvreté
    # (incidence H). Niveaux commune et province, 2024 » ne contient pas le
    # libellé d'affilée, puisque la mention des niveaux s'intercale.
    reste = set(cle(texte).split())
    reste -= set(cle(libelle or "").split())
    reste -= _MOTS_SANS_INFORMATION
    return texte if sum(len(m) for m in reste) >= LONGUEUR_DEFINITION_UTILE else None


def _faits(branche, resultat):
    """Met en forme, pour le modèle, TOUT ce dont il a besoin — et rien d'autre.

    Une première version ne lui transmettait que le champ `message` des outils.
    Or ce champ porte des CONSIGNES (« citer la source », « classement par
    valeur croissante ») sans porter les DONNÉES correspondantes. Sommé de
    citer une source qu'il n'avait pas reçue, le modèle en a inventé trois :
    « Décision du Gouvernement Marocain », « INSEE », et un texte à trous.

    La règle qui en découle : on ne demande jamais au modèle de citer quelque
    chose qu'on ne lui a pas donné. Chaque élément exigé par la consigne doit
    figurer, littéralement, dans les faits.
    """
    lignes = []

    def ajouter(cle, valeur):
        if valeur not in (None, "", [], {}):
            lignes.append(f"{cle} : {valeur}")

    ajouter("Indicateur", resultat.get("libelle"))
    ajouter("Unité", resultat.get("unite"))
    ajouter("Millésime", resultat.get("millesime"))
    ajouter("Source", resultat.get("source"))

    if branche == "valeur":
        ajouter("Territoire", resultat.get("territoire"))
        ajouter("Valeur", resultat.get("valeur_lisible"))
        if resultat.get("absence"):
            ajouter("Absence", resultat["absence"])
        vent = (resultat.get("ventilation") or {}).get("choisie")
        ajouter("Ventilation retenue", vent)

    elif branche == "classement":
        ajouter("Niveau", resultat.get("niveau"))
        classement = resultat.get("classement") or []
        if classement:
            # On NE demande PAS au modèle d'interpréter l'ordre du classement.
            # « classer » trie du plus favorable au moins favorable, et ce que
            # « favorable » veut dire dépend du sens de l'indicateur : pour le
            # chômage, le rang 1 est la valeur la plus BASSE. Le modèle a lu
            # « 1. Tanger-Assilah » et répondu que c'était la province au
            # chômage le plus élevé — l'inverse de la vérité.
            # On lui donne donc les extrêmes nommés, sans rien à déduire.
            avec_valeur = [c for c in classement if c.get("valeur") is not None]
            if avec_valeur:
                haut = max(avec_valeur, key=lambda c: c["valeur"])
                bas = min(avec_valeur, key=lambda c: c["valeur"])
                lignes.append(f"Valeur la plus élevée : {haut['nom']} — "
                              f"{haut['valeur_lisible']}")
                lignes.append(f"Valeur la plus basse : {bas['nom']} — "
                              f"{bas['valeur_lisible']}")
            lignes.append("Liste complète, du plus favorable au moins favorable "
                          "selon le sens de l'indicateur :")
            for c in classement:
                lignes.append(f"  {c['rang']}. {c['nom']} — {c['valeur_lisible']}")
        ajouter("Territoires sans valeur", ", ".join(
            resultat.get("non_renseignes") or []))

    elif branche == "comparaison":
        for t in resultat.get("territoires") or []:
            lignes.append(f"  {t.get('nom')} — {t.get('valeur_lisible')}")
        ajouter("Écart", resultat.get("ecart"))
        ajouter("En tête", resultat.get("en_tete"))

    elif branche == "definition":
        ajouter("Secteur", resultat.get("secteur"))
        redigee = _definition_redigee(resultat.get("definition"),
                                      resultat.get("libelle"))
        if redigee:
            ajouter("Définition", redigee)
        else:
            # Le catalogue porte souvent, à la place d'une définition, le nom
            # de la colonne d'origine ou une note de provenance. Rendre cela
            # au modèle revient à lui donner une phrase à finir : il a répondu
            # « le taux de pauvreté en 2024 était de (source) », faute d'avoir
            # une valeur — alors que la question n'en demandait aucune.
            lignes.append("Définition : aucune définition rédigée dans le "
                          "catalogue pour cet indicateur")
        ajouter("Traçabilité", resultat.get("tracabilite"))
        ajouter("Publication", (resultat.get("couverture") or {}).get("phrase"))

    elif branche == "couverture":
        # lister_indicateurs rend des lignes du catalogue : la clé est
        # `libelle_court`, pas `libelle`. Avec la mauvaise clé les faits
        # étaient presque vides et le modèle comblait le silence.
        ajouter("Nombre d'indicateurs disponibles", resultat.get("nombre"))
        for secteur, n in (resultat.get("par_secteur") or {}).items():
            lignes.append(f"  {secteur} : {n}")
        liste = resultat.get("indicateurs") or []
        for i in liste[:20]:
            nom = i.get("libelle_court") if isinstance(i, dict) else str(i)
            lignes.append(f"  - {nom}")
        if len(liste) > 20:
            lignes.append(f"  … et {len(liste) - 20} autres")
        ailleurs = resultat.get("aussi_disponible")
        if ailleurs:
            niveau = ("communal" if ailleurs.get("niveau") == "commune"
                      else "provincial")
            lignes.append(f"Aucun à ce niveau, mais {ailleurs.get('nombre')} "
                          f"existent au niveau {niveau}")

    # Le sens de l'indicateur, quand il en a un : un dénombrement n'est ni bon
    # ni mauvais, et le modèle ne doit pas le commenter comme s'il l'était.
    sens = resultat.get("sens")
    if isinstance(sens, dict):
        ajouter("Lecture du sens", sens.get("lecture"))
    elif sens:
        ajouter("Sens", sens)

    return "\n".join(lignes)


def _brouillon(branche, resultat):
    """La réponse écrite en Python — correcte, complète, publiable telle quelle.

    C'est elle qui porte la vérité. Le modèle n'interviendra ensuite que pour
    la rendre naturelle, et sa version sera rejetée si elle s'en écarte.

    Pourquoi ce renversement : les branches où le modèle échouait sont
    exactement celles où les faits ne sont pas une valeur unique — une liste
    (classement, couverture) ou une absence (définition). Pour un chiffre seul
    il rédige bien ; pour le reste il copie la fiche de travail, ou pire, il
    comble. Sur « que sais-tu sur la santé au niveau communal ? », dont les
    faits ne contiennent AUCUN chiffre, il a répondu « 7,5 % ».
    """
    src = resultat.get("source")
    fin = f" (Source : {src})" if src else ""
    lib = resultat.get("libelle") or "cet indicateur"
    an = resultat.get("millesime")
    # « Population légale (2024) … en 2024 » : le libellé porte déjà le
    # millésime pour les indicateurs déclinés par année. On ne le répète pas.
    quand = f" en {an}" if an and str(an) not in lib else ""

    if branche == "valeur":
        absence = resultat.get("absence")
        terr = resultat.get("territoire") or "ce territoire"
        if absence == "hors_niveau":
            return f"{lib} n'est pas publié à ce niveau territorial."
        if absence == "non_renseigne":
            return (f"{lib} n'est pas renseigné pour {terr}{quand} : "
                    f"la donnée est publiée à cette échelle, mais cette "
                    f"valeur-là manque.{fin}")
        return f"{lib} pour {terr}{quand} : {resultat.get('valeur_lisible')}.{fin}"

    if branche == "classement":
        c = [x for x in (resultat.get("classement") or [])
             if x.get("valeur") is not None]
        if not c:
            return f"Aucune valeur classable pour {lib}{quand}."
        haut = max(c, key=lambda x: x["valeur"])
        bas = min(c, key=lambda x: x["valeur"])
        phrase = (f"{lib}{quand} : la valeur la plus élevée est celle de "
                  f"{haut['nom']} ({haut['valeur_lisible']}), la plus basse "
                  f"celle de {bas['nom']} ({bas['valeur_lisible']}), "
                  f"sur {len(c)} territoires.")
        absents = resultat.get("non_renseignes") or []
        if absents:
            phrase += (f" {len(absents)} territoire(s) sans valeur, écarté(s) "
                       f"du classement : {', '.join(absents)}.")
        return phrase + fin

    if branche == "comparaison":
        # comparer() range les valeurs dans indicateurs[…]["cases"], et non
        # dans "territoires" qui ne porte que les noms. Lire la mauvaise
        # structure produisait « Population de la commune de Tétouan None ».
        lignes_ind = resultat.get("indicateurs") or []
        if not lignes_ind:
            return resultat.get("message") or "Rien à comparer."
        ind = lignes_ind[0]
        src_i = ind.get("source")
        fin_i = f" (Source : {src_i})" if src_i else ""
        an_i = ind.get("millesime")
        quand_i = (f" en {an_i}" if an_i and str(an_i) not in (ind.get("libelle") or "")
                   else "")

        parts, absents = [], []
        for c in ind.get("cases") or []:
            if c.get("valeur_lisible") is not None:
                parts.append(f"{c['nom']} {c['valeur_lisible']}")
            else:
                absents.append(c["nom"])
        if len(parts) < 2:
            return (f"{ind.get('libelle')} : moins de deux territoires "
                    f"renseignés, il n'y a rien à comparer.{fin_i}")

        phrase = f"{ind.get('libelle')}{quand_i} — " + ", ".join(parts) + "."
        if ind.get("ecart_lisible"):
            phrase += f" Écart de {ind['ecart_lisible']}."
        # On ne désigne un mieux placé que si l'indicateur a un sens. Un
        # dénombrement n'est ni bon ni mauvais.
        if ind.get("en_tete"):
            phrase += f" {ind['en_tete']} est le mieux placé."
        if absents:
            phrase += f" Sans valeur : {', '.join(absents)}."
        return phrase + fin_i

    if branche == "definition":
        redigee = _definition_redigee(resultat.get("definition"), lib)
        publication = (resultat.get("couverture") or {}).get("phrase") or ""
        if redigee:
            # Le point final : `_definition_redigee` retire la ponctuation de
            # fin pour pouvoir accoler la source. Tant que le modèle
            # reformulait, on ne voyait que sa phrase à lui ; depuis que ce
            # brouillon EST la réponse, « … du taux d'activité (Source : … ) »
            # se lirait sans point.
            return f"{redigee}.{fin}" if not redigee.endswith(".") \
                   else f"{redigee}{fin}"
        return (f"Le catalogue ne comporte pas de définition rédigée pour "
                f"« {lib} ». Il est exprimé en "
                f"{resultat.get('unite') or 'unité non précisée'}, millésime "
                f"{an or 'non précisé'}"
                f"{', publié ' + publication if publication else ''}.{fin}")

    if branche == "couverture":
        liste = resultat.get("indicateurs") or []
        n = resultat.get("nombre") or len(liste)
        if not n:
            ailleurs = resultat.get("aussi_disponible")
            if ailleurs:
                niveau = ("communal" if ailleurs.get("niveau") == "commune"
                          else "provincial")
                return (f"Aucun indicateur à ce niveau, mais "
                        f"{ailleurs.get('nombre')} existent au niveau {niveau}.")
            return "Aucun indicateur disponible pour cette demande."
        noms = [i.get("libelle_court") if isinstance(i, dict) else str(i)
                for i in liste[:8]]
        suite = f", et {len(liste) - 8} autres" if len(liste) > 8 else ""
        return (f"{n} indicateur(s) disponible(s) : "
                + ", ".join(noms) + suite + ".")

    return resultat.get("message") or ""


_NOMBRE = re.compile(r"\d[\d  ]*(?:[.,]\d+)?")


def _chiffres(texte):
    """Les nombres d'un texte, normalisés pour être comparables."""
    return {m.group(0).replace(" ", "").replace(" ", "").replace(",", ".")
            .rstrip(".")
            for m in _NOMBRE.finditer(texte or "")}


# Les mots par lesquels une reformulation cesse de reformuler et se met à
# interpréter. Sur « Population de Tétouan 611 928, de Larache 510 211 », le
# modèle a ajouté « soulignent l'équilibre démographique entre les deux
# territoires » : un commentaire que rien dans les faits n'autorise, et qu'une
# vérification portant sur les seuls chiffres ne pouvait pas voir.
# Les verbes sont écrits par leur RADICAL, suivi d'une terminaison libre :
# « soulignant » passait à travers « souligne|soulignent », et c'est
# exactement la forme que le modèle a employée en production. Énumérer les
# conjugaisons une à une, c'est la liste qui ne finit jamais — le signal est
# le radical.
_INTERPRETATION = re.compile(
    r"\b(soulign\w*|montre(?:nt)? que|indique(?:nt)? une|"
    r"r[ée]v[èeé]l\w*|traduit une|t[ée]moign\w*|signifie que|s'explique par|"
    r"[ée]quilibre|d[ée]s[ée]quilibre|tendance|dynamique favorable|"
    r"inqui[ée]tant|pr[ée]occupant|encourageant|satisfaisant|"
    r"il faut|il faudrait|on peut conclure|cela sugg[èe]re)\b", re.I)


def _verifier(brouillon, phrase):
    """La reformulation a-t-elle respecté le brouillon ?

    Trois motifs de rejet, du plus grave au moins grave :

      - un nombre ABSENT du brouillon est apparu : c'est une invention, et elle
        est indétectable à l'œil sur des centaines de réponses ;
      - un nombre du brouillon a disparu : perte d'information ;
      - un mot d'INTERPRÉTATION est apparu : le modèle ne reformule plus, il
        commente. La plateforme restitue des valeurs ; le commentaire appartient
        à celui qui les lit.

    En cas de rejet, on sert le brouillon : moins élégant, toujours exact.
    """
    if not phrase.strip():
        return False, "réponse vide"
    attendus, obtenus = _chiffres(brouillon), _chiffres(phrase)
    inventes = obtenus - attendus
    perdus = attendus - obtenus
    if inventes:
        return False, f"chiffre inventé : {', '.join(sorted(inventes))}"
    if perdus:
        return False, f"chiffre perdu : {', '.join(sorted(perdus))}"
    ajoute = _INTERPRETATION.search(phrase)
    if ajoute and not _INTERPRETATION.search(brouillon):
        return False, f"interprétation ajoutée : « {ajoute.group(0)} »"
    return True, None


def _rendre(branche, question, resultat, trace, etat, modele_actif):
    trace["millesime"] = resultat.get("millesime")
    trace["source"] = resultat.get("source")
    trace["valeur"] = resultat.get("valeur_lisible")
    # Pour une comparaison, millésime et source vivent dans le premier
    # indicateur : le niveau supérieur ne porte que le décompte des territoires.
    if branche == "comparaison" and (resultat.get("indicateurs") or []):
        premier = resultat["indicateurs"][0]
        trace["millesime"] = premier.get("millesime")
        trace["source"] = premier.get("source")

    brouillon = _brouillon(branche, resultat)
    trace["brouillon"] = brouillon
    trace["faits"] = _faits(branche, resultat)

    if not modele_actif:
        return _sortie(branche, brouillon, trace)

    # UNE DÉFINITION NE SE REFORMULE PAS.
    #
    # Ailleurs, le brouillon est une phrase mécanique assemblée en Python à
    # partir de champs : « Taux de chômage pour Al Hoceima : 24,6 %. » Le
    # modèle lui rend une tournure naturelle, et c'est son seul emploi utile.
    #
    # Une définition, elle, est déjà de la prose : elle a été écrite mot à
    # mot, avec ses mises en garde, et c'est justement sur ces mises en garde
    # que la reformulation dérape. Constaté en production : à « l'indice de
    # sorties est rapporté à la population qui résidait là cinq ans
    # auparavant », le modèle a ajouté « tandis que cet indice est rapporté à
    # la population totale » — une phrase fausse, qui contredisait la
    # précédente dans la même réponse. Aucun chiffre n'avait bougé, la
    # vérification n'avait donc rien vu.
    #
    # Reformuler une définition, c'est réécrire une source. C'est le même
    # interdit que recalculer une valeur, et le gain est nul : le texte de
    # départ est déjà lisible. En prime, la réponse devient immédiate là où
    # elle demandait trente à quarante-cinq secondes.
    if branche == "definition":
        trace["reformulation"] = "non sollicitée — texte de source"
        return _sortie(branche, brouillon, trace)

    phrase = _rediger(question, brouillon)
    accepte, motif = _verifier(brouillon, phrase)
    trace["reformulation"] = "acceptée" if accepte else f"rejetée — {motif}"
    return _sortie(branche, phrase if accepte else brouillon, trace)


# --------------------------------------------------------------------------
# 5. Le modèle — il rédige, il ne décide pas
# --------------------------------------------------------------------------

# La consigne est volontairement COURTE. Une version plus longue, avec six
# règles dont quatre négatives, a rendu le modèle nettement moins bon : il
# s'est mis à recopier la fiche de travail au lieu de rédiger, à écrire le mot
# « Source » littéralement, et une fois à inventer un pourcentage. Un petit
# modèle suit mal les interdictions ; il suit bien un exemple et une tâche
# simple.
CONSIGNE = (
    "Tu es l'assistant de l'Observatoire régional de Tanger-Tétouan-Al Hoceïma.\n"
    "On te donne une réponse déjà rédigée et exacte. Reformule-la en une "
    "phrase naturelle en français.\n"
    "Garde tous les chiffres, tous les noms de territoires et la source à "
    "l'identique. N'ajoute rien."
)

CONSIGNE_BAVARDAGE = (
    "Tu es l'assistant de l'Observatoire régional de Tanger-Tétouan-Al Hoceïma.\n"
    "Réponds en UNE phrase, poliment et brièvement.\n"
    "Tu donnes des indicateurs territoriaux officiels — démographie, emploi, "
    "éducation, santé, conditions de vie — pour les 8 préfectures et provinces "
    "et les 146 communes de la région.\n"
    "N'écris aucun chiffre. Ne t'excuse pas. Ne mentionne pas ce que tu ne "
    "peux pas faire."
)

# Une salutation seule n'a pas besoin du modèle : la réponse est toujours la
# même, et vingt secondes d'attente pour dire bonjour sont vingt secondes de
# trop. Le modèle reste utile pour les questions sur l'assistant lui-même,
# qui varient.
_REPONSES_FIXES = {
    "bonjour": "Bonjour. Que souhaitez-vous savoir sur la région ?",
    "bonsoir": "Bonsoir. Que souhaitez-vous savoir sur la région ?",
    "salut": "Bonjour. Que souhaitez-vous savoir sur la région ?",
    "coucou": "Bonjour. Que souhaitez-vous savoir sur la région ?",
    "merci": "Je vous en prie. Une autre question ?",
    "merci beaucoup": "Je vous en prie. Une autre question ?",
    "au revoir": "Au revoir.",
    "ok": "Une autre question ?",
    "d'accord": "Une autre question ?",
}


def _appeler(consigne, contenu):
    import ollama
    reponse = ollama.chat(
        model=MODELE,
        messages=[{"role": "system", "content": consigne},
                  {"role": "user", "content": contenu}],
        keep_alive=GARDE_EN_MEMOIRE,
        options={"num_predict": PLAFOND_JETONS, "temperature": 0.2},
    )
    return (reponse["message"].get("content") or "").strip()


def _rediger(question, brouillon):
    return _appeler(CONSIGNE,
                    f"Question posée : {question}\n\nRéponse à reformuler :\n{brouillon}")


def _bavarder(question, etat):
    fixe = _REPONSES_FIXES.get(question.strip().lower().rstrip("!.? "))
    if fixe:
        return fixe

    rappel = ""
    if etat.get("territoire_nom"):
        rappel = (f"\n(La dernière réponse portait sur {etat['territoire_nom']}. "
                  f"Si la personne demande confirmation, renvoie-la vers la "
                  f"source citée, sans changer le chiffre.)")
    return _appeler(CONSIGNE_BAVARDAGE, question + rappel)
