"""
Les gardiens du refus : ce que la recherche d'indicateur ne peut pas voir.

POURQUOI CE FICHIER EXISTE
« Quel est le taux de chômage à Marrakech ? » désigne un indicateur qui EXISTE.
« Quelle sera la population en 2030 ? » aussi. « Calcule la moyenne pondérée du
chômage et de la pauvreté » aussi. Dans les trois cas, la recherche trouve —
et elle a raison de trouver. Ce n'est pas l'indicateur qui pose problème.

Le refus se partage donc entre quatre gardiens :

    indicateur   l'indicateur existe-t-il ?         -> recherche.chercher()
    territoire   est-il servi par la plateforme ?   -> outils.resoudre_territoire()
    temps        le millésime existe-t-il ?         -> ce fichier
    intention    demande-t-on un calcul, un score ? -> ce fichier

Chacun répond à une question différente, et aucun ne peut faire le travail
d'un autre. C'est ce partage qui permet à l'assistant de dire POURQUOI il
refuse, au lieu d'un « je ne dispose pas de cette information » qui effacerait
la distinction entre « ça n'existe pas », « ce n'est pas publié à ce niveau »
et « je ne fais pas ce calcul ».

AUCUN DE CES CONTRÔLES N'APPELLE LE MODÈLE.
Ils s'exécutent en quelques microsecondes, avant toute inférence. Une question
refusée ici ne coûte rien et ne peut rien inventer.
"""

import re
import unicodedata
from datetime import date


def _sans_accents(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# --------------------------------------------------------------------------
# Gardien du temps
# --------------------------------------------------------------------------

# Une année à quatre chiffres, plausible pour une statistique territoriale.
_ANNEE = re.compile(r"\b(19\d{2}|20\d{2})\b")

# Marques de futur ou de projection. « va se développer », « dans dix ans ».
_FUTUR = re.compile(
    r"\b(sera|seront|serait|va\s+\w+er|vont\s+\w+er|projection|projections|"
    r"previsions?|prevoir|prevois|d'?ici|prochaine?s?\s+(annees?|mois)|"
    # « dans dix ans » autant que « dans 10 ans » : les gens écrivent les
    # petits nombres en toutes lettres.
    r"dans\s+(\d+|un|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|"
    r"quinze|vingt|trente)\s+ans?|"
    r"evoluera|augmentera|diminuera|futur|a\s+l'?avenir)\b")


def garde_temps(question, millesimes_disponibles=None, libelle=None):
    """
    Le millésime demandé est-il disponible ?

    Renvoie None si la question ne pose aucun problème de temps, sinon un
    dictionnaire décrivant le refus et sa raison.

    `millesimes_disponibles` est l'ensemble des millésimes de la famille
    retenue — par exemple {'2014', '2024'}. Quand il n'est pas fourni, seule
    la projection est détectée.

    `libelle` est le nom de l'indicateur. Il compte : « Taux de scolarisation
    des 6-11 ans en 2023/2024 » porte son année scolaire dans son nom, alors
    que sa colonne `annee` vaut 2024. Sans lui, la question qui reprenait cette
    année scolaire était refusée pour un millésime qu'elle contenait pourtant.
    """
    texte = _sans_accents(question)

    if _FUTUR.search(texte):
        return {
            "refus": "projection",
            "message": ("Cette plateforme ne restitue que des données publiées. "
                        "Elle ne produit ni projection ni prévision."),
        }

    annees = set(_ANNEE.findall(texte))
    if not annees:
        return None

    # Une année postérieure au dernier millésime connu est une projection,
    # même formulée au passé : « le chômage en 2027 » n'existe pas.
    if any(int(a) > date.today().year for a in annees):
        return {
            "refus": "projection",
            "message": ("L'année demandée est à venir : la plateforme ne "
                        "restitue que des données déjà publiées."),
        }

    if millesimes_disponibles is None:
        return None

    # Un millésime peut être une période : « 2023-2024 » couvre 2023 et 2024.
    # Le nom de l'indicateur compte aussi : « … en 2023/2024 » annonce une
    # année scolaire que la colonne `annee` réduit à 2024.
    couverts = set()
    for m in list(millesimes_disponibles) + [libelle or ""]:
        bornes = _ANNEE.findall(str(m))
        if len(bornes) == 2:
            couverts.update(str(a) for a in range(int(bornes[0]), int(bornes[1]) + 1))
        else:
            couverts.update(bornes)

    manquantes = sorted(annees - couverts)
    if manquantes and couverts:
        return {
            "refus": "millesime",
            "annees_demandees": manquantes,
            "annees_disponibles": sorted(couverts),
            "message": (f"Aucune donnée pour {', '.join(manquantes)}. "
                        f"Millésime(s) disponible(s) : {', '.join(sorted(couverts))}."),
        }
    return None


# --------------------------------------------------------------------------
# Gardien de l'intention
# --------------------------------------------------------------------------

# Un calcul demandé explicitement. La plateforme restitue des valeurs
# publiées ; elle n'en fabrique pas de nouvelles.
_CALCUL = re.compile(
    r"\b(calcule|calculer|moyenne\s+ponderee|ponderation|ponderer|"
    r"somme\s+de|additionne|multiplie|combine|agrege|agreger)\b")

# Agréger PLUSIEURS TERRITOIRES en une seule grandeur est un calcul, même
# quand aucun verbe ne le dit : « la moyenne du chômage des 8 provinces »
# demande un nombre que personne n'a publié.
#
# Le mot « moyenne » ne suffit pas à le reconnaître, et c'est tout le piège :
# « température moyenne », « humidité relative moyenne », « distance moyenne
# des logements » sont des NOMS d'indicateurs. Les refuser sur ce seul mot
# écartait cinq questions parfaitement légitimes du jeu d'évaluation.
#
# Le signal est la conjonction des deux : un mot d'agrégation ET une portée
# territoriale au pluriel. C'est cette conjonction qui est exigée ici.
_AGREGAT = re.compile(
    r"\b(moyenne|mediane|total|cumul|somme|ensemble)\b")

_PORTEE_MULTIPLE = re.compile(
    r"\b(des|de\s+(?:tous|toutes)\s+les|pour\s+(?:tous|toutes)\s+les|"
    r"sur\s+(?:tous|toutes)\s+les|par)\s+"
    r"(\d+\s+)?(provinces|prefectures|communes|territoires|villes)\b"
    r"|\b(regionale?|de\s+la\s+region|au\s+niveau\s+regional)\b")


def _agregation_entre_territoires(texte):
    return bool(_AGREGAT.search(texte) and _PORTEE_MULTIPLE.search(texte))

# « Comment est calculé le taux d'analphabétisme ? » demande une EXPLICATION,
# pas un calcul. Le gardien refusait la question qui interroge la méthode.
# On énumère les formes de la question sur la méthode plutôt que ses
# conjugaisons : « comment calcule-t-on », « comment est calculé »,
# « de quelle manière ». Le trait d'union de l'inversion sujet-verbe fait
# partie du mot pour l'expression régulière — d'où le \w*[- ]?t?[- ]?on.
_QUESTION_SUR_LA_METHODE = re.compile(
    r"\b(comment (est|sont|a ete|ont ete|se) \w+|comment on |"
    r"comment calcul\w*|calcul\w*[- ]t[- ]on|comment (l'|le |la )?obtient|"
    r"sur quoi|selon quelle|quelle methode|methodologie|"
    r"de quelle (maniere|facon)|que (mesure|represente)|"
    r"que veut dire|c'est quoi|definition)\b")

# Un jugement global, c'est-à-dire un indicateur composite : agréger plusieurs
# dimensions en un score unique. C'est précisément l'approche abandonnée en
# cours de projet, faute de pondération défendable.
_COMPOSITE = re.compile(
    r"\b(meilleure?s?|pires?|plus\s+developpee?s?|moins\s+developpee?s?|"
    r"niveau\s+de\s+developpement|score\s+global|indice\s+global|"
    r"note\s+globale|classement\s+general)\b")

# Une tranche d'âge nommée dans la question : « les 15 à 24 ans », « 15-24 ».
_TRANCHE_AGE = re.compile(r"\b(\d{1,2})\s*(?:a|-|et)\s*(\d{1,2})\s*ans?\b")


def garde_intention(question, ventilations_disponibles=None, libelle=None):
    """
    La question demande-t-elle autre chose qu'une lecture ?

    Renvoie None si tout va bien, sinon un dictionnaire décrivant le refus.

    `ventilations_disponibles` est la liste des étiquettes de la famille
    retenue — « Masculin », « Féminin », « 0-4 ans »… Elle permet de détecter
    qu'une tranche d'âge est demandée alors qu'elle n'est pas publiée.

    `libelle` est le nom de l'indicateur retenu. Il est nécessaire : « Population
    de 7 à 12 ans » EST un indicateur, la tranche d'âge est dans son nom et non
    dans une ventilation. Sans ce contrôle, la question « Population de 7 à 12
    ans dans la commune de Bni Said ? » était refusée au motif que l'indicateur
    n'est pas ventilé par âge — alors qu'elle nommait exactement l'indicateur
    voulu.
    """
    texte = _sans_accents(question)

    # Demander COMMENT une chose est calculée n'est pas demander un calcul.
    if _QUESTION_SUR_LA_METHODE.search(texte):
        return None

    if _CALCUL.search(texte) or _agregation_entre_territoires(texte):
        return {
            "refus": "calcul",
            "message": ("La plateforme restitue des valeurs publiées et n'en "
                        "calcule pas de nouvelles. Je peux en revanche donner "
                        "chaque valeur séparément, avec sa source."),
        }

    if _COMPOSITE.search(texte):
        return {
            "refus": "composite",
            "message": ("Il n'existe pas d'indicateur global de développement "
                        "ni de classement général : agréger plusieurs "
                        "dimensions en un score unique supposerait une "
                        "pondération qui n'est publiée par aucune source. "
                        "Précisez l'indicateur qui vous intéresse."),
        }

    tranche = _TRANCHE_AGE.search(texte)
    if tranche and ventilations_disponibles is not None:
        demandee = f"{tranche.group(1)}-{tranche.group(2)}"
        connues = " ".join(_sans_accents(v) for v in ventilations_disponibles)
        # La tranche peut être dans le NOM de l'indicateur plutôt que dans une
        # ventilation : « Population de 7 à 12 ans » est un indicateur entier.
        # On accepte les deux écritures, « 7-12 » et « 7 à 12 ».
        dans_le_nom = _sans_accents(libelle or "")
        ecritures = (demandee,
                     f"{tranche.group(1)} a {tranche.group(2)}",
                     f"{tranche.group(1)} et {tranche.group(2)}")
        if any(e in dans_le_nom for e in ecritures):
            return None
        if demandee not in connues:
            return {
                "refus": "ventilation",
                "tranche_demandee": demandee,
                "message": (f"Cet indicateur n'est pas ventilé par tranche "
                            f"d'âge ; la tranche {demandee} ans n'est pas "
                            f"publiée séparément."),
            }
    return None
