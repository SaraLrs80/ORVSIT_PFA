"""
Premier contact avec le modèle local.

On ne teste PAS la qualité des réponses ici. On teste une seule chose, la plus
risquée : le modèle sait-il émettre un appel d'outil structuré ? Un modèle qui
répond « le taux de chômage est de 24,6 % » sans passer par l'outil est
inutilisable pour ce projet, quelle que soit l'élégance de sa phrase.

Usage :  python essai_ollama.py
"""

import time
import ollama

MODELES = ["qwen2.5:3b", "qwen2.5:7b"]

# Un outil FICTIF, volontairement simple. On ne veut pas savoir si le modèle
# comprend notre catalogue, seulement s'il sait produire un appel.
OUTILS = [{
    "type": "function",
    "function": {
        "name": "lire_valeur",
        "description": "Lit la valeur d'un indicateur pour un territoire donné.",
        "parameters": {
            "type": "object",
            "properties": {
                "indicateur": {"type": "string", "description": "nom de l'indicateur"},
                "territoire": {"type": "string", "description": "nom du territoire"},
            },
            "required": ["indicateur", "territoire"],
        },
    },
}]

QUESTION = "Quel est le taux de chômage dans la province d'Al Hoceima ?"


def essayer(modele):
    print(f"\n=== {modele}")
    debut = time.time()
    try:
        reponse = ollama.chat(
            model=modele,
            messages=[{"role": "user", "content": QUESTION}],
            tools=OUTILS,
        )
    except Exception as e:
        print(f"[!] échec : {e}")
        return

    duree = time.time() - debut
    appels = reponse["message"].get("tool_calls") or []

    if appels:
        for a in appels:
            f = a["function"]
            print(f"[ok] appel d'outil : {f['name']}({f['arguments']})")
    else:
        # Le cas qui doit nous inquiéter : il a répondu de lui-même.
        texte = reponse["message"].get("content", "")
        print(f"[!] AUCUN appel d'outil. Il a répondu : {texte[:160]}")

    print(f"     {duree:.1f} s")


if __name__ == "__main__":
    for m in MODELES:
        essayer(m)