"""
Mesure du coût réel d'un appel, à chaud, avec et sans le catalogue.

Pourquoi cette mesure décide de l'architecture : sur un processeur sans carte
graphique, le temps se passe surtout à LIRE l'invite, pas à écrire la réponse.
Si mettre le catalogue entier dans l'invite coûte trente secondes par question,
il faudra le filtrer avant de l'envoyer. Si ça coûte trois secondes, on le laisse
entier et l'assistant voit tout le catalogue à chaque fois — beaucoup plus simple
et beaucoup plus fiable.

Usage :  python essai_debit.py
"""

import csv
import statistics
import ollama

MODELES = ["qwen2.5:3b", "qwen2.5:7b"]
CATALOGUE_CSV = "../data-pipeline/dim_indicateur.csv"
GARDE_EN_MEMOIRE = "30m"   # le modèle reste chargé : on mesure à chaud
OUTILS = [{
    "type": "function",
    "function": {
        "name": "lire_valeur",
        "description": "Lit la valeur d'un indicateur du catalogue pour un territoire.",
        "parameters": {
            "type": "object",
            "properties": {
                "indicateur_id": {"type": "integer",
                                  "description": "identifiant repris du catalogue"},
                "territoire": {"type": "string",
                               "description": "nom du territoire, tel qu'il s'écrit"},
            },
            "required": ["indicateur_id", "territoire"],
        },
    },
}]

def vrai(v):
    return str(v).strip().lower() in ("true", "vrai", "1", "oui")


def catalogue():
    """Le catalogue tel que le modèle le verra : un indicateur par ligne."""
    lignes = []
    for c in csv.DictReader(open(CATALOGUE_CSV, encoding="utf-8-sig")):
        niveaux = ("P" if vrai(c["dispo_province"]) else "") + \
                  ("C" if vrai(c["dispo_commune"]) else "")
        if not niveaux:          # indicateur masqué : inutile de l'exposer
            continue
        lignes.append(f"{c['indicateur_id']}|{c['libelle_court']}|"
                      f"{c['unite']}|{c['secteur']}|{niveaux}")
    return "\n".join(lignes)

def catalogue_secteur(secteur):
    """Le catalogue restreint à un seul secteur : sert à mesurer l'effet
    de la LONGUEUR du contexte, indépendamment de la formulation."""
    return "\n".join(l for l in catalogue().split("\n")
                     if f"|{secteur}|" in l)

def mesurer(modele, invite_systeme, question, repetitions=3):
    """Mesure un tour réaliste : outils déclarés, réponse brève attendue."""
    messages = []
    if invite_systeme:
        messages.append({"role": "system", "content": invite_systeme})
    messages.append({"role": "user", "content": question})

    ecrits, ecritures, appels = [], [], 0
    for i in range(repetitions + 1):
        r = ollama.chat(model=modele, messages=messages, tools=OUTILS,
                        keep_alive=GARDE_EN_MEMOIRE,
                        options={"num_predict": 200})   # plafond de sécurité
        if i == 0:
            continue
        if r["message"].get("tool_calls"):
            appels += 1
        ecrits.append(r.get("eval_count", 0))
        ecritures.append(r.get("eval_duration", 0) / 1e9)

    return (statistics.median(ecrits), statistics.median(ecritures),
            appels, repetitions)
if __name__ == "__main__":
    cat = catalogue()
    print(f"catalogue : {len(cat.splitlines())} indicateurs, "
          f"{len(cat)} caractères\n")

    QUESTION = "Quel est le taux de chômage dans la province d'Al Hoceima ?"

    CONSIGNE = (
        "Tu es un assistant de données territoriales. Tu ne connais AUCUNE "
        "valeur chiffrée par toi-même.\n"
        "Le catalogue ci-dessous liste seulement QUELS indicateurs existent. "
        "Il ne contient AUCUNE valeur.\n"
        "Pour obtenir une valeur, tu DOIS appeler l'outil lire_valeur avec "
        "l'identifiant repris du catalogue.\n"
        "Ne réponds jamais un chiffre sans avoir appelé l'outil.\n\n"
        "Catalogue (identifiant|libellé|unité|secteur|niveaux) :\n"
    )

    emploi = catalogue_secteur("Emploi")
    print(f"catalogue Emploi seul : {len(emploi.splitlines())} indicateurs\n")

    variantes = [
        ("1 sans catalogue",   None),
        ("2 ancienne consigne",
         "Tu réponds à partir du catalogue ci-dessous, jamais de mémoire.\n"
         "Chaque ligne : identifiant|libellé|unité|secteur|niveaux.\n"
         "Pour lire une valeur, appelle l'outil avec l'identifiant du catalogue.\n"
         "Sois bref.\n\n" + cat),
        ("3 consigne stricte",  CONSIGNE + cat),
        ("4 secteur Emploi",    CONSIGNE + emploi),
    ]

    for modele in MODELES:
        print(f"=== {modele}")
        for nom, systeme in variantes:
            try:
                jetons, duree, appels, total = mesurer(modele, systeme, QUESTION)
            except Exception as e:
                print(f"  {nom:<22} échec : {e}")
                continue
            debit = jetons / duree if duree else 0
            print(f"  {nom:<22} outil {appels}/{total} · {jetons:>4.0f} jetons "
                  f"en {duree:5.1f} s ({debit:4.1f} j/s)")
        print()