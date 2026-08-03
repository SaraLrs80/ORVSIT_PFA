"""
Explorer un indicateur — lecture générique du catalogue, thème par thème.

Trois endpoints :
  GET /explorer/{theme}/catalogue
  GET /explorer/{theme}/indicateur/{cle}
  GET /explorer/{theme}/jeu/{table}

Principe : ce router ne connaît AUCUN nom de table en dur. Il lit
referential.dim_indicateur et en déduit quoi interroger. C'est ce qui permet
d'ajouter un thème sans toucher au code.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_dwh
from ..deps import get_current_user

router = APIRouter(prefix="/explorer", tags=["explorer"])

# ---------------------------------------------------------------- liste blanche

def _catalogue(dwh: Session, theme: str) -> list[dict]:
    """
    Toutes les entrées de dim_indicateur pour un thème.

    C'EST NOTRE LISTE BLANCHE. Aucun nom de table ni de colonne n'entrera dans
    une requête SQL sans être d'abord retrouvé ici. On ne maintient donc aucune
    liste de thèmes en dur : le catalogue est la seule source de vérité, et il
    ne peut pas se désynchroniser de lui-même.

    Noter que :theme est bien un paramètre lié — c'est une VALEUR comparée dans
    un WHERE, pas un identifiant. Aucun risque de ce côté.
    """
    lignes = dwh.execute(text("""
        SELECT theme, table_pg, mode_stockage, colonne_valeur, filtre_indicateur,
               nom_indicateur, definition, unite, source, annee, statut
        FROM referential.dim_indicateur
        WHERE theme = :theme
        ORDER BY table_pg, filtre_indicateur
    """), {"theme": theme}).mappings().all()

    if not lignes:
        raise HTTPException(404, f"Thème inconnu ou vide : {theme}")
    return [dict(l) for l in lignes]


def _nom_reel(theme: str, table_pg: str) -> str:
    """
    Nom de la table TEL QU'IL EXISTE dans PostgreSQL.

    charger_postgres.py retire le préfixe du thème avant d'écrire la table,
    puisqu'il devient redondant une fois dans le schéma :
        health_offre_province  ->  health."offre_province"
    Mais huit entrées ne portent pas ce préfixe (demo_population_milieu sous le
    thème demography) : le préfixe n'est donc retiré que s'il est présent.
    C'est exactement la règle de nom_table_pg() côté pipeline — si l'une change,
    l'autre doit changer.
    """
    prefixe = f"{theme}_"
    return table_pg[len(prefixe):] if table_pg.startswith(prefixe) else table_pg


def _identifiant(nom: str) -> str:
    """
    Met un identifiant entre guillemets doubles pour PostgreSQL.

    Indispensable : nos colonnes viennent des CSV et gardent leurs majuscules,
    accents, espaces et points — "Catégorie", "Circ. sanitaire", "Spécialité".
    Sans guillemets, PostgreSQL passe tout en minuscules et ne trouve rien.

    Le doublement des guillemets internes est une ceinture par-dessus la
    bretelle : après la liste blanche, aucun nom hostile ne devrait arriver
    jusqu'ici. Une protection qui ne coûte rien se garde quand même.
    """
    return '"' + nom.replace('"', '""') + '"'


def _resoudre_table(dwh: Session, theme: str, table_pg: str):
    """
    Vérifie qu'une table est bien déclarée pour ce thème, puis renvoie
    son nom qualifié prêt à être concaténé, ainsi que ses entrées de catalogue.

    C'est le SEUL passage par lequel un nom de table peut atteindre le SQL.
    """
    entrees = [e for e in _catalogue(dwh, theme) if e["table_pg"] == table_pg]
    if not entrees:
        raise HTTPException(404, f"Table inconnue pour le thème « {theme} » : {table_pg}")

    schema = entrees[0]["theme"]                      # la valeur réellement chargée
    nom = _nom_reel(schema, table_pg)
    return f"{_identifiant(schema)}.{_identifiant(nom)}", entrees

LABELS_GEO = {"Province", "Commune"}

# Rattachement de chaque territoire à sa province.
#
# Une version précédente le faisait par WITH RECURSIVE côté PostgreSQL. C'était
# élégant, mais deux endpoints en dépendaient et le moindre écart de typage sur
# parent_id — écrit en double precision par le pipeline, parce qu'il contient
# des valeurs nulles — rendait la jointure silencieusement vide : la colonne
# Province s'affichait « — » partout sans qu'aucune erreur ne soit levée.
#
# La hiérarchie fait 3 000 lignes et trois niveaux au plus. La remonter en
# Python coûte quelques millisecondes, se teste hors base, et échoue bruyamment
# plutôt qu'en silence. On préfère cela à une requête plus savante.
def _provinces(dwh: Session) -> dict:
    """{territoire_id : nom de sa province}. Une province se renvoie elle-même."""
    lignes = dwh.execute(text("""
        SELECT territoire_id, parent_id, niveau, nom FROM referential.dim_territoire
    """)).mappings().all()
    info = {int(l["territoire_id"]): l for l in lignes}

    memo: dict = {}

    def remonter(tid, profondeur=0):
        if tid in memo:
            return memo[tid]
        ligne = info.get(tid)
        # La garde de profondeur protège d'un cycle dans le référentiel : sans
        # elle, une boucle parent/enfant ferait tourner la requête à l'infini.
        if ligne is None or profondeur > 8:
            return None
        if ligne["niveau"] == "prefecture_province":
            memo[tid] = ligne["nom"]
            return memo[tid]
        parent = ligne["parent_id"]
        memo[tid] = None if parent is None else remonter(int(parent), profondeur + 1)
        return memo[tid]

    return {tid: remonter(tid) for tid in info}


# ------------------------------------------------------------------- angles
# Les angles sont un choix de PRÉSENTATION, pas un fait sur les données. Ils
# répondent à « quelle question un décideur se pose ? », alors que le catalogue
# répond à « qu'est-ce que cette donnée ? ». Les mélanger obligerait à recharger
# la base pour renommer un onglet.
#
# Règle de regroupement : deux jeux ne sont variantes du même angle que s'ils
# ont le MÊME GRAIN territorial. L'unité, elle, peut varier — à condition
# d'être affichée, d'où le troisième élément de chaque ligne.

ANGLES = {
    "health": [
        {"cle": "acces", "nom": "Accès aux soins", "grain": "province", "sens": "bas_mieux",
         "question": "Combien d'habitants doivent se partager un médecin, un lit, "
                     "une pharmacie ? Plus le chiffre est élevé, plus l'accès est tendu.",
         "tables": [("health_offre_province", "Ratios d'accès", "hab./unité")]},

        {"cle": "etablissements", "nom": "Établissements publics", "grain": "province",
         "question": "Où se trouvent les 365 structures publiques de la région, "
                     "et de quel réseau relèvent-elles : hôpital, soins de base, urgences ?",
         "tables": [("health_etablissements_reseau", "Réseau de soins", "établissement")]},

        {"cle": "proximite", "nom": "Soins de proximité", "grain": "commune",
         "question": "Quelles communes disposent d'un point de soins au plus près "
                     "des habitants — accouchement, RAMED, unité mobile ?",
         "tables": [("health_etablissements_ramed", "Rattachement RAMED", "établissement"),
                    ("health_etablissements_accouchement", "Module d'accouchement", "établissement"),
                    ("health_etablissements_ump", "Unité médicale de proximité", "établissement")]},

        {"cle": "personnel", "nom": "Personnel de santé", "grain": "province",
         "question": "Où sont affectés les 7 300 agents publics de santé de la région, "
                     "et quelles spécialités manquent dans quelle province ?",
         "tables": [("health_professionnels_medicaux_public", "Corps médical", "personne"),
                    ("health_professionnels_paramedicaux_public", "Corps paramédical", "personne"),
                    ("health_corps_technique", "Corps technique", "personne"),
                    ("health_corps_administratif", "Corps administratif", "personne")]},

        {"cle": "plateau", "nom": "Plateau technique", "grain": "province",
         "question": "De quels moyens lourds disposent les hôpitaux : scanners, "
                     "blocs opératoires, salles de radiologie, lits par discipline ?",
         "tables": [("health_equipements_biomedicaux", "Équipements biomédicaux", "équipement"),
                    ("health_lits_par_discipline", "Lits par discipline", "lit"),
                    ("health_salles_bloc_operatoire", "Salles de bloc opératoire", "salle"),
                    ("health_salles_radiologie", "Salles de radiologie", "salle")]},

        {"cle": "prive", "nom": "Secteur privé", "grain": "province",
         "question": "Quelle part de l'offre repose sur le privé, et quels territoires "
                     "n'en bénéficient pas du tout ?",
         "tables": [("health_medecins_prive", "Médecins", "médecin"),
                    ("health_cliniques_nombre", "Cliniques", "clinique"),
                    ("health_cliniques_lits", "Lits de clinique", "lit"),
                    ("health_infrastructures_privees_autres", "Autres infrastructures", "infrastructure")]},

        {"cle": "mobilite", "nom": "Mobilité sanitaire", "grain": "province",
         "question": "Combien d'ambulances et de véhicules sanitaires, et depuis "
                     "quels établissements peuvent-ils partir ?",
         "tables": [("health_mobilite", "Ambulances et véhicules", "véhicule")]},

        {"cle": "privations", "nom": "Privations sanitaires", "grain": "commune", "sens": "bas_mieux",
         "question": "Quelles communes cumulent les privations de santé mesurées par "
                     "le HCP : mortalité infantile, handicap ?",
         "tables": [("health_pauvrete_communale", "Privations", "%")]},
    ],
}
# Nom lisible d'un thème. Le schéma PostgreSQL s'appelle « socio_economic » ;
# personne ne veut lire ça dans un menu.
LIBELLES_THEME = {
    "health": "Santé",
    "education": "Éducation",
    "demography": "Démographie",
    "socio_economic": "Socio-économique",
    "infrastructure": "Infrastructures",
    "climate": "Climat",
}


@router.get("/themes")
def themes(
    dwh: Session = Depends(get_dwh),
    _=Depends(get_current_user),
):
    """
    Les thèmes réellement explorables.

    Un thème n'apparaît que si ses angles sont déclarés dans ANGLES : les
    données peuvent exister en base sans que l'on ait encore décidé comment les
    présenter, et un onglet qui mène à une page vide est pire que pas d'onglet.
    C'est donc cette route qui alimente le menu latéral — il se remplit tout
    seul le jour où un thème est déclaré.
    """
    sortie = []
    for cle in ANGLES:
        lignes = dwh.execute(text("""
            SELECT COUNT(*) FROM referential.dim_indicateur WHERE theme = :t
        """), {"t": cle}).scalar()
        sortie.append({
            "cle": cle,
            "nom": LIBELLES_THEME.get(cle, cle),
            "angles": len(ANGLES[cle]),
            "indicateurs": lignes or 0,
        })
    return sortie


def _angles(dwh: Session, theme: str) -> list[dict]:
    """
    Croise la liste ANGLES avec le catalogue et produit le menu de la page.

    Deux choses se passent ici, et la seconde est la plus importante :
      1. chaque table déclarée est DÉPLIÉE selon son mode_stockage ;
      2. chaque table déclarée est VÉRIFIÉE contre le catalogue. Une faute de
         frappe dans ANGLES lève une erreur immédiate au lieu de produire un
         onglet vide que personne ne remarquerait avant la soutenance.
    """
    catalogue = _catalogue(dwh, theme)
    connues = {e["table_pg"] for e in catalogue}

    resultat = []
    for angle in ANGLES.get(theme, []):
        variantes, sources = [], set()

        for table, libelle, unite in angle["tables"]:
            if table not in connues:
                raise HTTPException(
                    500, f"Angle « {angle['cle']} » : table absente du catalogue : {table}")

            entrees = [e for e in catalogue if e["table_pg"] == table]
            mode = entrees[0]["mode_stockage"]

            if mode == "long":
                # table longue : une variante PAR indicateur empilé dedans
                for e in entrees:
                    variantes.append({
                        "cle": e["filtre_indicateur"],
                        "table": table,
                        "nom": e["nom_indicateur"],
                        "unite": e["unite"] or unite,
                        "mode": mode,
                    })
            else:
                # table brute : la table est elle-même la variante
                variantes.append({
                    "cle": table, "table": table,
                    "nom": libelle, "unite": unite, "mode": mode,
                })

            for e in entrees:
                if e["source"]:
                    annee = str(e["annee"]).replace(".0", "") if e["annee"] else ""
                    sources.add(f"{e['source']} ({annee})" if annee else e["source"])

        resultat.append({
            "cle": angle["cle"],
            "nom": angle["nom"],
            # La question de décision à laquelle l'angle répond. Sans elle, un
            # onglet nommé « Plateau technique » ne dit pas à un élu ce qu'il
            # va y trouver ni pourquoi il devrait le regarder.
            "question": angle.get("question", ""),
            "grain": angle["grain"],
            "variantes": variantes,
            "sources": sorted(sources),
        })
    return resultat



@router.get("/{theme}/catalogue")
def catalogue(
    theme: str,
    dwh: Session = Depends(get_dwh),
    _=Depends(get_current_user),
):
    return {"theme": theme, "angles": _angles(dwh, theme)}


# ------------------------------------------------------------ lecture d'un indicateur

# Colonnes de plomberie : elles décrivent la structure, pas une ventilation.
STRUCTURELLES = {"territoire_id", "indicateur", "valeur", "fk_territoire", "theme", "unite"}

# Libellés employés par les sources pour la ligne « déjà totalisée ». On la
# CHOISIT, on ne la recalcule jamais : additionner des taux n'aurait aucun sens.
TOTAUX = {"ensemble", "total", "les deux sexes", "deux sexes", "tous"}


def _sens_de(theme: str, table_pg: str) -> str:
    """
    « bas_mieux » ou « haut_mieux ».

    Impossible à deviner depuis la donnée : 1 200 habitants par médecin et
    1 200 lits se lisent en sens opposés. C'est donc déclaré dans ANGLES.
    """
    for angle in ANGLES.get(theme, []):
        if any(t[0] == table_pg for t in angle["tables"]):
            return angle.get("sens", "haut_mieux")
    return "haut_mieux"


def _colonnes(dwh: Session, schema: str, table: str) -> list[str]:
    """Colonnes réelles de la table, demandées à PostgreSQL lui-même."""
    return list(dwh.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = :s AND table_name = :t
        ORDER BY ordinal_position
    """), {"s": schema, "t": table}).scalars().all())


def _ventilations(dwh: Session, qualifie: str, colonnes: list[str], cle: str) -> dict:
    """
    Axes selon lesquels cet indicateur est ventilé, et leurs valeurs possibles.

    Définition exacte, sans heuristique : une colonne est un axe si elle prend
    plus d'une valeur À L'INTÉRIEUR d'un même territoire, pour cet indicateur.
    Une colonne constante (« zone = Région TTA ») ne sépare rien : ce n'est
    donc pas un axe, et elle est ignorée.
    """
    axes = {}
    for c in colonnes:
        if c in STRUCTURELLES:
            continue
        col = _identifiant(c)                      # nom venu d'information_schema
        est_axe = dwh.execute(text(f"""
            SELECT EXISTS (SELECT 1 FROM {qualifie}
                           WHERE "indicateur" = :cle
                           GROUP BY territoire_id
                           HAVING COUNT(DISTINCT {col}) > 1)
        """), {"cle": cle}).scalar()
        if est_axe:
            axes[c] = [str(v) for v in dwh.execute(text(f"""
                SELECT DISTINCT {col} FROM {qualifie}
                WHERE "indicateur" = :cle AND {col} IS NOT NULL ORDER BY 1
            """), {"cle": cle}).scalars().all()]
    return axes


def _valeur_totale(valeurs: list[str]) -> str | None:
    """La modalité « Ensemble » si la source en fournit une, sinon None."""
    for v in valeurs:
        if v.strip().lower() in TOTAUX:
            return v
    return None


@router.get("/{theme}/indicateur/{cle}")
def indicateur(
    theme: str,
    cle: str,
    requete: Request,
    dwh: Session = Depends(get_dwh),
    _=Depends(get_current_user),
):
    """
    Une valeur par territoire, pour un indicateur d'une table « longue ».

    GET /explorer/health/indicateur/hab_par_medecin_public_prive
    GET /explorer/socio_economic/indicateur/{cle}?sexe=Féminin&milieu=Rural
    """
    catalogue = _catalogue(dwh, theme)
    entrees = [e for e in catalogue if e["filtre_indicateur"] == cle]
    if not entrees:
        raise HTTPException(404, f"Indicateur inconnu pour « {theme} » : {cle}")

    entree = entrees[0]
    if entree["mode_stockage"] != "long":
        raise HTTPException(400, f"« {cle} » est une table brute : elle se lit par /jeu.")

    qualifie, _e = _resoudre_table(dwh, theme, entree["table_pg"])
    schema = entree["theme"]
    colonnes = _colonnes(dwh, schema, _nom_reel(schema, entree["table_pg"]))
    axes = _ventilations(dwh, qualifie, colonnes, cle)

    # --- choisir une modalité sur chaque axe ---
    choix, a_choisir = {}, []
    for col, valeurs in axes.items():
        demande = requete.query_params.get(col)
        if demande is not None:
            if demande not in valeurs:                       # liste blanche, encore
                raise HTTPException(400, f"« {col} » : valeur inconnue « {demande} ».")
            choix[col] = demande
        elif (total := _valeur_totale(valeurs)) is not None:
            choix[col] = total                               # défaut : la ligne « Ensemble »
        else:
            a_choisir.append(col)                            # aucun total : il faut trancher

    if a_choisir:
        # On ne devine pas. On renvoie la question plutôt qu'une fausse réponse.
        return {"cle": cle, "nom": entree["nom_indicateur"],
                "ventilations": axes, "choix_requis": a_choisir, "valeurs": []}

    conditions = ['f."indicateur" = :cle']
    params = {"cle": cle}
    for i, (col, val) in enumerate(choix.items()):
        conditions.append(f"f.{_identifiant(col)} = :v{i}")   # nom collé, valeur liée
        params[f"v{i}"] = val

    lignes = dwh.execute(text(f"""
        SELECT t.territoire_id, t.nom, t.niveau,
               f.{_identifiant(entree['colonne_valeur'])} AS valeur
        FROM {qualifie} f
        JOIN referential.dim_territoire t ON t.territoire_id = f.territoire_id
        WHERE {' AND '.join(conditions)}
        ORDER BY t.nom
    """), params).mappings().all()

    # La province permet à la page de proposer « seulement les communes de
    # Chefchaouen » : au niveau commune, 146 lignes sans regroupement sont
    # difficiles à parcourir.
    prov = _provinces(dwh)

    # Filet de sécurité : si une ventilation nous avait échappé, on refuse
    # plutôt que d'afficher une ligne prise au hasard.
    vus = set()
    for l in lignes:
        if l["territoire_id"] in vus:
            raise HTTPException(409, f"Plusieurs valeurs subsistent pour « {cle} » : ventilation non résolue.")
        vus.add(l["territoire_id"])

    return {
        "cle": cle,
        "nom": entree["nom_indicateur"],
        "unite": entree["unite"],
        "sens": _sens_de(theme, entree["table_pg"]),
        "source": entree["source"],
        "annee": str(entree["annee"]).replace(".0", "") if entree["annee"] else None,
        "niveau": lignes[0]["niveau"] if lignes else None,
        "ventilations": axes,                  # ce que la page doit proposer
        "ventilation_appliquee": choix,        # ce qui est affiché en ce moment
        "valeurs": [{"territoire_id": l["territoire_id"], "nom": l["nom"],
                     "province": prov.get(l["territoire_id"]),
                     "valeur": float(l["valeur"]) if l["valeur"] is not None else None}
                    for l in lignes],
    }
    # ------------------------------------------------------------------ jeux bruts

# Colonnes qui IDENTIFIENT une ligne au lieu de la CLASSER. Elles restent dans
# les données renvoyées, mais ne peuvent pas servir de filtre : 341 valeurs
# distinctes sur 365 lignes ne filtrent rien.
IDENTIFIANTES = {"Nom", "Code", "territoire_id", "fk_territoire", "theme", "unite"}

# On envoie la table entière et le navigateur filtre : la plus grosse fait 958
# lignes, un aller-retour réseau par case cochée serait absurde. Cette limite
# existe pour que le jour où l'arbitrage cesse d'être valable, on l'apprenne par
# une erreur claire et non par une page qui rame.
MAX_LIGNES = 20_000

# Absences VÉRIFIÉES, à ne pas confondre avec des données manquantes.
# Source : vérification manuelle, juillet 2026. Ces trois provinces n'ont aucune
# clinique privée ; la table source ne contient donc simplement aucune ligne.
# Sans cette déclaration, la carte les laisserait grises « non renseigné », ce
# qui serait faux : nous SAVONS que la valeur est zéro.
ABSENCES_CONFIRMEES = {
    "health_cliniques_nombre": {
        3: "Aucune grande clinique privée à M'diq-Fnideq : l'offre repose sur le public "
           "(Hôpital de proximité Hassan II de Fnideq), le recours privé se fait à Tétouan ou Tanger.",
        5: "Aucune grande clinique privée à Fahs-Anjra : l'offre privée se concentre à Tanger.",
        8: "Aucune clinique privée à Chefchaouen.",
    },
}
ABSENCES_CONFIRMEES["health_cliniques_lits"] = ABSENCES_CONFIRMEES["health_cliniques_nombre"]
# Colonnes de LIBELLÉ géographique : elles répètent, en moins fiable, ce que
# territoire_id dit déjà. Trois provinces sur huit y sont mal orthographiées
# par rapport au référentiel. On les remplace par la jointure.
@router.get("/{theme}/jeu/{table}")
def jeu(
    theme: str,
    table: str,
    dwh: Session = Depends(get_dwh),
    _=Depends(get_current_user),
):
    """
    Les lignes brutes d'une table, avec ses colonnes filtrables.

    GET /explorer/health/jeu/health_etablissements_reseau
    """
    qualifie, entrees = _resoudre_table(dwh, theme, table)
    entree = entrees[0]
    if entree["mode_stockage"] == "long":
        raise HTTPException(400, f"« {table} » est une table longue : elle se lit par /indicateur.")

    schema = entree["theme"]
    colonnes = _colonnes(dwh, schema, _nom_reel(schema, table))
    if "territoire_id" not in colonnes:
        raise HTTPException(500, f"« {table} » n'a pas de colonne territoire_id : non cartographiable.")

    total = dwh.execute(text(f"SELECT COUNT(*) FROM {qualifie}")).scalar()
    if total > MAX_LIGNES:
        raise HTTPException(413, f"« {table} » fait {total} lignes : il faut filtrer côté serveur.")

    # La mesure est ANNONCÉE par le catalogue mais VÉRIFIÉE dans la table :
    # quatre tables d'établissements n'ont pas de colonne Nombre, chaque ligne
    # y est un bâtiment. Dans ce cas la mesure est le comptage des lignes.
    mesure = entree["colonne_valeur"] if entree["colonne_valeur"] in colonnes else None
    gardees = [c for c in colonnes if c not in LABELS_GEO]

    select = ", ".join(f"f.{_identifiant(c)}" for c in gardees)   # noms venus d'information_schema
    brutes = dwh.execute(text(f"""
        SELECT {select},
               t.nom    AS "Territoire",
               t.niveau AS territoire_niveau
        FROM {qualifie} f
        LEFT JOIN referential.dim_territoire t ON t.territoire_id = f.territoire_id
    """)).mappings().all()

    # La province est ajoutée en Python, par la même fonction que /indicateur :
    # une seule façon de faire dans le fichier, donc un seul endroit à corriger.
    prov = _provinces(dwh)
    lignes = [dict(l, Province=prov.get(l["territoire_id"])) for l in brutes]

    niveaux = {l["territoire_niveau"] for l in lignes if l["territoire_niveau"]}
    niveau = niveaux.pop() if len(niveaux) == 1 else (sorted(niveaux)[0] if niveaux else None)

    # « Territoire » n'est ajouté comme filtre qu'au niveau commune : sur une
    # table provinciale, il ferait double emploi avec « Province ».
    geo = ["Province"] + (["Territoire"] if niveau == "commune" else [])
    dimensions = [c for c in gardees if c not in IDENTIFIANTES and c != mesure] + geo
    # Au niveau province, « Territoire » et « Province » désignent la même chose :
    # afficher les deux remplit le tableau d'une colonne qui répète la voisine.
    # On ne garde « Territoire » que là où il apporte une information nouvelle,
    # c'est-à-dire au niveau commune. `geo` porte déjà exactement cette règle.
    colonnes_sortie = [c for c in gardees if c != "territoire_id"] + geo
    absences = [
        {"territoire_id": tid, "nom": nom, "motif": motif}
        for tid, motif in ABSENCES_CONFIRMEES.get(table, {}).items()
        for nom in [dwh.execute(text(
            "SELECT nom FROM referential.dim_territoire WHERE territoire_id = :i"),
            {"i": tid}).scalar()]
    ]

    return {
        "table": table,
        "nom": entree["nom_indicateur"],
        "definition": entree["definition"],
        "mesure": mesure,                    # nom de la colonne à sommer, ou None = compter les lignes
        "niveau": niveau,
        "dimensions": dimensions,            # colonnes proposées comme filtres
        "colonnes": colonnes_sortie,          # toutes, pour le tableau de détail
        "absences_confirmees": absences,     # zéro vérifié ≠ donnée manquante
        "source": entree["source"],
        "annee": str(entree["annee"]).replace(".0", "") if entree["annee"] else None,
        "lignes": lignes,
    }