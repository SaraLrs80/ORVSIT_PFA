"""
Endpoint de la Vue d'ensemble régionale.
Il lit la table pré-calculée referential.idt_territoire (produite par
data-pipeline/calcul_idt.py) et en déduit les indicateurs de synthèse.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_dwh
from ..deps import get_current_user  # réservé aux utilisateurs connectés

router = APIRouter(prefix="/overview", tags=["overview"])

# Population régionale officielle (RGPH 2024). Constante documentée ;
# on pourra la calculer dynamiquement depuis la table de population plus tard.
POPULATION_REGIONALE = 4_030_222

# Seuil en dessous duquel un territoire est considéré « prioritaire » (IDT faible).
SEUIL_PRIORITAIRE = 45

# Répartition urbain/rural de secours (RGPH 2024, HCP : 65,48 % urbain).
# Utilisée seulement si la table démographique n'est pas disponible.
URBAIN_PCT_DEFAUT = 65


def repartition_urbain_rural(dwh: Session):
    """
    Répartition urbain / rural régionale, calculée à partir de la table
    démographique officielle (demography.demo_population_milieu, RGPH 2024, HCP) :
    on lit la population urbaine et rurale de la région (territoire_id = 1).
    Donnée traçable jusqu'à la source, cohérente avec le chiffre HCP (65,48 %).
    """
    try:
        lignes = dwh.execute(text("""
            SELECT indicateur, valeur
            FROM demography.demo_population_milieu
            WHERE territoire_id = 1 AND indicateur IN ('pop_urbain', 'pop_rural')
        """)).mappings().all()
        vals = {l["indicateur"]: float(l["valeur"]) for l in lignes}
        urbain, rural = vals.get("pop_urbain"), vals.get("pop_rural")
        if urbain and rural:
            total = urbain + rural
            return round(urbain / total * 100, 1), round(rural / total * 100, 1)
    except Exception:
        pass
    return URBAIN_PCT_DEFAUT, 100 - URBAIN_PCT_DEFAUT


@router.get("")
def apercu(dwh: Session = Depends(get_dwh), user=Depends(get_current_user)):
    # 1) Le classement des territoires, du plus fort IDT au plus faible.
    #    Les scores sont RELATIFS (min-max 0-100) : 100 = le plus fort des 8,
    #    0 = le plus faible. Les valeurs réelles sont renvoyées dans « details ».
    lignes = dwh.execute(text("""
        SELECT territoire_id, nom,
               score_education, score_conditions_vie, score_sante,
               score_emploi, score_numerique, score_accessibilite, idt
        FROM referential.idt_territoire
        ORDER BY idt DESC
    """)).mappings().all()
    classement = [dict(l) for l in lignes]

    # 2) Indicateurs de synthèse déduits du classement.
    idts = [c["idt"] for c in classement]
    idt_moyen = round(sum(idts) / len(idts), 1) if idts else 0
    ecart_max = round(max(idts) - min(idts), 1) if idts else 0
    zones_prioritaires = [c["nom"] for c in classement if c["idt"] < SEUIL_PRIORITAIRE]

    # 3) Répartition urbain / rural, calculée depuis la table démographique.
    part_urbain, part_rural = repartition_urbain_rural(dwh)

    # 4) Principales disparités (plus gros écarts entre territoires).
    disp = dwh.execute(text("""
        SELECT indicateur, unite, max_nom, max_val, min_nom, min_val, ecart
        FROM referential.disparites
        ORDER BY ecart DESC
    """)).mappings().all()
    disparites = [dict(d) for d in disp]

    # 5) Valeurs RÉELLES par territoire (pour afficher la vraie valeur à côté du
    #    score relatif). On regroupe par territoire_id puis par dimension.
    details = {}
    try:
        lignes_det = dwh.execute(text("""
            SELECT territoire_id, dimension, indicateur, valeur, unite
            FROM referential.idt_details
        """)).mappings().all()
        for d in lignes_det:
            details.setdefault(d["territoire_id"], []).append({
                "dimension": d["dimension"], "indicateur": d["indicateur"],
                "valeur": d["valeur"], "unite": d["unite"],
            })
    except Exception:
        details = {}

    return {
        "population_regionale": POPULATION_REGIONALE,
        "idt_moyen": idt_moyen,
        "ecart_max": ecart_max,
        "nb_zones_prioritaires": len(zones_prioritaires),
        "zones_prioritaires": zones_prioritaires,
        "urbain_rural": {"urbain": part_urbain, "rural": part_rural},
        "disparites": disparites,
        "classement": classement,
        "details": details,
    }
