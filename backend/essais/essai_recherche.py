"""
Passe le jeu d'évaluation dans la recherche, SANS modèle.

CE QU'ON MESURE ICI
Une seule chose, et elle ne dépend d'aucun hasard : la recherche par mots
trouve-t-elle des candidats plausibles, et n'en trouve-t-elle AUCUN quand la
donnée n'existe pas ?

LE BARÈME, ET POURQUOI IL A CHANGÉ
La première version demandait à la recherche de refuser les douze questions
« impossibles ». C'était injuste : « le chômage à Marrakech » désigne un
indicateur qui EXISTE — c'est le territoire qui est hors région. Refuser cette
question est le travail d'un autre gardien.

Quatre gardiens se partagent le refus :
    indicateur   l'indicateur existe-t-il ?          -> chercher()          [ici]
    territoire   est-il servi par la plateforme ?    -> resoudre_territoire
    temps        le millésime existe-t-il ?          -> à écrire
    intention    demande-t-on un calcul, un score ?  -> à écrire

Ce script ne note donc que le premier. Les questions relevant des trois autres
sont affichées mais comptées à part.

Usage :  python essai_recherche.py
"""

import csv
import glob
import re
import unicodedata

from app.assistant.recherche import chercher, ligne_pour_le_modele
from app.database import SessionDWH

DOSSIER = "evaluation"
LARGEUR = 3          # candidats affichés par question

# Questions dont le refus n'appartient PAS à la recherche : l'indicateur
# existe, c'est autre chose qui cloche. Elles sont exclues du barème.
AUTRES_GARDIENS = {
    "J2": "temps (projection)",
    "J3": "territoire (hors région)",
    "J7": "temps (millésime absent)",
    "J8": "intention (prévision)",
    "J9": "intention (calcul composite)",
    "J10": "territoire (hors région)",
    "J11": "territoire (niveau non servi)",
    "J12": "intention (ventilation absente)",
    "G3": "territoire (niveaux différents)",
}


def niveau_de_la_phrase(question):
    """
    Le niveau territorial mentionné n'importe où dans la phrase.

    Provisoire : niveau_demande() de outils.py ne lit que le DÉBUT d'un nom de
    territoire. Le découpage propre de la phrase reviendra au moteur.
    """
    t = unicodedata.normalize("NFD", question.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    if re.search(r"\bcommunes?\b|\bmunicipalites?\b", t):
        return "commune"
    if re.search(r"\bprovinces?\b|\bprefectures?\b", t):
        return "prefecture_province"
    return None


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
        print(f"{len(cas)} questions\n")

        DOIT_TROUVER = {"valeur", "classement", "comparaison", "zero",
                        "definition", "ambigu", "orthographe"}
        DOIT_RIEN_TROUVER = {"impossible"}

        justes = total = 0
        muettes = 0
        rates = []

        for q in cas:
            niveau = niveau_de_la_phrase(q["question"])
            trouves = chercher(dwh, q["question"], niveau)
            if not trouves:
                muettes += 1

            note = " "
            if q["id"] in AUTRES_GARDIENS:
                note = "hors"
            elif q["famille"] in DOIT_TROUVER:
                total += 1
                ok = bool(trouves)
                justes += ok
                note = "OK " if ok else "RATE"
            elif q["famille"] in DOIT_RIEN_TROUVER:
                total += 1
                ok = not trouves
                justes += ok
                note = "OK " if ok else "RATE"
            if note == "RATE":
                rates.append(q)

            suffixe = f"   <- {AUTRES_GARDIENS[q['id']]}" if q["id"] in AUTRES_GARDIENS else ""
            print(f"[{note}] {q['id']:<5} {q['famille']:<11} "
                  f"niveau={(niveau or '-'):<20} {q['question'][:48]}{suffixe}")
            for f in trouves[:LARGEUR]:
                print(f"            {ligne_pour_le_modele(f)[:104]}")
            if not trouves:
                print("            aucun candidat  ->  refus sans appeler le modèle")

        print(f"\n{justes}/{total} questions notables correctes "
              f"({round(justes * 100 / total)} %)")
        print(f"{muettes} questions sur {len(cas)} traitées sans modèle")
        print(f"{len(AUTRES_GARDIENS)} questions relèvent d'un autre gardien, "
              f"hors barème")
        if rates:
            print("\nà corriger :")
            for q in rates:
                print(f"   {q['id']:<5} {q['question'][:66]}")
    finally:
        dwh.close()


if __name__ == "__main__":
    raise SystemExit(principal())
