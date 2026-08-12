"""
La campagne d'évaluation : 300 questions à travers le moteur, sans modèle.

POURQUOI SANS MODÈLE
Ce qu'on éprouve ici, c'est l'aiguillage : la question part-elle par la bonne
porte ? Cette décision est entièrement déterministe. Y ajouter le modèle
coûterait plus d'une heure et n'éprouverait que la mise en forme de la phrase,
déjà mesurée ailleurs — et déjà protégée par le rejet des reformulations
infidèles.

POURQUOI DEUX SCORES ET UNE MATRICE
Les familles du jeu et les branches du moteur ne se correspondent pas une pour
une, et c'est normal. « Quel est le taux de chômage à Tanger ? » est rangée en
« valeur_precise », mais l'assistant DOIT demander : Tanger désigne une commune
et une préfecture. Noter cela comme un échec reviendrait à reprocher au système
le comportement qu'on lui a demandé.

    score strict      la branche attendue, sans nuance
    score acceptable  les branches défendables pour cette famille
    matrice           où le système diverge, et de combien

C'est la matrice qui sert. Un pourcentage ne dit pas quoi corriger ; une case
de la matrice, si.

Usage :
    python evaluer.py                     les 300 questions
    python evaluer.py --famille impossible  une famille seulement
"""

import csv
import sys
import time
from collections import Counter, defaultdict

# --hors-ligne : la campagne tourne sur les fichiers CSV, sans PostgreSQL.
# C'est ce qui permet de l'exécuter AVANT de proposer une correction, au lieu
# de découvrir la régression au tour suivant.
HORS_LIGNE = "--hors-ligne" in sys.argv
if HORS_LIGNE:
    from evaluation.faux_entrepot import brancher
    brancher()

from app.assistant.moteur import repondre          # noqa: E402

if not HORS_LIGNE:
    from app.database import SessionDWH            # noqa: E402

JEU = "evaluation/questions_300.csv"
RESULTATS = "evaluation/resultats.csv"

# Pour chaque famille du jeu : la branche attendue, et celles qui restent
# défendables. Toute divergence hors de ces ensembles est un vrai écart.
ATTENDU = {
    "valeur_precise":        ("valeur",       {"question"}),
    "impossible":            ("refus",        {"question"}),
    "territoire_ambigu":     ("question",     {"valeur"}),
    "classement_superlatif": ("classement",   {"refus"}),
    # Le refus est ACCEPTABLE ici, et souvent c'est même la bonne réponse :
    # le jeu contient des questions qui comparent une commune à une province.
    # Les refuser est la règle du projet — on ne compare que des pairs de même
    # niveau — mais leur famille reste « comparaison ». Sans cette tolérance,
    # huit refus justes étaient comptés comme des échecs.
    "comparaison":           ("comparaison",  {"question", "refus"}),
    "couverture":            ("couverture",   {"question"}),
    "definition_source":     ("definition",   {"couverture"}),
    "conversation":          ("conversation", set()),
    # Le langage familier n'a pas de branche attendue : la question peut être
    # de n'importe quelle nature. On la rapporte sans la noter.
    "langage_familier":      (None,           set()),
}


def questions(famille=None):
    with open(JEU, encoding="utf-8-sig") as f:
        tout = list(csv.DictReader(f, delimiter=";"))
    return [q for q in tout if not famille or q["famille"] == famille]


def principal(famille=None):
    dwh = None if HORS_LIGNE else SessionDWH()
    try:
        cas = questions(famille)
        print(f"{len(cas)} questions\n")

        matrice = defaultdict(Counter)
        refus_par_motif = Counter()
        strict = acceptable = notees = 0
        ecarts = []
        debut = time.time()

        with open(RESULTATS, "w", encoding="utf-8-sig", newline="") as sortie:
            plume = csv.writer(sortie, delimiter=";")
            plume.writerow(["id", "famille", "question", "branche_obtenue",
                            "refus", "indicateur", "territoire", "verdict",
                            "reponse"])

            for i, q in enumerate(cas, 1):
                t = repondre(dwh, q["question"], modele_actif=False)
                branche = t["branche"] or "?"
                matrice[q["famille"]][branche] += 1
                if t["refus"]:
                    refus_par_motif[t["refus"]] += 1

                vise, tolere = ATTENDU.get(q["famille"], (None, set()))
                if vise is None:
                    verdict = "non noté"
                else:
                    notees += 1
                    if branche == vise:
                        verdict = "strict"
                        strict += 1
                        acceptable += 1
                    elif branche in tolere:
                        verdict = "acceptable"
                        acceptable += 1
                    else:
                        verdict = "écart"
                        ecarts.append((q["id"], q["famille"], vise, branche,
                                       t["refus"], q["question"]))

                plume.writerow([q["id"], q["famille"], q["question"], branche,
                                t["refus"] or "", t.get("indicateur") or "",
                                t.get("territoire") or "", verdict,
                                (t["reponse"] or "")[:300]])

                if i % 50 == 0:
                    print(f"   … {i}/{len(cas)}")

        duree = time.time() - debut
        print(f"\n{len(cas)} questions en {duree:.1f} s "
              f"({duree / len(cas) * 1000:.0f} ms par question)\n")

        print("--- matrice famille x branche ---")
        branches = sorted({b for c in matrice.values() for b in c})
        entete = "famille".ljust(24) + "".join(b[:11].rjust(13) for b in branches)
        print(entete)
        for fam in sorted(matrice):
            ligne = fam.ljust(24)
            for b in branches:
                n = matrice[fam][b]
                ligne += (str(n) if n else "·").rjust(13)
            print(ligne)

        print("\n--- motifs de refus ---")
        for m, n in refus_par_motif.most_common():
            print(f"    {m:<14} {n:>4}")

        print(f"\nscore strict     : {strict}/{notees} "
              f"({round(strict * 100 / notees)} %)")
        print(f"score acceptable : {acceptable}/{notees} "
              f"({round(acceptable * 100 / notees)} %)")
        print(f"écarts à examiner: {len(ecarts)}")

        if ecarts:
            print("\n--- les vingt premiers écarts ---")
            for id_, fam, vise, obtenu, refus, question in ecarts[:20]:
                motif = f"/{refus}" if refus else ""
                print(f"   {id_:<8} {fam:<22} attendu {vise:<12} "
                      f"obtenu {obtenu}{motif}")
                print(f"            {question[:88]}")

        print(f"\nDétail complet : {RESULTATS}")
    finally:
        if dwh is not None:
            dwh.close()


if __name__ == "__main__":
    fam = None
    if "--famille" in sys.argv:
        fam = sys.argv[sys.argv.index("--famille") + 1]
    raise SystemExit(principal(fam))
