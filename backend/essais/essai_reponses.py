"""
Les vraies réponses, avec le modèle.

Huit questions représentatives, une par branche. On regarde deux choses :
la phrase est-elle correcte, et combien de temps a-t-elle coûté.

C'est le premier essai où Ollama entre en jeu. Tout ce qui précède a été
décidé par du code ; le modèle ne fait que mettre en français une valeur
déjà lue dans PostgreSQL.

Usage :  python essai_reponses.py
"""

import time

from app.assistant.moteur import repondre
from app.database import SessionDWH

QUESTIONS = [
    "Quel est le taux de chômage dans la province d'Al Hoceima ?",
    "Combien d'habitants compte la province de Fahs-Anjra ?",
    "Quel est le taux de pauvreté dans la commune de Chefchaouen ?",
    "Combien d'établissements avec unité UMP dans la province de Chefchaouen ?",
    "Quelle province a le taux de chômage le plus élevé ?",
    "Que veut dire taux de pauvreté multidimensionnelle ?",
    "Que sais-tu sur la santé au niveau communal ?",
    "Bonjour",
]


def principal():
    dwh = SessionDWH()
    try:
        total = 0.0
        acceptees, rejetees, motifs = 0, 0, []
        for question in QUESTIONS:
            debut = time.time()
            t = repondre(dwh, question)
            duree = time.time() - debut
            total += duree

            print(f"\n=== {question}")
            print(f"    branche  : {t['branche']}"
                  f"{' / ' + t['refus'] if t['refus'] else ''}")
            if t["outils"]:
                for o in t["outils"]:
                    print(f"    outil    : {o['nom']}({o['args']})")
            if t.get("valeur"):
                print(f"    valeur   : {t['valeur']}  ·  millésime "
                      f"{t.get('millesime')}")
            print(f"    durée    : {duree:.1f} s")

            # Le chiffre qui compte : la reformulation du modèle a-t-elle été
            # retenue, ou rejetée au profit du brouillon déterministe ?
            etat = t.get("reformulation")
            if etat:
                print(f"    modèle   : {etat}")
                if etat.startswith("acceptée"):
                    acceptees += 1
                else:
                    rejetees += 1
                    motifs.append((question[:40], etat))
                    print(f"    brouillon: {t.get('brouillon', '')[:100]}")
            print(f"    réponse  : {t['reponse']}")

        print(f"\n{len(QUESTIONS)} questions · {total:.0f} s au total · "
              f"{total / len(QUESTIONS):.1f} s en moyenne")
        soumises = acceptees + rejetees
        if soumises:
            print(f"\nreformulations soumises au modèle : {soumises}")
            print(f"   acceptées : {acceptees}  "
                  f"({round(acceptees * 100 / soumises)} %)")
            print(f"   rejetées  : {rejetees}   "
                  f"-> le brouillon déterministe a été servi")
            for q, m in motifs:
                print(f"      {q:<42} {m}")
    finally:
        dwh.close()


if __name__ == "__main__":
    raise SystemExit(principal())