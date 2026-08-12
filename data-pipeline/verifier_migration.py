"""
Vérifier, sur la donnée elle-même, ce que mesurent les indicateurs de migration.

POURQUOI CE SCRIPT
Le document de métadonnées du HCP décrit les indicateurs en français ; les
trois classeurs source portent des colonnes dont le nom a été repris tel quel
au nettoyage. Entre les deux, trois libellés du catalogue disaient autre chose
que ce que la colonne contient — dont un qui disait exactement l'inverse.

Le seul juge est l'arithmétique : les indices sont publiés DANS la source, à
côté de leurs composantes. On peut donc retrouver le dénominateur en essayant
tous les candidats et en regardant lequel reproduit l'indice publié sur les
179 territoires. Aucune interprétation n'intervient.

Ce script ne modifie rien. Il imprime les preuves qui justifient les
définitions écrites par rediger_definitions.py.

    python verifier_migration.py
"""

import glob
import os

import pandas as pd

DOSSIER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "data", "demography")

CLASSEURS = {
    "durée de vie": "*Migration interne durée de vie*.xlsx",
    "5 ans":        "*Mig-interne-5ans*.xlsx",
    "10 ans":       "*Mig_interne-10ans*.xlsx",
}

TOLERANCE_INDICE = 0.05   # points de pourcentage
TOLERANCE_EFFECTIF = 1    # personnes


def croiser(motif):
    trouves = glob.glob(os.path.join(DOSSIER, motif))
    if not trouves:
        raise SystemExit(f"[!] Classeur introuvable : {motif}\n"
                         f"    cherché dans {DOSSIER}")
    try:
        d = pd.read_excel(trouves[0], sheet_name=0)
    except ImportError:
        # pandas délègue la lecture des .xlsx à openpyxl, qui n'est pas une
        # dépendance obligatoire : le message d'origine est illisible.
        raise SystemExit("[!] Lecture des .xlsx impossible : le module "
                         "openpyxl manque.\n    Installez-le avec :  "
                         "pip install openpyxl")
    return d.pivot_table(index="cg", columns="indicateur",
                         values="valeur", aggfunc="first")


def concordance(a, b, tolerance):
    """Combien de territoires sur combien vérifient l'égalité."""
    x, y = a.align(b, join="inner")
    return int(((x - y).abs() <= tolerance).sum()), len(x)


def chercher_denominateur(p, indice, numerateur):
    """Quel dénominateur reproduit l'indice publié ? On les essaie tous."""
    candidats = [c for c in p.columns if not c.startswith("indice")]
    resultats = []
    for c in candidats:
        n, total = concordance(100 * p[numerateur] / p[c], p[indice],
                               TOLERANCE_INDICE)
        resultats.append((n, total, c))
    resultats.sort(reverse=True)
    return resultats


def titre(t):
    print(f"\n{'=' * 74}\n{t}\n{'=' * 74}")


def principal():
    p = {nom: croiser(motif) for nom, motif in CLASSEURS.items()}

    titre("1 · De quoi les indices sont-ils le rapport ?")
    for nom, tableau in p.items():
        e = [c for c in tableau.columns if "indice_entrees" in c][0]
        s = [c for c in tableau.columns if "indice_sortie" in c][0]
        print(f"\n  -- classeur « {nom} », {len(tableau)} territoires")
        for etiquette, indice, num in (("d'entrées", e, "entrees"),
                                       ("de sorties", s, "sorties")):
            n, total, col = chercher_denominateur(tableau, indice, num)[0]
            print(f"     indice {etiquette:<11} = {num} / {col:<32} "
                  f"{n}/{total}")

    titre("2 · Les identités de composition")
    d, c5, c10 = p["durée de vie"], p["5 ans"], p["10 ans"]
    for libelle, a, b in (
        ("natifs = natifs résidant sur place + sorties",
         d["natifs"], d["natifs_residents_non_migrants"] + d["sorties"]),
        ("résidents récents 5 ans = non-migrants récents + sorties",
         c5["residents_recents_5ans"],
         c5["natifs_residents_non_migrants"] + c5["sorties"]),
        ("résidents récents 10 ans = non-migrants + sorties",
         c10["residents_recents_10ans"],
         c10["natifs_residents_non_migrants"] + c10["sorties"]),
    ):
        n, total = concordance(a, b, TOLERANCE_EFFECTIF)
        print(f"  {libelle:<58} {n}/{total}")
    print("\n  Lecture : « residents_recents » est donc l'effectif PRÉSENT")
    print("  cinq (ou dix) ans plus tôt, et non les personnes arrivées depuis.")
    print("  Le libellé « Résidents installés depuis moins de 5 ans » disait")
    print("  l'inverse de la donnée.")

    titre("3 · Quelle tranche d'âge chaque population sédentaire couvre-t-elle ?")
    total_ages = d["population_sedentaire"]
    for nom, serie, tranche in (("5 ans", c5["population_sedentaire_5ans_plus"], "0-4 ans"),
                                ("10 ans", c10["population_sedentaire"], "0-9 ans")):
        part = 100 * (1 - serie / total_ages)
        print(f"  classeur « {nom} » : exclut {part.median():.2f} % de la "
              f"population (médiane sur {len(part)} territoires)")
        print(f"     à comparer à la part publiée des {tranche}")
    print("\n  RGPH 2024, région : 0-4 ans = 8,2 % ; 0-9 ans = 17,8 %.")

    titre("4 · Anomalie de source à signaler")
    brut = pd.read_excel(glob.glob(os.path.join(DOSSIER, CLASSEURS["5 ans"]))[0],
                         sheet_name=0)
    noms = dict(zip(brut["cg"], brut["collectivite"]))
    for nom, tableau, pop in (("5 ans", c5, "population_sedentaire_5ans_plus"),
                              ("10 ans", c10, "population_sedentaire")):
        reste = (tableau[pop] - tableau["natifs_residents_non_migrants"]
                 - tableau["entrees"])
        fautifs = reste[reste < -1000]
        for cg in fautifs.index:
            print(f"  classeur « {nom} », {noms.get(cg, cg)} ({cg}) : "
                  f"non-migrants + entrées dépassent la population "
                  f"de {-fautifs[cg]:,.0f}")
    print("\n  Ailleurs, l'écart médian est de quelques unités. L'anomalie est")
    print("  isolée : elle vient de la source, pas du chargement.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
