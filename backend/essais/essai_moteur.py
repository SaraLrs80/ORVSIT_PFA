"""
Le moteur sur les 65 questions, SANS modèle.

Les cinq premières branches sont déterministes : elles s'éprouvent seules, en
quelques millisecondes, sans Ollama. C'est ce que fait ce script — il arrête le
parcours juste avant l'étape 6 et regarde par où chaque question est sortie.

Ce qu'on lit dans la sortie :
    secteur       la question portait sur un secteur entier
    refus         un gardien a tranché, avec sa raison
    question      l'assistant demande une précision
    modele        la question ira jusqu'au modèle
    conversation  rien à chercher (salutation, remerciement)

Usage :  python essai_moteur.py
"""

import csv
import glob
from collections import Counter

from app.assistant.moteur import repondre
from app.database import SessionDWH

DOSSIER = "evaluation"


def questions():
    tout = []
    for chemin in sorted(glob.glob(f"{DOSSIER}/questions*.csv")):
        with open(chemin, encoding="utf-8") as f:
            tout += list(csv.DictReader(f, delimiter=";"))
    return tout


def principal():
    dwh = SessionDWH()
    try:
        cas = questions()
        branches, refus = Counter(), Counter()

        for q in cas:
            t = repondre(dwh, q["question"], modele_actif=False)
            branches[t["branche"]] += 1
            if t["refus"]:
                refus[t["refus"]] += 1

            marque = t["branche"] or "?"
            if t["refus"]:
                marque += f"/{t['refus']}"
            print(f"[{marque:<20}] {q['id']:<5} {q['famille']:<11} "
                  f"{q['question'][:44]}")
            if t["branche"] == "modele":
                print(f"      -> {t.get('territoire', '?')} · indicateur "
                      f"{t.get('indicateur', '?')} · {t['candidats'][:2]}")
            elif t["reponse"]:
                print(f"      -> {t['reponse'][:96]}")

        print("\n--- répartition des branches ---")
        for b, n in branches.most_common():
            print(f"    {str(b):<14} {n:>3}")
        print("\n--- raisons de refus ---")
        for r, n in refus.most_common():
            print(f"    {r:<14} {n:>3}")

        # Un refus et une demande de précision sont écrits par le code : ils
        # sortent sans que le modèle soit consulté. Toutes les autres branches
        # lui confient la rédaction de la phrase.
        SANS_MODELE = {"refus", "question"}
        sans = sum(n for b, n in branches.items() if b in SANS_MODELE)
        print(f"\n{sans}/{len(cas)} questions répondues sans appeler le modèle "
              f"({round(sans * 100 / len(cas))} %)")
        print(f"{len(cas) - sans}/{len(cas)} lui confient la rédaction")
    finally:
        dwh.close()


if __name__ == "__main__":
    raise SystemExit(principal())
