"""
Les constantes partagées par l'application et l'assistant.

Elles vivent ici et nulle part ailleurs. Deux définitions de « ce qui existe »
finissent toujours par diverger, et le jour où cela arrive, l'assistant promet
des indicateurs que l'interface ne sait pas montrer.
"""

# Les secteurs publiés. Le catalogue en contient d'autres — « non
# cartographiable », « hors secteur », « Santé — répertoires » — qui décrivent
# des données conservées mais non servies.
SECTEURS = ["Démographie", "Emploi", "Éducation", "Santé", "Conditions de vie"]

# Les niveaux territoriaux où des indicateurs sont publiés.
NIVEAUX = ["prefecture_province", "commune"]


# --------------------------------------------------------------------------
# Les familles d'indicateurs
#
# Le catalogue compte 254 lignes publiées, mais seulement 109 notions : « Type
# de logement » en occupe 6, « Âge quinquennal » 16. Ce sont des déclinaisons
# d'un même indicateur, pas des indicateurs différents.
#
# Ce regroupement sert à la fiche ET à la recherche de l'assistant. Il vit donc
# ici : deux implémentations finiraient par diverger, et le jour où cela
# arrive, l'assistant et l'écran ne parlent plus du même indicateur.
# --------------------------------------------------------------------------

import re

# Une parenthèse en fin de libellé, courte, sans parenthèse imbriquée :
# c'est une déclinaison, pas une précision rédactionnelle.
_PARENTHESE = re.compile(r"^(.*?)\s*\(([^()]{1,39})\)\s*$")


def cle_famille(libelle: str, secteur: str):
    """Rend (clé, type, étiquette du membre) pour un indicateur.

    La clé porte le secteur en plus du nom : « Privation » existe en Santé,
    en Éducation et en Conditions de vie, et ce sont trois familles.
    """
    if " — " in libelle:
        tete, membre = libelle.split(" — ", 1)
        return (secteur, tete.strip()), "modalite", membre.strip()

    trouve = _PARENTHESE.match(libelle)
    if trouve:
        return (secteur, trouve.group(1).strip()), "ventilation", trouve.group(2).strip()

    return (secteur, libelle), "seul", libelle


def millesime_famille(annees):
    """Le millésime affiché par une famille, déduit de ses membres.

    La colonne `annee` porte la période de référence d'UNE ligne : une année
    civile (2024), une année scolaire (2023-2024) ou une moyenne pluriannuelle
    (2020-2024). Une famille peut donc réunir plusieurs millésimes.

    Le séparateur est un point médian, jamais un tiret : « 2020-2024 » signifie
    déjà « moyenne calculée sur la période ». Écrire « 2014-2024 » laisserait
    croire qu'on possède les années intermédiaires, alors qu'on n'a que deux
    points de mesure.
    """
    distinctes = sorted({str(a).strip() for a in annees if str(a).strip()})
    if not distinctes:
        return None
    if len(distinctes) == 1:
        return distinctes[0]
    return " · ".join(distinctes)