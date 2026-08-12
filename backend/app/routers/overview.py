"""
Page d'accueil : ce que la plateforme contient.

POURQUOI CETTE PAGE, ET PAS UNE CARTE D'IDENTITÉ RÉGIONALE
La monographie interactive publiée sur orvsit.crtta.ma présente déjà la
région : population, superficie, urbanisation, PIB, portrait territorial,
atouts structurants. La refaire ici serait une redite, et la Fiche
territoriale ainsi que Comparer couvrent déjà la lecture par territoire.

La couverture régionale de l'entrepôt est de toute façon inégale : sur les
234 indicateurs publiés, 159 portent une valeur à l'échelle de la région, et
la Santé n'en compte qu'un sur vingt-quatre — la Carte Sanitaire s'arrête aux
provinces. Un portrait régional serait abondant en démographie et muet en
santé.

Reste ce que ni le site public ni les autres pages ne disent : l'état de
l'entrepôt lui-même. Combien d'indicateurs, dans quels secteurs, à quelles
échelles, de quels millésimes et de quelles sources. C'est la seule page qui
décrive le catalogue, et c'est lui qui gouverne toute l'application.

CE QU'ELLE N'AFFICHE PAS
La part d'indicateurs portant une définition rédigée n'y figure pas. C'est
une mesure de complétude interne : utile à qui tient le catalogue, sans
intérêt pour qui consulte la plateforme. Un écran d'accueil n'a pas à exposer
ce qui reste à faire. La mesure garde sa place dans le rapport, parmi les
limites connues.

AUCUN CALCUL
On compte des lignes et on lit des champs. Pas de score, pas d'agrégation de
valeurs, pas d'indice composite. Le décompte est vérifiable ligne à ligne
dans referential.dim_indicateur.
"""

import collections

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_dwh
from ..deps import get_current_user  # réservé aux utilisateurs connectés

router = APIRouter(prefix="/overview", tags=["overview"])

# Les secteurs servis par l'application, dans l'ordre d'affichage.
# « hors secteur » et « non cartographiable » n'en font pas partie : ils
# rassemblent des lignes techniques que l'interface ne propose pas.
SECTEURS = ("Démographie", "Emploi", "Éducation", "Santé", "Conditions de vie")


@router.get("")
def apercu(dwh: Session = Depends(get_dwh), user=Depends(get_current_user)):
    # --- le catalogue ------------------------------------------------------
    # Deux cent vingt et une lignes : on les rapporte et on compte en Python,
    # plutôt que d'écrire en SQL un critère que l'application applique déjà.
    # Le filtre est EXACTEMENT celui de `recherche._lignes`, que l'assistant
    # emploie pour lire le catalogue : secteur servi et disponible à au moins
    # une échelle. Ajouter ici une condition sur le statut donnerait 221 là où
    # l'assistant en sert 224 — trois dénombrements de la Carte Sanitaire
    # portent le statut « denombrement » sans cesser d'être publiés. Deux
    # comptes du même catalogue finiraient par se contredire à l'écran.
    publies = dwh.execute(text("""
        SELECT indicateur_id, secteur, libelle_court, annee, source,
               dispo_province, dispo_commune
        FROM referential.dim_indicateur
        WHERE secteur = ANY(:secteurs)
          AND (dispo_province IS TRUE OR dispo_commune IS TRUE)
    """), {"secteurs": list(SECTEURS)}).mappings().all()

    secteurs = []
    for s in SECTEURS:
        dedans = [l for l in publies if l["secteur"] == s]
        if not dedans:
            continue
        secteurs.append({
            "secteur": s,
            "total": len(dedans),
            "province": sum(1 for l in dedans if l["dispo_province"]),
            "commune": sum(1 for l in dedans if l["dispo_commune"]),
        })

    total = len(publies)

    # --- les territoires servis --------------------------------------------
    territoires = dwh.execute(text("""
        SELECT niveau, count(*) AS n
        FROM referential.dim_territoire
        WHERE niveau IN ('prefecture_province', 'commune')
        GROUP BY niveau
    """)).mappings().all()
    compte = {t["niveau"]: t["n"] for t in territoires}

    # --- les millésimes ----------------------------------------------------
    # `annee` est un texte : une évolution porte « 2020-2024 », une année
    # scolaire « 2023-2024 ». On rend la chaîne telle quelle plutôt que de
    # forcer un entier qui trahirait la donnée.
    millesimes = collections.Counter(l["annee"] for l in publies if l["annee"])

    # --- les sources -------------------------------------------------------
    # Le champ `source` porte l'intitulé complet, souvent suivi d'une URL et
    # d'une note de méthode. On regroupe sur ce qui précède le tiret cadratin,
    # qui sépare partout l'organisme du détail du fichier.
    organismes = collections.Counter(
        (l["source"] or "").split("—")[0].strip()
        for l in publies if (l["source"] or "").strip())

    return {
        "catalogue": {
            "total": total,
            "secteurs": secteurs,
        },
        "territoires": {
            "provinces": compte.get("prefecture_province", 0),
            "communes": compte.get("commune", 0),
        },
        "millesimes": [{"annee": a, "n": n}
                       for a, n in sorted(millesimes.items(), reverse=True)],
        "sources": [{"organisme": o, "n": n}
                    for o, n in organismes.most_common()],
    }
