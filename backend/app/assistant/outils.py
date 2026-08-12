"""
Les outils de l'assistant conversationnel.

Le modèle ne peut appeler que ces fonctions. Il formule l'intention ; le code
garde la vérité. Un identifiant inventé par un modèle est indétectable : la
requête aboutit et renvoie les chiffres d'un autre territoire, sans que rien
ne le signale. C'est ce que ces fonctions rendent impossible.

"""

import re
import unicodedata
from difflib import get_close_matches

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.referentiel import SECTEURS, NIVEAUX



# « Commune de », « Préfecture d' », précédés ou non d'un article.
# Le mot est capturé et non jeté : il dit le NIVEAU que l'utilisateur vise.
_PREFIXE = re.compile(
    r"^(la |le |les |l')?(?P<type>commune|prefecture|province|municipalite)s?"
    r"\s+(de\s+|d'|du\s+|des\s+)?"
)

_NIVEAU_DU_MOT = {
    "commune": "commune",
    "municipalite": "commune",
    "prefecture": "prefecture_province",
    "province": "prefecture_province",
}


def _sans_accents(nom: str) -> str:
    """Minuscules, accents retirés, apostrophes uniformisées.

    Ces trois nivellements sont du bruit de forme : « Tétouan » et « TETOUAN »
    désignent le même territoire, et l'utilisateur ignore quelle graphie la base
    a retenue. On les efface donc sans rien perdre.
    """
    s = unicodedata.normalize("NFD", str(nom).lower().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("\u2019", "'")


def cle(nom: str) -> str:
    """Le nom réduit à sa forme comparable, sans son préfixe de niveau."""
    s = _PREFIXE.sub("", _sans_accents(nom))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def niveau_demande(nom: str) -> str | None:
    """Le niveau que l'utilisateur a explicitement désigné, ou None.

    C'est l'information que la normalisation aurait détruite. Elle vaut de l'or :
    cinq noms désignent à la fois une province et une commune, et ce seul mot
    tranche sans qu'on ait à poser la question.
    """
    trouve = _PREFIXE.match(_sans_accents(nom))
    return _NIVEAU_DU_MOT.get(trouve.group("type")) if trouve else None

# Les niveaux que l'assistant sait manipuler. Cercles, arrondissements, centres
# urbains et douars existent dans dim_territoire, mais aucun indicateur n'y est
# publié : les proposer reviendrait à promettre des chiffres qui n'existent pas.


_NIVEAU_LISIBLE = {
    "region": "région",
    "prefecture_province": "préfecture ou province",
    "commune": "commune",
}

# Du plus large au plus fin. Ce n'est pas de l'esthétique : l'assistant lit la
# liste des candidats pour formuler sa question, et « la province ou la
# commune ? » se comprend mieux que l'inverse — on nomme d'abord le territoire
# qui contient l'autre. Le tri de la base, lui, range « commune » avant
# « prefecture_province » par simple ordre alphabétique.
_RANG_NIVEAU = {"region": 0, "prefecture_province": 1, "commune": 2}

def _territoires(dwh: Session) -> list[dict]:
    """Les territoires connus, chaqcun accompagné de son nom réduit et de son niveau.
        
    Cent cinquante-cinq lignes, relues à chaque appel plutôt que gardées en
    mémoire. Un cache économiserait quelques millisecondes et coûterait le
    risque de répondre d'après un référentiel périmé : mauvais échange pour un
    outil dont la seule raison d'être est de ne pas se tromper.
    """
    
    lignes = dwh.execute(text("""
        SELECT territoire_id, nom, niveau, parent_id
        FROM referential.dim_territoire
        WHERE niveau = ANY(:niveaux)
        ORDER BY niveau, nom
    """), {"niveaux": list(NIVEAUX)}).mappings().all()
    return [{**ligne, "cle": cle(ligne["nom"])} for ligne in lignes]

def resoudre_territoire(dwh: Session, nom: str, niveau: str | None = None) -> dict:
    """Traduit un nom de territoire en identifiant, ou refuse de trancher.

    Rend toujours la même forme : une liste de candidats, un degré de certitude,
    et une ACTION qui dit au modèle ce qu'il a le droit de faire. C'est cette
    action qui interdit le choix silencieux — le modèle ne décide pas s'il peut
    conclure, l'outil le lui dit.

    `niveau` passé en argument l'emporte sur le mot lu dans le nom : l'appelant
    sait parfois ce que l'utilisateur ignore.
    """
    demande = cle(nom)
    vise = niveau or niveau_demande(nom)
    
    if not demande:
        return {"certitude": "aucune", "action": "aucun", "candidats": [],
                "message": "Aucun nom de territoire n'a été fourni."}
    
    candidats = _territoires(dwh)
    if vise:
        candidats = [t for t in candidats if t["niveau"] == vise]

    # Niveau 1 — correspondance exacte du nom nivelé.
    trouves = [t for t in candidats if t["cle"] == demande]
    certitude = "certain"

    # Niveau 2 — le nom demandé est un morceau d'un nom composé.
    # Sous-ensemble STRICT : avec un sous-ensemble large, l'égalité passerait
    # aussi par ici et le niveau 1 ne servirait à rien.
    if not trouves:
        mots = set(demande.split())
        trouves = [t for t in candidats if mots < set(t["cle"].split())]
        certitude = "probable"

    # Niveau 3 — ressemblance orthographique, en dernier recours seulement.
    # Le seuil de 0,75 est volontairement haut : la base compte des noms très
    # proches — Bni Ahmed, Bni Ammart, Bni Bouchibet — et un seuil permissif
    # confondrait deux communes réelles, ce qui est pire que ne rien trouver.
    if not trouves:
        proches = get_close_matches(demande, [t["cle"] for t in candidats], n=4, cutoff=0.75)
        trouves = [t for t in candidats if t["cle"] in proches]
        certitude = "possible"

    if not trouves:
        return {
            "certitude": "aucune", "action": "aucun", "candidats": [],
            "message": f"Aucun territoire ne correspond à « {nom} ». "
                       f"Ne pas répondre au sujet d'un autre territoire.",
        }

    # Du territoire le plus large au plus fin, avant de rendre la liste :
    # l'assistant la lit dans cet ordre pour formuler sa question.
    trouves.sort(key=lambda t: (_RANG_NIVEAU.get(t["niveau"], 9), t["nom"]))

    # Agir seul suppose une correspondance sûre ET unique.
    demander = len(trouves) > 1 or certitude == "possible"

    if not demander:
        t = trouves[0]
        message = (f"« {nom} » désigne {t['nom']}, "
                   f"{_NIVEAU_LISIBLE[t['niveau']]}. Nommer ce territoire dans la réponse.")
    elif certitude == "possible":
        message = (f"Aucun territoire ne porte exactement le nom « {nom} ». "
                   f"Ceux-ci s'en approchent — demander lequel avant de répondre.")
    else:
        message = (f"« {nom} » peut désigner plusieurs territoires. "
                   f"Demander lequel avant de répondre.")

    return {
        "certitude": certitude,
        "action": "demander" if demander else "utiliser",
        "candidats": [{"territoire_id": t["territoire_id"], "nom": t["nom"],
                       "niveau": t["niveau"], "parent_id": t["parent_id"]}
                      for t in trouves],
        "message": message,
    }
    
def lister_indicateurs(dwh: Session, secteur: str | None = None,
                       niveau: str = "prefecture_province",
                       motif: str | None = None,
                       _replie: bool = False) -> dict:
    """Ce qui existe, pour un niveau et éventuellement un secteur.

    L'inverse de `decrire` : on part d'un secteur et d'un niveau pour arriver à
    une liste. Le modèle pourrait la produire en filtrant le catalogue qu'il a
    sous les yeux, mais ce serait du comptage — et il compte mal. Ici il lit un
    résultat au lieu de le fabriquer.

    Sans secteur ni motif, l'outil ne déverse pas les 217 indicateurs : il rend
    un DÉCOMPTE par secteur. Un outil doit protéger la fenêtre de contexte
    autant que l'exactitude ; deux cents lignes inutiles chassent le catalogue.
    """
    if niveau not in ("prefecture_province", "commune"):
        return {"nombre": 0, "indicateurs": [],
                "message": f"Niveau inconnu : « {niveau} ». "
                           f"Les niveaux servis sont prefecture_province et commune."}

    colonne = "dispo_commune" if niveau == "commune" else "dispo_province"
    lignes = dwh.execute(text(f"""
        SELECT indicateur_id, libelle_court, secteur, unite, annee
        FROM referential.dim_indicateur
        WHERE secteur = ANY(:secteurs) AND {colonne} IS TRUE
        ORDER BY secteur, libelle_court
    """), {"secteurs": SECTEURS}).mappings().all()

    lisible = "au niveau communal" if niveau == "commune" else "au niveau province"

    # Le secteur écrit par le modèle est nivelé comme un nom de territoire :
    # « santé », « Sante » et « SANTÉ » désignent le même secteur, et le modèle
    # n'a pas la graphie exacte sous la main.
    if secteur:
        vise = next((s for s in SECTEURS if cle(s) == cle(secteur)), None)
        if not vise:
            return {"nombre": 0, "indicateurs": [],
                    "message": f"Secteur inconnu : « {secteur} ». "
                               f"Secteurs servis : {', '.join(SECTEURS)}."}
        lignes = [l for l in lignes if l["secteur"] == vise]

    if motif:
        recherche = cle(motif)
        lignes = [l for l in lignes if recherche in cle(l["libelle_court"])]

    # Aucun filtre : on résume au lieu de tout déverser.
    if not secteur and not motif:
        decompte = {}
        for l in lignes:
            decompte[l["secteur"]] = decompte.get(l["secteur"], 0) + 1
        return {
            "nombre": len(lignes),
            "par_secteur": decompte,
            "indicateurs": [],
            "message": f"{len(lignes)} indicateurs publiés {lisible}, répartis par "
                       f"secteur. Demander un secteur pour obtenir la liste détaillée.",
        }

    precisions = ((f" en {secteur}" if secteur else "")
                  + (f" contenant « {motif} »" if motif else ""))

    if not lignes:
        # Rien à ce niveau. Avant de conclure, on regarde à l'autre : répondre
        # « il n'y en a pas » quand la donnée existe une échelle plus bas laisse
        # croire qu'elle n'existe nulle part — et l'utilisateur renonce à une
        # question qui avait une réponse.
        # `_replie` interdit à ce repli de s'appeler lui-même sans fin.
        autre = "commune" if niveau == "prefecture_province" else "prefecture_province"
        if not _replie:
            ailleurs = lister_indicateurs(dwh, secteur=secteur, niveau=autre,
                                          motif=motif, _replie=True)
            if ailleurs["nombre"]:
                mot = "au niveau communal" if autre == "commune" else "au niveau province"
                return {
                    "nombre": 0, "indicateurs": [],
                    "aussi_disponible": {"niveau": autre, "nombre": ailleurs["nombre"],
                                         "indicateurs": ailleurs["indicateurs"]},
                    "message": (f"Aucun indicateur {lisible}{precisions}. "
                                f"En revanche, {ailleurs['nombre']} existe(nt) {mot}. "
                                f"Le signaler et proposer ce niveau, plutôt que de "
                                f"répondre que la donnée n'existe pas."),
                }
        return {"nombre": 0, "indicateurs": [],
                "message": f"Aucun indicateur {lisible}{precisions}. Ne pas en inventer."}

    return {
        "nombre": len(lignes),
        "indicateurs": [dict(l) for l in lignes],
        "message": (f"{len(lignes)} indicateur(s) {lisible}{precisions}. "
                    f"Cette liste est exhaustive : ne pas en citer d'autres."),
    }
    
_LECTURE_DU_SENS = {
    "haut_mieux": "une valeur élevée est favorable",
    "bas_mieux": "une valeur basse est favorable",
    "neutre": "cet indicateur n'a pas de sens favorable : ne jamais le présenter "
              "comme un bon ou un mauvais résultat",
}


def _defaire_definition(texte: str) -> tuple[str, str | None]:
    """Sépare la définition de sa note de traçabilité.

    Le catalogue range les deux dans le même champ, la seconde entre crochets :
    « … Thème : health. [Traçabilité : vérifié 441/441 valeurs.] »
    Les séparer sert les deux familles de questions sans que le modèle ait à
    découper une chaîne — découpage qu'il ferait parfois mal, et sans le dire.
    """
    texte = (texte or "").strip()
    debut = texte.find("[Traçabilité")
    if debut == -1:
        return texte, None
    return texte[:debut].strip(), texte[debut:].strip(" []")


def decrire(dwh: Session, indicateur_id: int) -> dict:
    """Tout ce que le catalogue sait d'un indicateur.

    Ne touche pas aux tables de faits : il décrit l'indicateur, pas un
    territoire. Savoir si une valeur existe pour Chefchaouen est le travail de
    `lire_valeur` — mélanger les deux rendrait chacun moins clair.
    """
    try:
        identifiant = int(indicateur_id)
    except (TypeError, ValueError):
        return {"trouve": False,
                "message": f"« {indicateur_id} » n'est pas un identifiant d'indicateur. "
                           f"Utiliser lister_indicateurs pour en trouver un."}

    ligne = dwh.execute(text("""
        SELECT indicateur_id, libelle_court, secteur, unite, annee, sens,
               source, definition, dispo_province, dispo_commune
        FROM referential.dim_indicateur
        WHERE indicateur_id = :i
    """), {"i": identifiant}).mappings().first()

    if not ligne:
        return {"trouve": False,
                "message": f"Aucun indicateur ne porte l'identifiant {identifiant}. "
                           f"Ne pas inventer sa définition."}

    prov, comm = bool(ligne["dispo_province"]), bool(ligne["dispo_commune"])
    if ligne["secteur"] not in SECTEURS or not (prov or comm):
        return {"trouve": False,
                "message": f"L'indicateur {identifiant} existe en base mais n'est publié "
                           f"à aucun niveau dans l'application. Ne pas le citer."}
        
    definition, tracabilite = _defaire_definition(ligne["definition"])
    couverture = ("aux niveaux province et commune" if prov and comm
                  else "au niveau province uniquement" if prov
                  else "au niveau communal uniquement" if comm
                  else "à aucun niveau")

    return {
        "trouve": True,
        "indicateur_id": ligne["indicateur_id"],
        "libelle": ligne["libelle_court"],
        "secteur": ligne["secteur"],
        "unite": ligne["unite"],
        "millesime": ligne["annee"],
        "definition": definition,
        "tracabilite": tracabilite,
        "source": ligne["source"],
        "sens": {"code": ligne["sens"],
                 "lecture": _LECTURE_DU_SENS.get(ligne["sens"], "sens non déclaré")},
        "couverture": {"province": prov, "commune": comm, "phrase": couverture},
        "message": (f"« {ligne['libelle_court'] } », {ligne['unite'] or 'sans unité'}, "
                    f"millésime {ligne['annee']}, publié {couverture}. "
                    f"Citer la source telle quelle, sans la reformuler."),
    }
    
# Colonnes qui décrivent la structure de la table, jamais une ventilation.
_STRUCTURELLES = {
    "territoire_id", "indicateur", "indicateur_id", "valeur", "fk_territoire",
    "theme", "unite", "territoire", "type_territoire", "annee", "source",
    "code_geo", "collectivite", "cg", "iso",
}


def _identifiant(nom: str) -> str:
    """Protège un nom de table ou de colonne venant du catalogue."""
    return '"' + str(nom).replace('"', '""') + '"'


def lire_valeur(dwh: Session, indicateur_id: int, territoire_id: int,
                ventilation: str | None = None) -> dict:
    """La valeur d'un indicateur pour un territoire — ou la raison de son absence.

    Trois absences existent, et les confondre est ce qui fait qu'un tableau de
    bord ment :

      hors_niveau     l'indicateur n'est pas publié à cette échelle. La Carte
                      Sanitaire ne descend pas à la commune : la donnée n'existe
                      pas, elle n'est pas manquante.
      non_renseigne   il est publié à cette échelle, mais ce territoire n'a pas
                      de valeur.
      zéro            la valeur EST zéro. Ce n'est pas une absence, et l'effacer
                      détruirait une information.

    Le catalogue est consulté AVANT la table de faits, parce que lui seul
    distingue la première de la deuxième : une table vide ne dit pas pourquoi
    elle est vide.
    """
    try:
        ind = int(indicateur_id)
    except (TypeError, ValueError):
        return {"trouve": False, "absence": "identifiant",
                "message": f"« {indicateur_id} » n'est pas un identifiant d'indicateur."}

    c = dwh.execute(text("""
        SELECT indicateur_id, libelle_court, secteur, unite, annee, sens, source,
               theme, table_pg, filtre_indicateur, dispo_province, dispo_commune
        FROM referential.dim_indicateur WHERE indicateur_id = :i
    """), {"i": ind}).mappings().first()
    if not c:
        return {"trouve": False, "absence": "indicateur",
                "message": f"Aucun indicateur ne porte l'identifiant {ind}. "
                           f"Ne pas inventer de valeur."}

    t = dwh.execute(text("""
        SELECT territoire_id, nom, niveau FROM referential.dim_territoire
        WHERE territoire_id = :t
    """), {"t": territoire_id}).mappings().first()
    if not t:
        return {"trouve": False, "absence": "territoire",
                "message": f"Aucun territoire ne porte l'identifiant {territoire_id}."}

    # --- première absence : l'indicateur n'existe pas à cette échelle -------
    publie = (c["dispo_commune"] if t["niveau"] == "commune" else c["dispo_province"])
    if not publie:
        autre = "province" if t["niveau"] == "commune" else "communal"
        ailleurs = (c["dispo_province"] if t["niveau"] == "commune" else c["dispo_commune"])
        return {
            "trouve": False, "absence": "hors_niveau",
            "libelle": c["libelle_court"], "territoire": t["nom"], "niveau": t["niveau"],
            "message": (f"« {c['libelle_court']} » n'est pas publié au niveau "
                        f"{_NIVEAU_LISIBLE[t['niveau']]}. "
                        + (f"Il l'est au niveau {autre} : proposer cette échelle. "
                           if ailleurs else "")
                        + "Ne pas estimer, ne pas répondre zéro."),
        }

    # --- la table de faits --------------------------------------------------
    schema, table = c["theme"], c["table_pg"]
    court = table[len(schema) + 1:] if table.startswith(schema + "_") else table
    rows = dwh.execute(text(f"""
        SELECT * FROM {_identifiant(schema)}.{_identifiant(court)}
        WHERE indicateur_id = :i AND territoire_id = :t AND valeur IS NOT NULL
    """), {"i": ind, "t": t["territoire_id"]}).mappings().all()

    # --- deuxième absence : publié, mais rien pour ce territoire ------------
    if not rows:
        return {
            "trouve": False, "absence": "non_renseigne",
            "libelle": c["libelle_court"], "territoire": t["nom"],
            "message": (f"« {c['libelle_court']} » est publié à cette échelle, mais "
                        f"n'est pas renseigné pour {t['nom']}. Ne jamais présenter "
                        f"cette absence comme un zéro."),
        }

    # --- la ventilation, déduite de ce qui est revenu -----------------------
    # On ne devine pas le nom de la colonne : on regarde laquelle prend
    # plusieurs valeurs pour ce couple indicateur-territoire. C'est un test sur
    # la donnée, pas une liste de noms à maintenir.
    axe = None
    for col in rows[0].keys():
        if col in _STRUCTURELLES or not isinstance(rows[0][col], str):
            continue
        if len({r[col] for r in rows}) > 1 or len(rows) == 1:
            axe = col
            break

    modalites = {str(r[axe]): float(r["valeur"]) for r in rows} if axe \
        else {"—": float(rows[0]["valeur"])}
    choisie = (ventilation if ventilation in modalites
               else next((m for m in modalites if m.lower() in ("ensemble", "total", "—")),
                         list(modalites)[0]))
    valeur = modalites[choisie]
    lisible = _lisible(valeur, c["unite"])
    return {
        "trouve": True, "absence": None,
        "valeur": valeur,
        "valeur_lisible":lisible,
        "unite": c["unite"], "millesime": c["annee"],
        "libelle": c["libelle_court"], "secteur": c["secteur"],
        "territoire": t["nom"], "niveau": t["niveau"],
        "ventilation": {"choisie": choisie, "disponibles": sorted(modalites)},
        "source": c["source"], "sens": c["sens"],
         "message": (f"{c['libelle_court']} pour {t['nom']} : {lisible}, "
                    f"millésime {c['annee']}"
                    + (f", ventilation « {choisie} »" if axe and len(modalites) > 1 else "")
                    + ". Citer le millésime et la source dans la réponse."
                    + (" La valeur est zéro : c'est une valeur, pas une absence."
                       if valeur == 0 else "")),
    }
    
    
def _lisible(valeur: float, unite: str | None) -> str:
    """Une écriture prête à citer, à côté de la valeur exacte.

    Le modèle recopie ce qu'on lui donne. Lui transmettre 12.3816896208345
    revient à lui faire annoncer une précision que la source ne revendique pas :
    le HCP publie un taux, pas quatorze chiffres significatifs.
    On garde la valeur exacte dans la réponse — c'est elle qui sert aux
    classements — et on ajoute la forme lisible pour la phrase.
    """
    if valeur == 0:
        texte = "0"
    elif valeur == int(valeur) and abs(valeur) >= 1:
        texte = f"{int(valeur):,}".replace(",", " ")
    elif abs(valeur) < 1:
        texte = f"{valeur:.3f}".replace(".", ",")
    else:
        texte = f"{valeur:.1f}".replace(".", ",")
    return f"{texte} {unite}".strip() if unite else texte

def classer(dwh: Session, indicateur_id: int, niveau: str = "prefecture_province",
            province_id: int | None = None, ventilation: str | None = None,
            limite: int | None = None) -> dict:
    """Ordonne les territoires d'un même niveau sur un indicateur.

    Deux règles gouvernent cet outil.

    1. LE SENS DÉCIDE DE L'ORDRE. Pour un taux de chômage, être premier c'est
       avoir le taux le plus bas ; pour un taux d'activité, le plus haut. Un
       indicateur « neutre » — un effectif, une contribution — n'a pas de
       meilleur : on le classe par valeur décroissante et on le DIT, plutôt que
       de laisser croire à un palmarès.

    2. UN TERRITOIRE NON RENSEIGNÉ N'ENTRE PAS DANS LE CLASSEMENT, ET ON LE
       COMPTE. C'est le piège de cet outil : un classement qui écarte
       silencieusement quarante communes est juste dans son calcul et faux dans
       sa lecture. Le nombre d'exclus part avec la réponse.
    """
    try:
        ind = int(indicateur_id)
    except (TypeError, ValueError):
        return {"trouve": False, "message": f"« {indicateur_id} » n'est pas un identifiant."}

    if niveau not in ("prefecture_province", "commune"):
        return {"trouve": False,
                "message": f"Niveau inconnu : « {niveau} ». Les niveaux servis sont "
                           f"prefecture_province et commune."}

    c = dwh.execute(text("""
        SELECT indicateur_id, libelle_court, unite, annee, sens, source,
               theme, table_pg, dispo_province, dispo_commune
        FROM referential.dim_indicateur WHERE indicateur_id = :i
    """), {"i": ind}).mappings().first()
    if not c:
        return {"trouve": False,
                "message": f"Aucun indicateur ne porte l'identifiant {ind}."}

    if not (c["dispo_commune"] if niveau == "commune" else c["dispo_province"]):
        return {"trouve": False, "absence": "hors_niveau",
                "message": f"« {c['libelle_court']} » n'est pas publié à ce niveau. "
                           f"Ne pas construire de classement."}

    # --- les pairs. Au niveau communal, ceux d'UNE province : classer les 146
    #     communes de la région mêlerait des territoires que rien ne rend
    #     comparables, et c'est la règle posée dans toute l'application.
    if niveau == "commune":
        if province_id is None:
            return {"trouve": False,
                    "message": "Un classement communal exige une province : les communes "
                               "se comparent entre voisines, pas à l'échelle de la région. "
                               "Demander laquelle."}
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

    if not pairs:
        return {"trouve": False,
                "message": f"Aucun territoire trouvé pour ce niveau."}

    noms = {p["territoire_id"]: p["nom"] for p in pairs}

    # --- une seule lecture pour tous les pairs -----------------------------
    schema, table = c["theme"], c["table_pg"]
    court = table[len(schema) + 1:] if table.startswith(schema + "_") else table
    rows = dwh.execute(text(f"""
        SELECT * FROM {_identifiant(schema)}.{_identifiant(court)}
        WHERE indicateur_id = :i AND territoire_id = ANY(:t) AND valeur IS NOT NULL
    """), {"i": ind, "t": list(noms)}).mappings().all()

    axe = None
    if rows:
        for col in rows[0].keys():
            if col in _STRUCTURELLES or not isinstance(rows[0][col], str):
                continue
            if len({r[col] for r in rows}) > 1:
                axe = col
                break

    par_territoire = {}
    for r in rows:
        mod = str(r[axe]) if axe else "—"
        par_territoire.setdefault(int(r["territoire_id"]), {})[mod] = float(r["valeur"])

    modalites = sorted({m for d in par_territoire.values() for m in d})
    choisie = (ventilation if ventilation in modalites
               else next((m for m in modalites if m.lower() in ("ensemble", "total", "—")),
                         modalites[0] if modalites else "—"))

    classe, absents = [], []
    for tid, nom in noms.items():
        v = par_territoire.get(tid, {}).get(choisie)
        (classe if v is not None else absents).append((tid, nom, v))

    if not classe:
        return {"trouve": False, "absence": "non_renseigne",
                "message": f"« {c['libelle_court']} » n'est renseigné pour aucun "
                           f"territoire de ce niveau. Ne pas construire de classement."}

    # --- le sens décide de l'ordre -----------------------------------------
    croissant = c["sens"] == "bas_mieux"
    classe.sort(key=lambda x: x[2], reverse=not croissant)
    lecture = ("le mieux placé est celui dont la valeur est la plus basse" if croissant
               else "le mieux placé est celui dont la valeur est la plus haute"
               if c["sens"] == "haut_mieux"
               else "classement par valeur décroissante — cet indicateur n'a pas de "
                    "sens favorable, ne pas parler de meilleur ni de pire")

    montres = classe[:limite] if limite else classe
    return {
        "trouve": True,
        "libelle": c["libelle_court"], "unite": c["unite"], "millesime": c["annee"],
        "niveau": niveau, "sens": c["sens"], "source": c["source"],
        "ventilation": {"choisie": choisie, "disponibles": modalites},
        "classement": [
            {"rang": i + 1, "territoire_id": tid, "nom": nom,
             "valeur": v, "valeur_lisible": _lisible(v, c["unite"])}
            for i, (tid, nom, v) in enumerate(montres)
        ],
        "renseignes": len(classe), "total": len(noms),
        "non_renseignes": [nom for _, nom, _ in absents],
        "message": (f"{len(classe)} territoire(s) classé(s) sur {len(noms)} — {lecture}. "
                    + (f"Seuls les {len(montres)} premiers sont rendus. " 
                       if limite and len(montres) < len(classe) else "")
                    + (f"{len(absents)} territoire(s) sans valeur, écarté(s) du "
                       f"classement : ne pas les compter comme des zéros ni les passer "
                       f"sous silence. " if absents else "")
                    + f"Millésime {c['annee']}. Citer la source."),
        }
    
def comparer(dwh: Session, indicateur_ids: list[int], territoire_ids: list[int],
             ventilation: str | None = None) -> dict:
    """Met en regard deux à quatre territoires sur un ou plusieurs indicateurs.

    Il n'invente rien : il appelle `lire_valeur` pour chaque case, et hérite donc
    des trois absences sans avoir à les reprogrammer. Son travail propre tient en
    deux règles.

    1. MÊME NIVEAU, TOUJOURS. Une province et une commune ne sont pas
       comparables — Chefchaouen province est à 12,4 % de pauvreté, sa commune à
       2,5 %. Les mettre côte à côte fabriquerait un écart qui n'existe pas.

    2. L'ÉCART SE MESURE, LE VAINQUEUR SE TAIT SI L'INDICATEUR EST NEUTRE.
       On classe sur l'écart RELATIF — rapporté à la plus grande valeur — parce
       qu'un écart brut fait toujours gagner les grands nombres : « 8 500
       habitants par médecin » écraserait « 12 points de chômage », alors que le
       second parle davantage.
    """
    if not (2 <= len(territoire_ids) <= 4):
        return {"trouve": False,
                "message": "La comparaison porte sur deux à quatre territoires. "
                           "Au-delà, la réponse cesse d'être lisible."}

    territoires = dwh.execute(text("""
        SELECT territoire_id, nom, niveau FROM referential.dim_territoire
        WHERE territoire_id = ANY(:t)
    """), {"t": [int(x) for x in territoire_ids]}).mappings().all()

    manquants = set(map(int, territoire_ids)) - {t["territoire_id"] for t in territoires}
    if manquants:
        return {"trouve": False,
                "message": f"Territoire(s) introuvable(s) : {sorted(manquants)}."}

    niveaux = {t["niveau"] for t in territoires}
    if len(niveaux) > 1:
        return {"trouve": False,
                "message": "Comparaison impossible entre niveaux différents : une "
                           "province et une commune ne se comparent pas. "
                           "Demander lequel des deux niveaux intéresse."}

    # On garde l'ordre demandé : c'est celui de la question de l'utilisateur.
    ordre = {int(t): i for i, t in enumerate(territoire_ids)}
    territoires = sorted(territoires, key=lambda t: ordre[t["territoire_id"]])

    lignes = []
    for ind in indicateur_ids:
        cases, presentes = [], []
        for t in territoires:
            r = lire_valeur(dwh, ind, t["territoire_id"], ventilation)
            cases.append({"territoire_id": t["territoire_id"], "nom": t["nom"],
                          "valeur": r.get("valeur"),
                          "valeur_lisible": r.get("valeur_lisible"),
                          "absence": r.get("absence")})
            if r["trouve"]:
                presentes.append((t["nom"], r["valeur"]))

        premier = lire_valeur(dwh, ind, territoires[0]["territoire_id"], ventilation)
        entete = {"indicateur_id": ind,
                  "libelle": premier.get("libelle"), "unite": premier.get("unite"),
                  "millesime": premier.get("millesime"), "sens": premier.get("sens"),
                  "source": premier.get("source")}

        if len(presentes) < 2:
            lignes.append({**entete, "cases": cases, "comparable": False,
                           "message": "Moins de deux territoires renseignés : "
                                      "rien à comparer sur cet indicateur."})
            continue

        vs = [v for _, v in presentes]
        ecart = max(vs) - min(vs)
        reference = max(abs(v) for v in vs) or 1
        sens = entete["sens"]
        tete = (min(presentes, key=lambda x: x[1]) if sens == "bas_mieux"
                else max(presentes, key=lambda x: x[1]))

        lignes.append({
            **entete, "cases": cases, "comparable": True,
            "ecart": ecart, "ecart_lisible": _lisible(ecart, entete["unite"]),
            "ecart_relatif": round(ecart / reference, 4),
            "en_tete": tete[0] if sens in ("bas_mieux", "haut_mieux") else None,
            "message": (f"Écart de {_lisible(ecart, entete['unite'])}. "
                        + (f"{tete[0]} est le mieux placé. "
                           if sens in ("bas_mieux", "haut_mieux")
                           else f"{max(presentes, key=lambda x: x[1])[0]} a la valeur la "
                                f"plus élevée — cet indicateur n'a pas de sens favorable, "
                                f"ne pas désigner de gagnant. ")),
        })

    comparables = [l for l in lignes if l.get("comparable")]
    comparables.sort(key=lambda l: l["ecart_relatif"], reverse=True)

    return {
        "trouve": True,
        "niveau": niveaux.pop(),
        "territoires": [{"territoire_id": t["territoire_id"], "nom": t["nom"]}
                        for t in territoires],
        "indicateurs": lignes,
        "plus_discriminant": comparables[0]["libelle"] if comparables else None,
        "message": (f"{len(territoires)} territoires comparés sur {len(lignes)} "
                    f"indicateur(s), tous de niveau {niveaux_lisible(territoires)}. "
                    + (f"C'est « {comparables[0]['libelle']} » qui les sépare le plus. "
                       if comparables else "")
                    + "Citer le millésime et la source de chaque indicateur cité."),
    }


def niveaux_lisible(territoires) -> str:
    return _NIVEAU_LISIBLE.get(territoires[0]["niveau"], territoires[0]["niveau"])