"""
Le contexte commun aux tests unitaires.

Les tests ne touchent ni PostgreSQL ni Ollama. Les fonctions éprouvées ici
sont pures — elles reçoivent du texte et rendent une décision — sauf celles
de la recherche, qui lisent le catalogue : pour celles-là, le faux entrepôt
substitue les fichiers CSV du dossier data-pipeline aux requêtes SQL.

Conséquence pratique : `python -m unittest discover tests` s'exécute sans
serveur, sans base et sans modèle. C'est ce qui rend ces tests utilisables
comme garde-fou avant chaque livraison.
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

_branche = False


def brancher():
    """Substitue les CSV aux lectures en base, une seule fois."""
    global _branche
    if not _branche:
        from evaluation.faux_entrepot import brancher as brancher_faux
        brancher_faux()
        _branche = True
