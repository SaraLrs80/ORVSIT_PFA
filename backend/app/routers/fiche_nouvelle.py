"""
Fiche territoriale — version pilotée par le catalogue.

Différence avec fiche.py : aucun indicateur n'est nommé dans ce fichier.
Le catalogue (referential.dim_indicateur) porte désormais tout ce qu'il
faut pour décider seul de ce qui s'affiche :
  secteur          à quelle rubrique l'indicateur appartient
  libelle_court    ce qu'on écrit à l'écran
  unite            comment on l'écrit
  sens             une valeur haute est-elle favorable
  dispo_province   l'indicateur descend-il au niveau province
  dispo_commune    l'indicateur descend-il au niveau commune

Ajouter un indicateur à l'application ne demande donc plus de toucher au
code : il suffit de l'ajouter au catalogue.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_dwh
from ..deps import get_current_user
import re
from ..referentiel import SECTEURS
# Le découpage en familles et le calcul du millésime vivent dans referentiel.py :
# la recherche de l'assistant s'en sert aussi, et deux implémentations
# finiraient par diverger.
from ..referentiel import cle_famille as _cle_famille
from ..referentiel import millesime_famille as _millesime_famille

router = APIRouter(prefix="/fiche-nouvelle", tags=["fiche territoriale (nouvelle)"])



def _catalogue(dwh: Session, niveau: str):
    """Les indicateurs affichables au niveau demandé, dans l'ordre du catalogue.

    Le filtre sur le niveau se lit directement en base : c'est la colonne
    dispo_commune ou dispo_province qui tranche, pas une liste écrite ici.
    """
    colonne = "dispo_commune" if niveau == "commune" else "dispo_province"
    return dwh.execute(text(f"""
        SELECT indicateur_id, libelle_court, unite, secteur, sens, annee,
               source, definition, theme, table_pg, mode_stockage,
               colonne_valeur, filtre_indicateur
        FROM referential.dim_indicateur
        WHERE secteur = ANY(:secteurs)
          AND {colonne} IS TRUE
        ORDER BY secteur, indicateur_id
    """), {"secteurs": SECTEURS}).mappings().all()


def _familles(lignes):
    """Regroupe les indicateurs du catalogue en familles, dans l'ordre reçu."""
    groupes = {}
    for ligne in lignes:
        cle, typ, etiquette = _cle_famille(ligne["libelle_court"], ligne["secteur"])
        famille = groupes.setdefault(cle, {
            "secteur": cle[0],
            "nom": cle[1],
            "type": typ,
            "unite": ligne["unite"],
            "sens": ligne["sens"],
            "source": ligne["source"],
            "definition": ligne["definition"],
            "membres": [],
            "_annees": [],
        })
        if typ == "ventilation":
            famille["type"] = "ventilation"
        famille["_annees"].append(ligne["annee"])
        famille["membres"].append({
            "indicateur_id": ligne["indicateur_id"],
            "etiquette": etiquette,
            "unite": ligne["unite"],
            "annee": ligne["annee"],   # chaque membre garde le sien
        })

    # Le millésime de la famille se calcule une fois tous les membres connus.
    for famille in groupes.values():
        famille["annee"] = _millesime_famille(famille.pop("_annees"))

    return list(groupes.values())

# Colonnes qui décrivent la structure, jamais une ventilation.
_STRUCTURELLES = {
    "territoire_id", "indicateur", "indicateur_id", "valeur", "fk_territoire",
    "theme", "unite", "territoire", "type_territoire", "annee", "source",
    "code_geo", "collectivite", "cg", "iso",
}

_axes_connus: dict[str, str | None] = {}   # mémoire : une table n'est sondée qu'une fois


def _identifiant(nom: str) -> str:
    """Protège un nom de table ou de colonne venant du catalogue."""
    return '"' + str(nom).replace('"', '""') + '"'


def _axe_de_table(dwh: Session, schema: str, table: str) -> str | None:
    """Nom de la colonne de ventilation de cette table, ou None.

    Définition retenue : une colonne est un axe si elle prend plusieurs
    valeurs pour un même couple (territoire, indicateur). C'est un test sur
    la donnée, pas une liste de noms de colonnes à deviner.
    """
    memo = f"{schema}.{table}"
    if memo in _axes_connus:
        return _axes_connus[memo]

    colonnes = dwh.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = :s AND table_name = :t AND data_type IN ('text','character varying')
    """), {"s": schema, "t": table}).scalars().all()

    axe = None
    for col in colonnes:
        if col in _STRUCTURELLES:
            continue
        multiple = dwh.execute(text(f"""
            SELECT EXISTS (
                SELECT 1 FROM {_identifiant(schema)}.{_identifiant(table)}
                GROUP BY territoire_id, indicateur_id
                HAVING COUNT(DISTINCT {_identifiant(col)}) > 1
            )
        """)).scalar()
        if multiple:
            axe = col
            break

    _axes_connus[memo] = axe
    return axe

def _valeurs(dwh: Session, lignes, territoires: list[int]):
    """{indicateur_id: {modalité: {territoire_id: valeur}}} pour tous les indicateurs.

    Une requête par table de faits, pas une par indicateur : les identifiants
    sont passés en bloc. Trente-six tables suffisent à servir les 193 valeurs.
    """
    par_table: dict[tuple, list[int]] = {}
    for l in lignes:
        theme = l["theme"]                    # le schéma vient du catalogue,
        table = l["table_pg"]                 # jamais d'une découpe du nom
        # le chargeur retire le préfixe du thème, déjà porté par le schéma
        court = table[len(theme) + 1:] if table.startswith(theme + "_") else table
        par_table.setdefault((theme, court), []).append(l["indicateur_id"])

    resultat: dict[int, dict] = {}
    for (schema, table), ids in par_table.items():
        axe = _axe_de_table(dwh, schema, table)
        colonne_axe = f", {_identifiant(axe)} AS modalite" if axe else ""
        rows = dwh.execute(text(f"""
            SELECT indicateur_id, territoire_id, valeur{colonne_axe}
            FROM {_identifiant(schema)}.{_identifiant(table)}
            WHERE indicateur_id = ANY(:ids)
              AND territoire_id = ANY(:terr)
              AND valeur IS NOT NULL
        """), {"ids": ids, "terr": territoires}).mappings().all()

        for r in rows:
            mod = r["modalite"] if axe else "—"
            resultat.setdefault(r["indicateur_id"], {}).setdefault(str(mod), {})[
                str(r["territoire_id"])] = float(r["valeur"])
    return resultat

def _forme(famille, valeurs) -> str:
    """Quelle représentation convient à cette famille.

    Règle centrale : un anneau ou une barre empilée suppose que les parts
    composent un tout. On ne le suppose pas — on additionne et on vérifie.
    """
    membres = famille["membres"]

    if len(membres) == 1:
        return "chiffre"

    if famille["nom"] == "Âge quinquennal":
        return "pyramide"

    if famille["type"] == "modalite" and len(membres) >= 2 \
       and all(m["unite"] == "%" for m in membres):
        totaux: dict[str, float] = {}
        for m in membres:
            series = valeurs.get(m["indicateur_id"], {})
            serie = series.get("Ensemble") or series.get("—") or {}
            for terr, v in serie.items():
                totaux[terr] = totaux.get(terr, 0.0) + v
        if totaux and min(totaux.values()) >= 98 and max(totaux.values()) <= 102:
            return "anneau" if len(membres) <= 3 else "empile"

    if famille["type"] == "ventilation":
        return "groupe"

    return "barres"

# Établir la structure coûte cher — il faut lire toutes les valeurs de tous les
# indicateurs pour décider des formes — et elle ne change qu'avec le catalogue.
# On la garde donc en mémoire, mais indexée sur une EMPREINTE du catalogue et
# non sur le seul niveau : une empreinte différente signale un catalogue modifié
# et le cache se refait de lui-même.
#
# La première version n'indexait que sur le niveau. Conséquence : toute
# correction du catalogue restait invisible tant que le serveur n'était pas
# redémarré, et rien à l'écran ne le disait — on croyait le chargement raté
# alors que la base était juste.
_cache_familles: dict[tuple[str, str], list] = {}


def _empreinte_catalogue(dwh: Session) -> str:
    """Résumé de tout ce dont /familles dépend, en une seule valeur.

    Un md5 sur 327 lignes est négligeable devant la lecture des faits qu'il
    permet d'éviter ; le cache reste donc utile, sans jamais mentir.
    """
    return dwh.execute(text("""
        SELECT md5(string_agg(
                 indicateur_id::text          || '§' || COALESCE(libelle_court, '')
            || '§' || COALESCE(secteur, '')   || '§' || COALESCE(unite, '')
            || '§' || COALESCE(annee::text,'')|| '§' || COALESCE(sens, '')
            || '§' || COALESCE(source, '')    || '§' || COALESCE(definition, '')
            || '§' || COALESCE(dispo_province::text, '')
            || '§' || COALESCE(dispo_commune::text, ''),
            '|' ORDER BY indicateur_id))
        FROM referential.dim_indicateur
    """)).scalar() or ""


def _territoires_du_niveau(dwh: Session, niveau: str) -> list[int]:
    return dwh.execute(text("""
        SELECT territoire_id FROM referential.dim_territoire WHERE niveau = :n
    """), {"n": niveau}).scalars().all()


@router.get("/familles")
def lister_familles(niveau: str = "prefecture_province",
                    dwh: Session = Depends(get_dwh),
                    user=Depends(get_current_user)):
    """Structure de la fiche : quelles familles, quelle forme, quelle source.

    Ne dépend d'aucun territoire : le navigateur peut la garder en mémoire.
    """
    if niveau not in ("prefecture_province", "commune"):
        raise HTTPException(400, "Niveau attendu : prefecture_province ou commune.")

    cle = (niveau, _empreinte_catalogue(dwh))
    if cle in _cache_familles:
        return _cache_familles[cle]

    # Empreinte inconnue. On écarte les structures établies sous une AUTRE
    # empreinte — et elles seules : le navigateur demande les deux niveaux en
    # parallèle, un vidage complet ferait que chacun efface le travail de
    # l'autre. Le nettoyage des axes suit, car une table recréée par le
    # chargeur peut avoir changé de colonnes.
    perimes = [k for k in _cache_familles if k[1] != cle[1]]
    if perimes:
        for k in perimes:
            del _cache_familles[k]
        _axes_connus.clear()

    lignes = _catalogue(dwh, niveau)
    familles = _familles(lignes)
    valeurs = _valeurs(dwh, lignes, _territoires_du_niveau(dwh, niveau))
    for f in familles:
        f["forme"] = _forme(f, valeurs)

    _cache_familles[cle] = familles
    return familles


@router.get("/valeurs")
def lire_valeurs(niveau: str = "prefecture_province",
                 province_id: int | None = None,
                 dwh: Session = Depends(get_dwh),
                 user=Depends(get_current_user)):
    """Valeurs de l'ensemble des pairs, pour tous les indicateurs du niveau.

    Au niveau communal, les pairs sont les communes d'une même province :
    la comparaison ne mélange jamais deux provinces.
    """
    if niveau == "commune":
        if province_id is None:
            raise HTTPException(400, "province_id est requis au niveau communal.")
        pairs = dwh.execute(text("""
            SELECT c.territoire_id, c.nom
            FROM referential.dim_territoire c
            LEFT JOIN referential.dim_territoire pa ON pa.territoire_id = c.parent_id
            WHERE c.niveau = 'commune' AND (c.parent_id = :p OR pa.parent_id = :p)
            ORDER BY c.nom
        """), {"p": province_id}).mappings().all()
    else:
        pairs = dwh.execute(text("""
            SELECT territoire_id, nom FROM referential.dim_territoire
            WHERE niveau = 'prefecture_province' ORDER BY nom
        """)).mappings().all()

    ids = [p["territoire_id"] for p in pairs]
    return {
        "niveau": niveau,
        "territoires": {str(p["territoire_id"]): p["nom"] for p in pairs},
        "valeurs": _valeurs(dwh, _catalogue(dwh, niveau), ids),
    }