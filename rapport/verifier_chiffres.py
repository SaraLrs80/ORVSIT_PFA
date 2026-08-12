"""
Confronter les chiffres du rapport à la donnée.

POURQUOI
Un rapport technique se juge d'abord sur ses chiffres. Un jury qui trouve une
incohérence entre deux pages cesse de faire confiance au reste, y compris à
ce qui est juste. Le catalogue ayant changé pendant la réalisation, chaque
décompte cité doit être revérifié sur l'état livré.

CE QUE FAIT CE SCRIPT
Il mesure les grandeurs vérifiables sur les fichiers du dossier de
préparation et sur le code, puis les cherche dans le texte du rapport. Il
signale ce qui ne concorde pas et ce qu'il n'a pas trouvé.

Il ne modifie rien.

    python verifier_chiffres.py
"""

import csv
import os
import re
import zipfile

RACINE = os.path.dirname(os.path.abspath(__file__))
PROJET = os.path.dirname(RACINE)
STAGE = os.path.dirname(PROJET)
PIPELINE = os.path.join(PROJET, "data-pipeline")
RAPPORT = os.path.join(STAGE, "rapport_stage1_v6.docx")

SECTEURS = ("Démographie", "Emploi", "Éducation", "Santé", "Conditions de vie")


def _vrai(v):
    return str(v).strip() == "True"


def mesurer():
    """Les grandeurs telles qu'elles sont, aujourd'hui, dans les fichiers."""
    with open(os.path.join(PIPELINE, "dim_indicateur.csv"),
              encoding="utf-8-sig") as f:
        cat = list(csv.DictReader(f))
    with open(os.path.join(PIPELINE, "dim_territoire.csv"),
              encoding="utf-8-sig") as f:
        terr = list(csv.DictReader(f))

    # Le filtre de l'application : secteur servi, disponible à une échelle.
    servis = [l for l in cat if l["secteur"] in SECTEURS
              and (_vrai(l["dispo_province"]) or _vrai(l["dispo_commune"]))]

    niveaux = {}
    for t in terr:
        niveaux[t["niveau"]] = niveaux.get(t["niveau"], 0) + 1

    # Les routes, comptées dans le code.
    routers = os.path.join(PROJET, "backend", "app", "routers")
    routes, modules = 0, 0
    for nom in sorted(os.listdir(routers)):
        if not nom.endswith(".py") or nom == "__init__.py":
            continue
        code = open(os.path.join(routers, nom), encoding="utf-8").read()
        n = len(re.findall(r"^@router\.(get|post|put|patch|delete)",
                           code, re.M))
        if n:
            modules += 1
            routes += n

    # Les tests unitaires.
    tests = os.path.join(PROJET, "backend", "tests")
    unitaires = sum(
        len(re.findall(r"^    def test_", open(os.path.join(tests, f),
                                               encoding="utf-8").read(), re.M))
        for f in os.listdir(tests) if f.startswith("test_"))

    # Les captures consignées.
    captures = os.path.join(STAGE, "captures")
    swagger = len([f for f in os.listdir(captures)
                   if re.fullmatch(r"t\d+.*\.png", f)])

    return {
        "lignes du catalogue": len(cat),
        "indicateurs servis": len(servis),
        "servis au niveau province": sum(1 for l in servis
                                         if _vrai(l["dispo_province"])),
        "servis au niveau commune": sum(1 for l in servis
                                        if _vrai(l["dispo_commune"])),
        "secteurs servis": len({l["secteur"] for l in servis}),
        "territoires du référentiel": len(terr),
        "préfectures et provinces": niveaux.get("prefecture_province", 0),
        "communes": niveaux.get("commune", 0),
        "routes de l'API": routes,
        "modules de l'API": modules,
        "tests unitaires": unitaires,
        "captures Swagger": swagger,
    }


def texte_du_rapport():
    """Le texte du rapport, lu directement dans l'archive .docx.

    On évite volontairement toute conversion : pas de PDF à produire, pas
    d'outil externe à installer. Le document Word est une archive dont
    word/document.xml porte le texte, réparti en éléments <w:t>.
    """
    if not os.path.exists(RAPPORT):
        raise SystemExit(f"[!] rapport introuvable : {RAPPORT}")
    xml = zipfile.ZipFile(RAPPORT).read("word/document.xml").decode("utf-8")
    return " ".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml))


def principal():
    faits = mesurer()
    print("--- mesuré sur les fichiers livrés ---")
    for cle, valeur in faits.items():
        print(f"   {cle:<30} {valeur:>6}")

    try:
        texte = texte_du_rapport()
    except SystemExit as e:
        print(f"\n{e}")
        return 0

    # Les nombres écrits en toutes lettres ou avec espace insécable ne sont
    # pas cherchés : on ne contrôle que les formes numériques.
    normalise = texte.replace(" ", " ").replace(" ", " ")
    print("\n--- présence dans le texte du rapport ---")
    for cle, valeur in faits.items():
        formes = {str(valeur), f"{valeur:,}".replace(",", " ")}
        trouve = any(re.search(rf"\b{re.escape(f)}\b", normalise)
                     for f in formes)
        print(f"   {cle:<30} {valeur:>6}   "
              f"{'cité' if trouve else 'non cité (à vérifier)'}")

    print("\n--- chiffres périmés à ne plus trouver ---")
    for perime, remplacant in (("394 indicateurs", "342 lignes de catalogue"),
                               ("254 indicateurs", "224 indicateurs servis"),
                               ("240 indicateurs", "224 indicateurs servis"),
                               ("vingt-quatre routes", "trente et une routes"),
                               ("dix modules", "onze modules"),
                               ("105 notions", "106 notions"),
                               ("78 des", "156 des 224")):
        present = perime in normalise
        print(f"   {perime:<24} {'ENCORE PRÉSENT' if present else 'absent'}"
              f"   -> {remplacant}")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
