"""
Comparaison de territoires de même niveau.

Un seul endpoint : GET /comparer?ids=2,9,8

Pourquoi un router séparé de la fiche ?
  La fiche décrit UN territoire en profondeur ; la comparaison met en regard
  PLUSIEURS territoires sur un petit nombre d'indicateurs communs. Les deux
  questions sont différentes, donc les deux réponses aussi.

Ce qu'on réutilise de fiche.py plutôt que de le réécrire :
  - la résolution du territoire et de ses pairs,
  - la lecture groupée des valeurs de comparaison,
  - la définition des indicateurs et leur sens.
Dupliquer ce code serait la garantie qu'un jour les deux versions divergent.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..database import get_dwh
from ..deps import get_current_user
from .fiche import (
    _territoire, _province_de, _pairs, _valeurs_pairs, _sources,
    INDICATEURS_PAIRS, INDICATEURS_PROVINCE, INDICATEURS_COMMUNE,
)

router = APIRouter(prefix="/comparer", tags=["comparaison"])

def _lire_ids(ids: str):
    """
    Transforme « 2,9,8 » en [2, 9, 8].

    On retire les doublons SANS perdre l'ordre : l'ordre choisi par l'utilisateur
    détermine les couleurs à l'écran, donc il doit être stable.
    """
    trouves = []
    for morceau in ids.split(","):
        morceau = morceau.strip()
        if not morceau:
            continue
        if not morceau.lstrip("-").isdigit():
            raise HTTPException(400, f"Identifiant de territoire invalide : « {morceau} »")
        valeur = int(morceau)
        if valeur not in trouves:
            trouves.append(valeur)
    return trouves

def _ensemble_reference(dwh: Session, territoires, niveau: str):
    """
    Territoires servant de toile de fond à la comparaison.

    Ils ne sont pas seulement décoratifs : ce sont eux qui permettent de dire
    « ce territoire est le plus faible de la région » plutôt que simplement
    « il est plus faible que l'autre ». Sans eux, la carte n'apprend rien.
    """
    if niveau == "prefecture_province":
        return _pairs(dwh, territoires[0], None)

    # Niveau commune : on regarde si tous appartiennent à la même province.
    provinces = {_province_de(dwh, t) for t in territoires}
    if len(provinces) == 1 and None not in provinces:
        return _pairs(dwh, territoires[0], provinces.pop())

    # Provinces différentes : on élargit à toutes les communes de la région.
    lignes = dwh.execute(text("""
        SELECT territoire_id, nom FROM referential.dim_territoire
        WHERE niveau = 'commune' ORDER BY nom
    """)).mappings().all()
    return {str(l["territoire_id"]): l["nom"] for l in lignes}

def _ecarts(valeurs, definitions, ids_compares):
    """
    Pour chaque indicateur : qui mène, qui suit, et de combien.

    Le tri final se fait sur l'écart RELATIF (écart ÷ valeur la plus haute) et
    non sur l'écart brut. Sinon « 8576 habitants par médecin » écraserait
    toujours « 12 points de chômage », alors que le second est souvent plus
    parlant pour décider.
    """
    resultat = []
    for d in definitions:
        vals = valeurs.get(d["cle"], {})
        presents = [(tid, vals[tid]) for tid in ids_compares if tid in vals]
        if len(presents) < 2:
            continue   # un seul territoire renseigné : rien à comparer

        # Le sens de l'indicateur décide qui est « le meilleur ».
        favorable = max if d["sens"] == 1 else min
        meilleur = favorable(presents, key=lambda x: x[1])
        pire = (min if d["sens"] == 1 else max)(presents, key=lambda x: x[1])

        ecart = abs(meilleur[1] - pire[1])
        reference = max(abs(v) for _, v in presents) or 1

        resultat.append({
            "cle": d["cle"], "label": d["label"], "unite": d["unite"], "theme": d["theme"],
            "meilleur": {"territoire_id": meilleur[0], "valeur": meilleur[1]},
            "pire": {"territoire_id": pire[0], "valeur": pire[1]},
            "ecart": round(ecart, 2),
            "ecart_relatif": round(ecart / reference, 4),
        })

    resultat.sort(key=lambda x: x["ecart_relatif"], reverse=True)
    return resultat


def _rangs(valeurs, definitions, ids_compares):
    """
    Position de chaque territoire comparé dans l'ensemble de référence.
    Rang 1 = le mieux placé, selon le sens de l'indicateur.
    """
    resultat = {}
    for d in definitions:
        vals = valeurs.get(d["cle"], {})
        if len(vals) < 2:
            continue
        ordonne = sorted(vals.items(), key=lambda kv: kv[1], reverse=(d["sens"] == 1))
        positions = [tid for tid, _ in ordonne]
        for tid in ids_compares:
            if tid in vals:
                resultat.setdefault(tid, {})[d["cle"]] = {
                    "rang": positions.index(tid) + 1,
                    "total": len(positions),
                }
    return resultat

@router.get("")
def comparer(ids: str = Query(..., description="Identifiants séparés par des virgules, ex. 2,9,8"),
             dwh: Session = Depends(get_dwh),
             user=Depends(get_current_user)):
    """Met en regard 2 à 4 territoires de même niveau."""
    demandes = _lire_ids(ids)

    if len(demandes) < 2:
        raise HTTPException(400, "Il faut au moins deux territoires différents à comparer.")
    if len(demandes) > 4:
        raise HTTPException(400, "Comparaison limitée à quatre territoires pour rester lisible.")

    # On résout chaque territoire, en signalant précisément lequel pose problème.
    territoires = []
    for tid in demandes:
        terr = _territoire(dwh, tid)
        if terr is None:
            raise HTTPException(404, f"Territoire {tid} introuvable.")
        if terr["niveau"] not in ("prefecture_province", "commune"):
            raise HTTPException(400, f"« {terr['nom']} » n'est ni une province ni une commune.")
        territoires.append(terr)

    # Règle métier : on ne compare que des territoires de même niveau.
    niveaux = {t["niveau"] for t in territoires}
    if len(niveaux) > 1:
        raise HTTPException(
            400, "Comparaison impossible entre niveaux différents : "
                 "une province et une commune ne sont pas comparables.")
    niveau = territoires[0]["niveau"]

    reference = _ensemble_reference(dwh, territoires, niveau)

    definitions = INDICATEURS_PAIRS + (
        INDICATEURS_PROVINCE if niveau == "prefecture_province" else INDICATEURS_COMMUNE)

    # Une seule lecture pour TOUS les territoires de référence, pas une par
    # territoire : c'est ce qui garde l'endpoint rapide même sur 146 communes.
    valeurs = _valeurs_pairs(dwh, reference.keys(), niveau)
    # Les clés de « valeurs » sont des chaînes : on aligne les identifiants
    # comparés sur le même type, sinon aucune correspondance ne sera trouvée.
    ids_compares = [str(t["territoire_id"]) for t in territoires]
    return {
        "niveau": niveau,
        "territoires": [{"territoire_id": t["territoire_id"], "nom": t["nom"]} for t in territoires],
        "reference": reference,
        "indicateurs": definitions,
        "valeurs": valeurs,
        "ecarts": _ecarts(valeurs, definitions, ids_compares),
        "rangs": _rangs(valeurs, definitions, ids_compares),
        "sources": _sources(dwh, niveau),
    }