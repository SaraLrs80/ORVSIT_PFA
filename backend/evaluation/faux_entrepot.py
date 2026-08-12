"""
Un entrepôt de substitution, bâti sur les fichiers CSV du dossier data-pipeline.

POURQUOI CE FICHIER EXISTE
La campagne d'évaluation a besoin de PostgreSQL. Tant qu'elle ne pouvait
tourner que là où la base est installée, chaque correction du moteur était
proposée sans avoir été éprouvée sur les trois cents questions : on corrigeait
un défaut, on en introduisait un autre, et on ne s'en apercevait qu'au tour
suivant.

Ce module lève cette dépendance pour la partie du moteur qui décide de tout :
l'AIGUILLAGE. Il fournit les deux seules lectures nécessaires — le référentiel
des territoires et le catalogue des indicateurs — à partir des CSV, et
neutralise les outils qui liraient des valeurs.

CE QU'IL NE FAIT PAS
Il ne remplace pas la base. Les valeurs rendues par les outils sont factices :
ce module sert à vérifier PAR OÙ une question passe, jamais ce qu'elle
rapporte. La justesse des valeurs se vérifie sur la vraie base, avec
essai_reponses.py.

Usage :
    from evaluation.faux_entrepot import brancher
    brancher()          # à appeler AVANT d'importer le moteur
"""

import csv
import os

RACINE = os.path.join(os.path.dirname(__file__), "..", "..", "data-pipeline")


def _vrai(v):
    return str(v).strip().lower() in ("true", "vrai", "1", "oui")


def _entier(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _lire(nom):
    with open(os.path.join(RACINE, nom), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def brancher():
    """Remplace les lectures en base par des lectures de fichiers."""
    from app.assistant import outils, recherche

    indicateurs = _lire("dim_indicateur.csv")
    territoires = _lire("dim_territoire.csv")

    # --- le référentiel des territoires -----------------------------------
    servis = [t for t in territoires
              if t["niveau"] in ("prefecture_province", "commune")]

    def faux_territoires(dwh):
        return [{"territoire_id": _entier(t["territoire_id"]),
                 "nom": t["nom"], "niveau": t["niveau"],
                 "parent_id": _entier(t["parent_id"]),
                 "cle": outils.cle(t["nom"])} for t in servis]

    outils._territoires = faux_territoires

    # --- le catalogue ------------------------------------------------------
    def fausses_lignes(dwh, niveau):
        gardees = []
        for l in indicateurs:
            if l["secteur"] not in recherche.SECTEURS:
                continue
            prov, comm = _vrai(l["dispo_province"]), _vrai(l["dispo_commune"])
            if not (prov or comm):
                continue
            if niveau == "commune" and not comm:
                continue
            if niveau == "prefecture_province" and not prov:
                continue
            gardees.append({**l, "indicateur_id": _entier(l["indicateur_id"]),
                            "mots_cles": l.get("mots_cles", "")})
        gardees.sort(key=lambda l: (l["secteur"], l["indicateur_id"]))
        return gardees

    recherche._lignes = fausses_lignes

    # --- les outils de lecture --------------------------------------------
    # Ils ne sont atteints qu'une fois l'aiguillage terminé. On leur fait
    # rendre une forme correcte avec des valeurs factices : la campagne note
    # la BRANCHE, pas le chiffre.
    par_id = {_entier(l["indicateur_id"]): l for l in indicateurs}

    def faux_lire_valeur(dwh, indicateur_id, territoire_id, ventilation=None):
        c = par_id.get(int(indicateur_id), {})
        return {"trouve": True, "absence": None, "valeur": 0.0,
                "valeur_lisible": "valeur factice",
                "libelle": c.get("libelle_court"), "unite": c.get("unite"),
                "millesime": c.get("annee"), "source": c.get("source"),
                "secteur": c.get("secteur"), "sens": c.get("sens"),
                "territoire": "territoire factice", "niveau": "",
                "ventilation": {"choisie": None, "disponibles": []},
                "message": ""}

    def faux_decrire(dwh, indicateur_id):
        c = par_id.get(int(indicateur_id), {})
        return {"trouve": True, "libelle": c.get("libelle_court"),
                "secteur": c.get("secteur"), "unite": c.get("unite"),
                "millesime": c.get("annee"), "definition": c.get("definition"),
                "tracabilite": None, "source": c.get("source"),
                "sens": {"code": c.get("sens"), "lecture": ""},
                "couverture": {"province": True, "commune": True, "phrase": ""},
                "message": ""}

    def faux_classer(dwh, indicateur_id, niveau="prefecture_province", **k):
        c = par_id.get(int(indicateur_id), {})
        return {"trouve": True, "libelle": c.get("libelle_court"),
                "unite": c.get("unite"), "millesime": c.get("annee"),
                "niveau": niveau, "sens": c.get("sens"),
                "source": c.get("source"), "non_renseignes": [],
                "classement": [{"rang": 1, "nom": "A", "valeur": 1.0,
                                "valeur_lisible": "1"},
                               {"rang": 2, "nom": "B", "valeur": 2.0,
                                "valeur_lisible": "2"}],
                "message": ""}

    def faux_comparer(dwh, indicateur_ids, territoire_ids, **k):
        c = par_id.get(int(indicateur_ids[0]), {})
        return {"trouve": True, "niveau": "",
                "territoires": [{"territoire_id": t, "nom": f"T{t}"}
                                for t in territoire_ids],
                "indicateurs": [{"indicateur_id": indicateur_ids[0],
                                 "libelle": c.get("libelle_court"),
                                 "unite": c.get("unite"),
                                 "millesime": c.get("annee"),
                                 "source": c.get("source"),
                                 "sens": c.get("sens"), "comparable": True,
                                 "ecart_lisible": "0", "en_tete": None,
                                 "cases": [{"nom": f"T{t}", "valeur": 0.0,
                                            "valeur_lisible": "0"}
                                           for t in territoire_ids]}],
                "message": ""}

    def faux_lister(dwh, secteur=None, niveau="prefecture_province", **k):
        lignes = fausses_lignes(dwh, niveau)
        if secteur:
            lignes = [l for l in lignes if l["secteur"] == secteur]
        return {"nombre": len(lignes),
                "indicateurs": [{"libelle_court": l["libelle_court"]}
                                for l in lignes],
                "message": ""}

    # Le moteur importe ces fonctions par leur nom : on remplace donc les
    # deux endroits, le module d'origine et celui qui les a importées.
    from app.assistant import moteur
    for cible in (outils, moteur):
        cible.lire_valeur = faux_lire_valeur
        cible.decrire = faux_decrire
        cible.classer = faux_classer
        cible.comparer = faux_comparer
        cible.lister_indicateurs = faux_lister
