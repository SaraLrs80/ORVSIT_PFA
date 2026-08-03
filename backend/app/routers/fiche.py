"""
Fiche territoriale — toutes les données d'un territoire (province ou commune).

Un seul endpoint : GET /fiche/{territoire_id}

Principes de conception :
  - GÉNÉRIQUE : le même code sert une préfecture/province et une commune.
    Ce qui change, c'est la disponibilité des sources (voir DISPONIBILITÉ).
  - AUCUN CALCUL inventé : on ne renvoie que des valeurs officielles lues en
    base. Les seules opérations sont des sommes de comptages d'établissements
    (signalées comme telles) et des soustractions d'écarts côté frontend.
  - TOLÉRANT AUX TROUS : si une source ne couvre pas le territoire demandé,
    la section vaut None au lieu de faire échouer la requête.
  - COMPARAISON ENTRE PAIRS : une province se compare aux 8 provinces, une
    commune aux communes de SA province — jamais à la moyenne régionale, qui
    englobe le territoire lui-même et fausserait la lecture.

DISPONIBILITÉ des sources selon le niveau :
  Donnée                        Province   Commune
  population / ménages             oui       oui
  démographie RGPH (âges, sexe)    oui       oui
  emploi (activité, chômage)       oui       oui
  éducation (taux, niveau)         oui       oui
  établissements scolaires         oui       oui (table dédiée)
  santé : ratios d'offre           oui       non
  santé : privations (MPI)         non       oui
  santé : établissements           oui       oui (RAMED / accouchement / UMP)
  accès des ménages (habitat)      oui       non (remplacé par privations MPI)
  pauvreté multidimensionnelle     non       oui
  transport domicile-travail       oui       oui
  fracture numérique               oui       non
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_dwh
from ..deps import get_current_user

router = APIRouter(prefix="/fiche", tags=["fiche territoriale"])


# ---------------------------------------------------------------- utilitaires

def _f(valeur):
    """Convertit en float, ou None si la valeur est absente/illisible."""
    if valeur is None:
        return None
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return None


def _kv(lignes, cle="indicateur", val="valeur"):
    """Transforme des lignes (indicateur, valeur) en dictionnaire."""
    return {l[cle]: _f(l[val]) for l in lignes}


def _sans_none(d):
    """Retire les clés dont la valeur est None. Renvoie None si tout est vide."""
    propre = {k: v for k, v in d.items() if v is not None}
    return propre or None


# ------------------------------------------------------- territoire et pairs

def _territoire(dwh: Session, tid: int):
    """Identité du territoire + son parent direct."""
    ligne = dwh.execute(text("""
        SELECT t.territoire_id, t.nom, t.niveau, t.parent_id,
               p.nom AS parent_nom, p.niveau AS parent_niveau
        FROM referential.dim_territoire t
        LEFT JOIN referential.dim_territoire p ON p.territoire_id = t.parent_id
        WHERE t.territoire_id = :tid
    """), {"tid": tid}).mappings().first()
    return dict(ligne) if ligne else None


def _province_de(dwh: Session, terr: dict):
    """
    Remonte la hiérarchie jusqu'à la préfecture/province.

    Une commune peut être rattachée soit directement à la province, soit à un
    cercle intermédiaire — d'où la remontée en deux temps.
    """
    if terr["niveau"] == "prefecture_province":
        return terr["territoire_id"]
    parent = terr["parent_id"]
    for _ in range(3):                      # profondeur max : commune -> cercle -> province
        if parent is None:
            return None
        ligne = dwh.execute(text("""
            SELECT territoire_id, niveau, parent_id
            FROM referential.dim_territoire WHERE territoire_id = :p
        """), {"p": parent}).mappings().first()
        if ligne is None:
            return None
        if ligne["niveau"] == "prefecture_province":
            return ligne["territoire_id"]
        parent = ligne["parent_id"]
    return None


def _avec_arrondissements(dwh: Session, tid: int):
    """
    Le territoire, augmenté de ses arrondissements.

    Certaines communes — Tanger notamment — sont découpées en arrondissements
    dans les sources administratives. Leurs équipements y sont donc rattachés,
    et la commune elle-même n'en porte aucun en propre : la fiche de Tanger
    affichait 0 école alors que ses arrondissements en comptent 201.

    ATTENTION : à n'utiliser que pour des COMPTAGES (nombre d'établissements).
    Additionner des taux — chômage, analphabétisme, structure par âge — n'aurait
    aucun sens. Ce n'est d'ailleurs pas nécessaire : les communes concernées
    disposent déjà de leurs propres taux, calculés par la source sur l'ensemble
    de leur territoire.
    """
    lignes = dwh.execute(text("""
        SELECT territoire_id FROM referential.dim_territoire
        WHERE parent_id = :tid AND niveau = 'arrondissement'
    """), {"tid": tid}).mappings().all()
    return [tid] + [l["territoire_id"] for l in lignes]


def _pairs(dwh: Session, terr: dict, province_id):
    """
    Liste des territoires de comparaison (les « pairs »).

    - Une province se compare aux autres préfectures/provinces de la région.
    - Une commune se compare aux communes de SA province (directement rattachées
      ou via un cercle).
    """
    if terr["niveau"] == "prefecture_province":
        lignes = dwh.execute(text("""
            SELECT territoire_id, nom FROM referential.dim_territoire
            WHERE niveau = 'prefecture_province' ORDER BY territoire_id
        """)).mappings().all()
    elif terr["niveau"] == "commune" and province_id is not None:
        lignes = dwh.execute(text("""
            SELECT c.territoire_id, c.nom
            FROM referential.dim_territoire c
            LEFT JOIN referential.dim_territoire pa ON pa.territoire_id = c.parent_id
            WHERE c.niveau = 'commune'
              AND (c.parent_id = :prov OR pa.parent_id = :prov)
            ORDER BY c.territoire_id
        """), {"prov": province_id}).mappings().all()
    else:
        return {}
    return {str(l["territoire_id"]): l["nom"] for l in lignes}


# ------------------------------------------------------------------ sections

def _identite(dwh: Session, tid: int, terr: dict, nb_communes):
    """Population, ménages, répartition urbain/rural, croissance."""
    lignes = dwh.execute(text("""
        SELECT milieu, indicateur, valeur
        FROM demography."demography_population_population_legale_2025_urba"
        WHERE territoire_id = :tid
    """), {"tid": tid}).mappings().all()

    par_milieu = {}
    for l in lignes:
        par_milieu.setdefault(l["milieu"], {})[l["indicateur"]] = _f(l["valeur"])

    ens = par_milieu.get("Ensemble", {})
    urb = par_milieu.get("Urbain", {})
    rur = par_milieu.get("Rural", {})

    population = ens.get("population")
    pop_urbain = urb.get("population")
    pop_rural = rur.get("population")
    taux_urb = None
    if population and pop_urbain is not None:
        taux_urb = round(pop_urbain / population * 100, 1)

    # Taux d'accroissement : disponible seulement au niveau région/province.
    croissance = None
    if terr["niveau"] == "prefecture_province":
        c = dwh.execute(text("""
            SELECT valeur FROM demography."demography_population_population_1"
            WHERE territoire_id = :tid AND milieu = 'Ensemble'
              AND indicateur = 'taux_accroissement_pop_pct'
        """), {"tid": tid}).scalar()
        croissance = _f(c)

    return {
        "population": population,
        "menages": ens.get("menages"),
        "population_urbaine": pop_urbain,
        "population_rurale": pop_rural,
        "taux_urbanisation": taux_urb,
        "croissance_annuelle": croissance,
        "nb_communes": nb_communes,
    }


def _demographie(dwh: Session, tid: int):
    """Sexe, pyramide des âges, état matrimonial, fécondité (RGPH 2024)."""
    lignes = dwh.execute(text("""
        SELECT sexe, indicateur, valeur
        FROM demography."demography_population_rgph2024_population_demogra"
        WHERE territoire_id = :tid
    """), {"tid": tid}).mappings().all()
    if not lignes:
        return None

    par_sexe = {}
    for l in lignes:
        par_sexe.setdefault(l["sexe"], {})[l["indicateur"]] = _f(l["valeur"])
    ens = par_sexe.get("Ensemble", {})
    masc = par_sexe.get("Masculin", {})
    fem = par_sexe.get("Féminin", {})

    tranches = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39",
                "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74"]

    def age(d, tr):
        return d.get(f"Âge quinquennal (%) - {tr} ans")

    pyramide = [
        {"tranche": tr, "hommes": age(masc, tr), "femmes": age(fem, tr)}
        for tr in tranches
    ]
    pyramide.append({
        "tranche": "75+",
        "hommes": masc.get("Âge quinquennal (%) - 75 ans ou plus"),
        "femmes": fem.get("Âge quinquennal (%) - 75 ans ou plus"),
    })

    def matri(d, statut):
        return d.get(f"État matrimonial des 15 ans et plus (%) - {statut}")

    return {
        "population_legale": ens.get("Population légale"),
        "population_municipale": ens.get("Population municipale"),
        "sexe": _sans_none({
            "masculin": ens.get("Sexe (%) - Masculin"),
            "feminin": ens.get("Sexe (%) - Féminin"),
        }),
        "pyramide_ages": pyramide,
        "matrimonial": _sans_none({
            "celibataire": matri(ens, "Célibataire"),
            "marie": matri(ens, "Marié.e"),
            "divorce": matri(ens, "Divorcé.e"),
            "veuf": matri(ens, "Veuf.ve"),
        }),
        "fecondite": _sans_none({
            "indice_conjoncturel": ens.get("Indicateur conjoncturel de fécondité"),
            "descendance_finale": ens.get("Descendance finale des femmes"),
            "age_moyen_mariage": ens.get("Âge moyen singulier au mariage"),
            "age_moyen_mariage_hommes": masc.get("Âge moyen singulier au mariage"),
            "age_moyen_mariage_femmes": fem.get("Âge moyen singulier au mariage"),
        }),
        "population_15_plus": ens.get("Population de 15 ans et plus"),
    }


def _emploi(dwh: Session, tid: int):
    """Activité, chômage et statut professionnel, par sexe (RGPH 2024)."""
    lignes = dwh.execute(text("""
        SELECT sexe, indicateur, valeur
        FROM socio_economic."rgph2024_population_socio_econo_rgph2024_popu"
        WHERE territoire_id = :tid
    """), {"tid": tid}).mappings().all()
    if not lignes:
        return None

    par_sexe = {}
    for l in lignes:
        par_sexe.setdefault(l["sexe"], {})[l["indicateur"]] = _f(l["valeur"])
    ens, masc, fem = par_sexe.get("Ensemble", {}), par_sexe.get("Masculin", {}), par_sexe.get("Féminin", {})

    ACT = "Taux d'activité des 15 ans et plus (%)"
    CHO = "Taux de chômage (%)"
    PREFIXE_STATUT = "Statut professionnel des actifs occupés de 15 ans et plus (%) - "

    def statut(nom):
        return ens.get(PREFIXE_STATUT + nom)

    return {
        "activite": _sans_none({"ensemble": ens.get(ACT), "hommes": masc.get(ACT), "femmes": fem.get(ACT)}),
        "chomage": _sans_none({"ensemble": ens.get(CHO), "hommes": masc.get(CHO), "femmes": fem.get(CHO)}),
        "population_active": ens.get("Population active de 15 ans et plus"),
        "population_active_occupee": ens.get("Population active occupée de 15 ans et plus"),
        "population_inactive": ens.get("Population inactive de 15 ans et plus"),
        "statut_professionnel": _sans_none({
            "employeur": statut("Employeur"),
            "independant": statut("Indépendant"),
            "salarie_public": statut("Salarié du secteur public"),
            "salarie_prive": statut("Salarié du secteur privé"),
            "aide_familial": statut("Aide familial"),
            "apprenti": statut("Apprenti"),
            "cooperateur": statut("Coopérateur/Associé"),
            "autre": statut("Autre"),
        }),
        "prevalence_handicap": ens.get("Taux de prévalence du handicap (%)"),
    }


def _education(dwh: Session, tid: int, niveau: str):
    """Scolarisation, analphabétisme, niveau d'études, établissements scolaires."""
    lignes = dwh.execute(text("""
        SELECT sexe, indicateur, valeur
        FROM education."etab_scoalires_mesures_rgph2024_population_educati"
        WHERE territoire_id = :tid
    """), {"tid": tid}).mappings().all()

    par_sexe = {}
    for l in lignes:
        par_sexe.setdefault(l["sexe"], {})[l["indicateur"]] = _f(l["valeur"])
    ens, masc, fem = par_sexe.get("Ensemble", {}), par_sexe.get("Masculin", {}), par_sexe.get("Féminin", {})

    SCO = "Taux de scolarisation des 6-11 ans en 2023/2024 (%)"
    ANA15 = "Taux d'analphabétisme des 15 ans et plus (%)"
    ANA10 = "Taux d'analphabétisme des 10 ans et plus (%)"
    PREFIXE_NIV = "Niveau d'études dans l'enseignement général (%) - "

    def niv(nom):
        return ens.get(PREFIXE_NIV + nom)

    # --- Établissements scolaires : deux sources aux périmètres DIFFÉRENTS ---
    #
    # 1) Province : le comptage OFFICIEL de l'Annuaire Statistique du Maroc 2024
    #    (année scolaire 2023-2024), qui distingue public et privé.
    # 2) Commune : l'annuaire nominatif du MENPS (open data), qui ne couvre que
    #    le secteur PUBLIC et reflète la situation antérieure à 2022 — c'est la
    #    seule source descendant à la commune.
    #
    # Les deux ne sont volontairement JAMAIS additionnées ni comparées : la somme
    # des communes ne reconstitue pas le total provincial. Chaque chiffre est
    # renvoyé avec sa source pour être affiché tel quel.
    etablissements = None
    if niveau == "prefecture_province":
        off = _kv(dwh.execute(text("""
            SELECT indicateur, valeur FROM education."etablissements_officiel"
            WHERE territoire_id = :tid
        """), {"tid": tid}).mappings().all())
        etablissements = _sans_none({
            "primaire_public": off.get("etab_primaire_public"),
            "primaire_prive": off.get("etab_primaire_prive"),
            "primaire": off.get("etab_primaire_total"),
            "primaire_satellites": off.get("etab_primaire_satellites"),
            "collegial_public": off.get("etab_collegial_public"),
            "collegial_prive": off.get("etab_collegial_prive"),
            "collegial": off.get("etab_collegial_total"),
            "qualifiant_public": off.get("etab_qualifiant_public"),
            "qualifiant_prive": off.get("etab_qualifiant_prive"),
            "qualifiant": off.get("etab_qualifiant_total"),
        })
        if etablissements:
            total = sum(etablissements.get(c) or 0 for c in ("primaire", "collegial", "qualifiant"))
            etablissements["total"] = total or None
            etablissements["source"] = ("Annuaire Statistique du Maroc 2024 (HCP) — "
                                        "année scolaire 2023-2024, public + privé")
    else:
        # On additionne la commune et ses éventuels arrondissements : ce sont des
        # comptages d'établissements, donc la somme est exacte et non estimée.
        etab = _kv(dwh.execute(text("""
            SELECT indicateur, SUM(valeur) AS valeur
            FROM education."indicateur_nombre_etablissements_commune"
            WHERE territoire_id = ANY(:ids) GROUP BY indicateur
        """), {"ids": _avec_arrondissements(dwh, tid)}).mappings().all())

        def cycle(nom):
            return etab.get(f"Nombre d'établissements {nom}")

        etablissements = _sans_none({
            "primaire": cycle("primaire"),
            "collegial": cycle("collegial"),
            "qualifiant": cycle("qualifiant"),
        })
        if etablissements:
            etablissements["total"] = sum(etablissements.values())   # somme de comptages
            etablissements["source"] = ("Annuaire des établissements publics du MENPS "
                                        "(open data, antérieur à 2022) — secteur public uniquement")

    # Privations scolaires (indice de pauvreté HCP) — niveau commune uniquement.
    privations = None
    if niveau == "commune":
        p = _kv(dwh.execute(text("""
            SELECT indicateur, valeur FROM education."pauvrete_communale"
            WHERE territoire_id = :tid
        """), {"tid": tid}).mappings().all())
        privations = _sans_none({
            "scolarisation": p.get("priv_scolarisation"),
            "annees_scolarite": p.get("priv_annees_scolarite"),
            "contribution_mpi": p.get("contrib_education"),
        })

    resultat = {
        "scolarisation_6_11": ens.get(SCO),
        "analphabetisme_15_plus": _sans_none({
            "ensemble": ens.get(ANA15), "hommes": masc.get(ANA15), "femmes": fem.get(ANA15)}),
        "analphabetisme_10_plus": ens.get(ANA10),
        "niveau_etudes": _sans_none({
            "aucun": niv("Aucun niveau d'études"),
            "prescolaire": niv("Préscolaire"),
            "primaire": niv("Primaire"),
            "college": niv("Secondaire collégial"),
            "qualifiant": niv("Secondaire qualifiant"),
            "superieur": niv("Supérieur"),
        }),
        "etablissements": etablissements,
        "privations": privations,
    }
    return resultat if any(v is not None for v in resultat.values()) else None


def _sante(dwh: Session, tid: int, niveau: str):
    """
    Santé : ratios d'offre (province) ou privations MPI (commune),
    plus la liste des établissements présents.
    """
    offre = None
    if niveau == "prefecture_province":
        offre = _sans_none(_kv(dwh.execute(text("""
            SELECT indicateur, valeur FROM health."offre_province"
            WHERE territoire_id = :tid
        """), {"tid": tid}).mappings().all()))

    privations = None
    if niveau == "commune":
        p = _kv(dwh.execute(text("""
            SELECT indicateur, valeur FROM health."pauvrete_communale"
            WHERE territoire_id = :tid
        """), {"tid": tid}).mappings().all())
        privations = _sans_none({
            "mortalite_infantile": p.get("priv_mortalite_infantile"),
            "handicap": p.get("priv_handicap"),
            "contribution_mpi": p.get("contrib_sante"),
        })

    # Établissements de santé recensés.
    # Province : le réseau complet. Commune : les tables qui portent un
    # territoire_id communal (RAMED, maternités, urgences de proximité).
    etablissements = []
    if niveau == "prefecture_province":
        lignes = dwh.execute(text("""
            SELECT "Nom" AS nom, "Catégorie" AS categorie, "Réseau" AS reseau
            FROM health."etablissements_reseau" WHERE territoire_id = :tid
            ORDER BY "Catégorie", "Nom"
        """), {"tid": tid}).mappings().all()
        etablissements = [dict(l) for l in lignes]
    else:
        vus = set()
        for table, source in (("etablissements_ramed", "RAMED"),
                              ("etablissements_accouchement", "Accouchement"),
                              ("etablissements_ump", "Urgences de proximité")):
            try:
                lignes = dwh.execute(text(f"""
                    SELECT "Nom" AS nom, "Catégorie" AS categorie, "Milieu" AS milieu
                    FROM health."{table}" WHERE territoire_id = :tid
                """), {"tid": tid}).mappings().all()
            except Exception:
                continue
            for l in lignes:
                if l["nom"] in vus:
                    continue
                vus.add(l["nom"])
                etablissements.append({**dict(l), "service": source})

    resultat = {"offre": offre, "privations": privations, "etablissements": etablissements}
    return resultat if (offre or privations or etablissements) else None


def _conditions_vie(dwh: Session, tid: int, niveau: str):
    """Accès des ménages (province), privations MPI et pauvreté (commune), transport, numérique."""
    habitat = None
    if niveau == "prefecture_province":
        lignes = dwh.execute(text("""
            SELECT indicateur, valeur FROM socio_economic."conditions_habitat_ensemble"
            WHERE territoire_id = :tid
        """), {"tid": tid}).mappings().all()
        tout = _kv(lignes)

        def contient(*mots):
            for cle, val in tout.items():
                if all(m.lower() in cle.lower() for m in mots):
                    return val
            return None

        habitat = _sans_none({
            "eau_courante": contient("confort", "eau courante"),
            "electricite": contient("confort", "électricité"),
            "assainissement": contient("évacuation", "réseau public"),
            "fosse_septique": contient("évacuation", "fosse septique"),
        })

    pauvrete = privations = None
    if niveau == "commune":
        ig = _kv(dwh.execute(text("""
            SELECT indicateur, valeur FROM socio_economic."pauvrete_communale_indice_global"
            WHERE territoire_id = :tid
        """), {"tid": tid}).mappings().all())
        pauvrete = _sans_none({
            "mpi": ig.get("MPI"),
            "taux_pauvrete": ig.get("taux_pauvrete_H"),
            "intensite": ig.get("intensite_A"),
            "vulnerabilite": ig.get("vulnerabilite"),
        })
        cv = _kv(dwh.execute(text("""
            SELECT indicateur, valeur FROM socio_economic."pauvrete_communale_conditions_vie"
            WHERE territoire_id = :tid
        """), {"tid": tid}).mappings().all())
        privations = _sans_none({
            "eau": cv.get("priv_eau"),
            "electricite": cv.get("priv_electricite"),
            "assainissement": cv.get("priv_assainissement"),
            "logement": cv.get("priv_logement"),
            "cuisson": cv.get("priv_cuisson"),
            "communication": cv.get("priv_communication"),
            "contribution_mpi": cv.get("contrib_conditions_vie"),
        })

    # Transport domicile-travail (région, provinces et communes).
    tr = _kv(dwh.execute(text("""
        SELECT indicateur, valeur FROM socio_economic."transport_domicile_travail"
        WHERE territoire_id = :tid
    """), {"tid": tid}).mappings().all())
    PREFIXE_TR = "Mode de transport (%) - "
    transport = _sans_none({
        "a_pieds": tr.get(PREFIXE_TR + "À pieds"),
        "moto_velo": tr.get(PREFIXE_TR + "Motocycle/ Bicyclette"),
        "voiture": tr.get(PREFIXE_TR + "Voiture privée"),
        "bus": tr.get(PREFIXE_TR + "Bus"),
        "taxi": tr.get(PREFIXE_TR + "Taxi"),
        "employeur": tr.get(PREFIXE_TR + "Transport de l'employeur / Etablissement"),
        "train": tr.get(PREFIXE_TR + "Train"),
        "tram": tr.get(PREFIXE_TR + "Tram"),
        "informel": tr.get(PREFIXE_TR + "Transport informel"),
        "animaux": tr.get(PREFIXE_TR + "Animaux"),
        "autre": tr.get(PREFIXE_TR + "Autre"),
        "ne_se_deplace_pas": tr.get(PREFIXE_TR + "Ne se déplace pas"),
    })

    # Fracture numérique — niveau province uniquement.
    numerique = None
    if niveau == "prefecture_province":
        try:
            ligne = dwh.execute(text("""
                SELECT ordinateur_personnel_pct_5ansplus AS ordinateur,
                       internet_utilisation_pct_5ansplus AS internet
                FROM socio_economic."dataset_fracture_numerique_provinces_2024"
                WHERE territoire_id = :tid
            """), {"tid": tid}).mappings().first()
            if ligne:
                numerique = _sans_none({"ordinateur": _f(ligne["ordinateur"]),
                                        "internet": _f(ligne["internet"])})
        except Exception:
            numerique = None

    resultat = {"habitat": habitat, "pauvrete": pauvrete, "privations": privations,
                "transport": transport, "numerique": numerique}
    return resultat if any(v for v in resultat.values()) else None


# ------------------------------------------------------- comparaison entre pairs

# Indicateurs servant au classement et à la carte.
# sens : 1 = une valeur élevée est favorable, -1 = une valeur élevée est défavorable.
INDICATEURS_PAIRS = [
    {"cle": "chomage", "label": "Taux de chômage", "unite": "%", "sens": -1, "theme": "Emploi"},
    {"cle": "chomage_femmes", "label": "Chômage des femmes", "unite": "%", "sens": -1, "theme": "Emploi"},
    {"cle": "activite", "label": "Taux d'activité", "unite": "%", "sens": 1, "theme": "Emploi"},
    {"cle": "activite_femmes", "label": "Activité des femmes", "unite": "%", "sens": 1, "theme": "Emploi"},
    {"cle": "analphabetisme", "label": "Analphabétisme 15+", "unite": "%", "sens": -1, "theme": "Éducation"},
    {"cle": "scolarisation", "label": "Scolarisation 6-11", "unite": "%", "sens": 1, "theme": "Éducation"},
    {"cle": "superieur", "label": "Niveau supérieur", "unite": "%", "sens": 1, "theme": "Éducation"},
]
INDICATEURS_PROVINCE = [
    {"cle": "eau_courante", "label": "Accès eau courante", "unite": "%", "sens": 1, "theme": "Conditions de vie"},
    {"cle": "assainissement", "label": "Accès assainissement", "unite": "%", "sens": 1, "theme": "Conditions de vie"},
    {"cle": "hab_par_medecin", "label": "Habitants / médecin", "unite": "", "sens": -1, "theme": "Santé"},
    {"cle": "hab_par_lit", "label": "Habitants / lit hospitalier", "unite": "", "sens": -1, "theme": "Santé"},
]
INDICATEURS_COMMUNE = [
    {"cle": "taux_pauvrete", "label": "Taux de pauvreté", "unite": "%", "sens": -1, "theme": "Pauvreté"},
    {"cle": "vulnerabilite", "label": "Vulnérabilité à la pauvreté", "unite": "%", "sens": -1, "theme": "Pauvreté"},
    {"cle": "privation_eau", "label": "Privation d'eau", "unite": "%", "sens": -1, "theme": "Conditions de vie"},
    {"cle": "privation_assainissement", "label": "Privation d'assainissement", "unite": "%", "sens": -1, "theme": "Conditions de vie"},
]


def _valeurs_pairs(dwh: Session, ids, niveau: str):
    """
    Valeurs de chaque indicateur de comparaison, pour tous les pairs.
    Retourne { cle_indicateur : { territoire_id : valeur } }.
    Une seule requête par source (et non une par territoire).
    """
    if not ids:
        return {}
    ids = [int(i) for i in ids]
    valeurs = {}

    def ranger(cle, lignes):
        valeurs.setdefault(cle, {})
        for l in lignes:
            v = _f(l["valeur"])
            if v is not None:
                valeurs[cle][str(l["territoire_id"])] = v

    # Population (contexte).
    ranger("population", dwh.execute(text("""
        SELECT territoire_id, valeur FROM demography."demography_population_population_legale_2025_urba"
        WHERE territoire_id = ANY(:ids) AND milieu = 'Ensemble' AND indicateur = 'population'
    """), {"ids": ids}).mappings().all())

    # Emploi.
    emploi_src = [
        ("chomage", "Ensemble", "Taux de chômage (%)"),
        ("chomage_femmes", "Féminin", "Taux de chômage (%)"),
        ("activite", "Ensemble", "Taux d'activité des 15 ans et plus (%)"),
        ("activite_femmes", "Féminin", "Taux d'activité des 15 ans et plus (%)"),
    ]
    for cle, sexe, indic in emploi_src:
        ranger(cle, dwh.execute(text("""
            SELECT territoire_id, valeur FROM socio_economic."rgph2024_population_socio_econo_rgph2024_popu"
            WHERE territoire_id = ANY(:ids) AND sexe = :sexe AND indicateur = :indic
        """), {"ids": ids, "sexe": sexe, "indic": indic}).mappings().all())

    # Éducation.
    educ_src = [
        ("analphabetisme", "Taux d'analphabétisme des 15 ans et plus (%)"),
        ("scolarisation", "Taux de scolarisation des 6-11 ans en 2023/2024 (%)"),
        ("superieur", "Niveau d'études dans l'enseignement général (%) - Supérieur"),
    ]
    for cle, indic in educ_src:
        ranger(cle, dwh.execute(text("""
            SELECT territoire_id, valeur FROM education."etab_scoalires_mesures_rgph2024_population_educati"
            WHERE territoire_id = ANY(:ids) AND sexe = 'Ensemble' AND indicateur = :indic
        """), {"ids": ids, "indic": indic}).mappings().all())

    if niveau == "prefecture_province":
        # ILIKE (et non LIKE) : PostgreSQL est sensible à la casse, et les
        # libellés source contiennent des majuscules accentuées (« Électricité »).
        ranger("eau_courante", dwh.execute(text("""
            SELECT territoire_id, valeur FROM socio_economic."conditions_habitat_ensemble"
            WHERE territoire_id = ANY(:ids) AND indicateur ILIKE '%confort%eau courante%'
        """), {"ids": ids}).mappings().all())
        ranger("assainissement", dwh.execute(text("""
            SELECT territoire_id, valeur FROM socio_economic."conditions_habitat_ensemble"
            WHERE territoire_id = ANY(:ids) AND indicateur ILIKE '%vacuation%r_seau public%'
        """), {"ids": ids}).mappings().all())
        for cle, indic in (("hab_par_medecin", "hab_par_medecin_public_prive"),
                           ("hab_par_lit", "hab_par_lit_public_prive")):
            ranger(cle, dwh.execute(text("""
                SELECT territoire_id, valeur FROM health."offre_province"
                WHERE territoire_id = ANY(:ids) AND indicateur = :indic
            """), {"ids": ids, "indic": indic}).mappings().all())
    else:
        for cle, indic in (("taux_pauvrete", "taux_pauvrete_H"), ("vulnerabilite", "vulnerabilite")):
            ranger(cle, dwh.execute(text("""
                SELECT territoire_id, valeur FROM socio_economic."pauvrete_communale_indice_global"
                WHERE territoire_id = ANY(:ids) AND indicateur = :indic
            """), {"ids": ids, "indic": indic}).mappings().all())
        for cle, indic in (("privation_eau", "priv_eau"),
                           ("privation_assainissement", "priv_assainissement")):
            ranger(cle, dwh.execute(text("""
                SELECT territoire_id, valeur FROM socio_economic."pauvrete_communale_conditions_vie"
                WHERE territoire_id = ANY(:ids) AND indicateur = :indic
            """), {"ids": ids, "indic": indic}).mappings().all())

    return valeurs


# Tables alimentant chaque section de la fiche. Sert à retrouver les sources
# dans le catalogue : on n'écrit aucune source en dur ici, on lit ce qui est
# déclaré dans referential.dim_indicateur. Mettre le catalogue à jour suffit
# donc à mettre l'affichage à jour.
TABLES_PAR_SECTION = {
    "demographie": ["demography_demography_population_rgph2024_population_demogra",
                    "demography_demography_population_population_legale_2025_urba",
                    "demography_demography_population_population_1"],
    "emploi": ["socio_economic_rgph2024_population_socio_econo_rgph2024_popu"],
    "education": ["education_etab_scoalires_mesures_rgph2024_population_educati",
                  "education_etablissements_officiel",
                  "education_indicateur_nombre_etablissements_commune",
                  "education_pauvrete_communale"],
    "sante": ["health_offre_province", "health_pauvrete_communale",
              "health_etablissements_reseau"],
    "conditions_vie": ["socio_economic_conditions_habitat_ensemble",
                       "socio_economic_pauvrete_communale_indice_global",
                       "socio_economic_pauvrete_communale_conditions_vie",
                       "socio_economic_transport_domicile_travail",
                       "socio_economic_dataset_fracture_numerique_provinces_2024"],
}


def _sources(dwh: Session, niveau: str):
    """
    Sources réellement utilisées par chaque section, lues dans le catalogue.

    On ne retient que les tables pertinentes pour le niveau demandé, pour ne pas
    afficher la source d'une donnée qui n'est pas montrée (par exemple les ratios
    d'offre de soins, absents au niveau commune).
    """
    hors_niveau = ({"education_indicateur_nombre_etablissements_commune",
                    "education_pauvrete_communale",
                    "socio_economic_pauvrete_communale_indice_global",
                    "socio_economic_pauvrete_communale_conditions_vie"}
                   if niveau == "prefecture_province" else
                   {"education_etablissements_officiel", "health_offre_province",
                    "socio_economic_conditions_habitat_ensemble",
                    "socio_economic_dataset_fracture_numerique_provinces_2024",
                    "demography_demography_population_population_1"})

    resultat = {}
    for section, tables in TABLES_PAR_SECTION.items():
        retenues = [t for t in tables if t not in hors_niveau]
        if not retenues:
            continue
        try:
            lignes = dwh.execute(text("""
                SELECT DISTINCT source, annee FROM referential.dim_indicateur
                WHERE table_pg = ANY(:tables) AND source IS NOT NULL AND source <> ''
            """), {"tables": retenues}).mappings().all()
        except Exception:
            continue
        # Plusieurs indicateurs partagent la même publication et ne diffèrent que
        # par le numéro de tableau. On les regroupe en une seule ligne lisible
        # plutôt que d'en afficher dix quasi identiques.
        groupes = {}
        for l in lignes:
            src = (l["source"] or "").strip()
            if not src:
                continue
            base, _, detail = src.partition(" — Tableau")
            base = base.strip()
            # « Tableaux 11-5 et 11-15 » se coupe en « Tableau » + « x 11-5 et 11-15 » :
            # on retire le « x » du pluriel resté collé au début.
            detail = detail.lstrip("x").strip()
            g = groupes.setdefault(base, {"annees": set(), "details": []})
            g["annees"].add(_annee_lisible(l["annee"]))
            for num in detail.replace(" et ", ",").split(","):
                num = num.strip(" .")
                if num and num not in g["details"]:
                    g["details"].append(num)

        propres = []
        for base, g in groupes.items():
            libelle = base
            if g["details"]:
                mot = "Tableaux" if len(g["details"]) > 1 else "Tableau"
                # Tri numérique : « 11-5 » doit précéder « 11-15 ».
                def rang(n):
                    return [int(p) if p.isdigit() else 0 for p in n.replace("-", " ").split()]
                libelle = f"{base} — {mot} {', '.join(sorted(g['details'], key=rang))}"
            annees = sorted(a for a in g["annees"] if a)
            propres.append({"source": libelle, "annee": " / ".join(annees) or None})
        if propres:
            resultat[section] = propres
    return resultat


def _annee_lisible(valeur):
    """Normalise l'année : 2024.0 -> « 2024 », en préservant « 2023-2024 »."""
    if valeur is None:
        return None
    texte = str(valeur).strip()
    if texte.endswith(".0"):
        texte = texte[:-2]
    return texte or None


def _classements(valeurs, definitions, tid):
    """
    Rang du territoire pour chaque indicateur, parmi ses pairs.
    Rang 1 = le mieux placé, selon le sens de l'indicateur.
    """
    resultat = {}
    for d in definitions:
        vals = valeurs.get(d["cle"], {})
        if str(tid) not in vals or len(vals) < 2:
            continue
        ordonne = sorted(vals.items(), key=lambda kv: kv[1], reverse=(d["sens"] == 1))
        rang = [k for k, _ in ordonne].index(str(tid)) + 1
        resultat[d["cle"]] = {"rang": rang, "total": len(ordonne), "valeur": vals[str(tid)]}
    return resultat


# ------------------------------------------------------------------ endpoint

@router.get("/{territoire_id}")
def fiche_territoriale(territoire_id: int,
                       dwh: Session = Depends(get_dwh),
                       user=Depends(get_current_user)):
    """Toutes les données disponibles pour un territoire, prêtes à afficher."""
    terr = _territoire(dwh, territoire_id)
    if terr is None:
        raise HTTPException(404, "Territoire introuvable")
    if terr["niveau"] not in ("prefecture_province", "commune"):
        raise HTTPException(
            400, "La fiche territoriale couvre les préfectures/provinces et les communes.")

    niveau = terr["niveau"]
    province_id = _province_de(dwh, terr)
    pairs_noms = _pairs(dwh, terr, province_id)

    # Nombre de communes rattachées (seulement pour une province).
    nb_communes = len(pairs_noms) if niveau == "prefecture_province" else None
    if niveau == "prefecture_province":
        nb_communes = dwh.execute(text("""
            SELECT COUNT(*) FROM referential.dim_territoire c
            LEFT JOIN referential.dim_territoire pa ON pa.territoire_id = c.parent_id
            WHERE c.niveau = 'commune' AND (c.parent_id = :prov OR pa.parent_id = :prov)
        """), {"prov": territoire_id}).scalar()

    definitions = INDICATEURS_PAIRS + (
        INDICATEURS_PROVINCE if niveau == "prefecture_province" else INDICATEURS_COMMUNE)
    valeurs_pairs = _valeurs_pairs(dwh, pairs_noms.keys(), niveau)

    return {
        "territoire": terr,
        "province_id": province_id,
        "identite": _identite(dwh, territoire_id, terr, nb_communes),
        "demographie": _demographie(dwh, territoire_id),
        "emploi": _emploi(dwh, territoire_id),
        "education": _education(dwh, territoire_id, niveau),
        "sante": _sante(dwh, territoire_id, niveau),
        "conditions_vie": _conditions_vie(dwh, territoire_id, niveau),
        "pairs": {
            "niveau": niveau,
            "noms": pairs_noms,
            "indicateurs": definitions,
            "valeurs": valeurs_pairs,
            "classements": _classements(valeurs_pairs, definitions, territoire_id),
        },
        "sources": _sources(dwh, niveau),
    }


@router.get("")
def lister_territoires_fiche(dwh: Session = Depends(get_dwh), user=Depends(get_current_user)):
    """
    Arborescence province -> communes, pour alimenter les sélecteurs de la fiche.
    """
    provinces = dwh.execute(text("""
        SELECT territoire_id, nom FROM referential.dim_territoire
        WHERE niveau = 'prefecture_province' ORDER BY nom
    """)).mappings().all()

    resultat = []
    for p in provinces:
        communes = dwh.execute(text("""
            SELECT c.territoire_id, c.nom
            FROM referential.dim_territoire c
            LEFT JOIN referential.dim_territoire pa ON pa.territoire_id = c.parent_id
            WHERE c.niveau = 'commune' AND (c.parent_id = :prov OR pa.parent_id = :prov)
            ORDER BY c.nom
        """), {"prov": p["territoire_id"]}).mappings().all()
        resultat.append({
            "territoire_id": p["territoire_id"],
            "nom": p["nom"],
            "communes": [dict(c) for c in communes],
        })
    return resultat
