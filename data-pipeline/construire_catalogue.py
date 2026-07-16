"""
ETAPE 2 (bis) -- CONSTRUCTION du catalogue dim_indicateur + preservation
des tables sources telles quelles (AUCUNE fusion, AUCUN depivotage force).

Principe : chaque source (fichier ou feuille) devient SA PROPRE table,
sauvegardee independamment dans faits/<theme>/<table>.csv, prete a etre
chargee telle quelle dans PostgreSQL (schema = theme, table = nom donne
ici). dim_indicateur ne contient AUCUNE valeur -- juste l'adresse ou
aller chercher chaque indicateur (table, colonne, filtre eventuel).

Prerequis :
    - dim_territoire.csv avec colonnes : territoire_id, nom_normalise,
      code_hcp, code_hcp_douar
    - dossier data/<theme>/*.csv, *.xlsx (meme structure que le diagnostic)

Lancer :
    python construire_catalogue.py data

Produit :
    - dim_indicateur.csv                  (le catalogue/annuaire)
    - faits/<theme>/<table>.csv           (une table par source, territoire_id ajoute)
    - rapport_construction.csv            (ce qui a ete traite, ignore, ou pose probleme)
"""
import pandas as pd
import os
import sys
import re

# Ordre de priorite : le plus GRANULAIRE en premier. C'est la correction du
# bug identifie -- avant, fk_territoire (qui ne descend qu'a la province)
# passait avant cg/code_geo (qui descendent jusqu'a l'arrondissement/douar).
TERRITOIRE_COLS = ["code_geo_douar", "code_geo", "cg", "territoire_code", "fk_territoire"]

THEMES_VALIDES = {"demography", "education", "health", "infrastructure", "climate", "socio_economic"}
NOMS_FEUILLES_A_IGNORER = re.compile(r"^(readme|notes?|concept|d[ée]finitions?|sheet\d*|feuil\d*)$", re.IGNORECASE)
COLONNES_NON_MESURE = set(TERRITOIRE_COLS + ["id", "collectivite", "region", "province_prefecture",
                           "territoire", "territoire_brut", "milieu", "sexe", "annee", "unite", "source",
                           "theme", "indicateur", "valeur", "sous_categorie", "cercle", "commune_rurale",
                           "fraction", "douar", "type_douar", "station", "aeroport", "distributeur",
                           "categorie", "categorie_qualite", "territoire_id", "fichier_source", "type_territoire"])


def slugify(s):
    s = str(s).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_")[:60]


def nettoyer_indicateur(v):
    v = str(v).replace("_x000D_", " ").replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", v).strip()


def code_to_str(x):
    if pd.isna(x):
        return None
    try:
        return str(int(float(x)))
    except (ValueError, TypeError):
        return str(x).strip()


# ---------------------------------------------------------------------------
# Chargement (identique aux scripts precedents)
# ---------------------------------------------------------------------------
def charger_sources(chemin, fichier):
    ext = os.path.splitext(fichier)[1].lower()
    if ext == ".csv":
        try:
            df = pd.read_csv(chemin, encoding="utf-8-sig", sep=None, engine="python", nrows=200000)
            return [(fichier, df)]
        except Exception as e:
            return [(fichier, None, str(e))]
    if ext == ".xlsx":
        try:
            xls = pd.ExcelFile(chemin, engine="openpyxl")
        except Exception as e:
            return [(fichier, None, str(e))]
        sources = []
        for feuille in xls.sheet_names:
            if len(xls.sheet_names) > 1 and NOMS_FEUILLES_A_IGNORER.match(feuille.strip()):
                continue
            try:
                df = xls.parse(feuille, nrows=200000)
            except Exception as e:
                sources.append((f"{fichier}::{feuille}", None, str(e)))
                continue
            if len(df) < 1 or df.shape[1] < 2:
                continue
            nom_source = fichier if len(xls.sheet_names) == 1 else f"{fichier}::{feuille}"
            sources.append((nom_source, df))
        return sources
    return []


# ---------------------------------------------------------------------------
# Rattachement territoire -- CORRIGE : priorite au plus granulaire
# ---------------------------------------------------------------------------
def construire_lookups(dim_territoire):
    dim_territoire = dim_territoire.copy()
    dim_territoire["code_hcp_str"] = dim_territoire["code_hcp"].apply(code_to_str)
    dim_territoire["code_hcp_douar_str"] = dim_territoire["code_hcp_douar"].apply(code_to_str)
    return {
        "fk_territoire": dict(zip(dim_territoire["nom_normalise"], dim_territoire["territoire_id"])),
        "territoire_code": dict(zip(dim_territoire["nom_normalise"], dim_territoire["territoire_id"])),
        "code_geo": dict(zip(dim_territoire["code_hcp_str"], dim_territoire["territoire_id"])),
        "cg": dict(zip(dim_territoire["code_hcp_str"], dim_territoire["territoire_id"])),
        "code_geo_douar": dict(zip(dim_territoire["code_hcp_douar_str"], dim_territoire["territoire_id"])),
    }


def normaliser_notation_hierarchique(serie):
    """
    Certains fichiers (migration, population_legale_2025) codent le territoire en
    notation hierarchique a points, ex: '01.511.01.05' pour Arrondissement de Mghogha,
    au lieu du code plat '15110105' utilise par dim_territoire. Detecte cette notation
    (>=2 points sur au moins une valeur de la colonne) et la convertit vers le code plat.
    Si la colonne n'utilise pas cette notation, la retourne inchangee.
    """
    valeurs = serie.dropna().astype(str)
    if valeurs.empty or valeurs.str.count(r"\.").max() < 2:
        return serie  # pas de notation hierarchique detectee, rien a faire

    def convertir(v):
        s = str(v).strip().replace(".", "")
        return s.lstrip("0") or "0"
    return serie.apply(lambda v: convertir(v) if pd.notna(v) else v)


def rattacher_territoire(df, lookups):
    if "territoire_id" in df.columns:
        return df, "territoire_id"  # deja calcule -- voir avertissement dans le rapport final
    territoire_col = next((c for c in TERRITOIRE_COLS if c in df.columns), None)
    if territoire_col is None:
        return df, None
    lut = lookups[territoire_col]
    if territoire_col in ("fk_territoire", "territoire_code"):
        df["territoire_id"] = df[territoire_col].apply(lambda v: lut.get(str(v).strip()) if pd.notna(v) else None)
    else:
        colonne_normalisee = normaliser_notation_hierarchique(df[territoire_col])
        df["territoire_id"] = colonne_normalisee.apply(lambda v: lut.get(code_to_str(v)))
    return df, territoire_col


# ---------------------------------------------------------------------------
# Catalogage -- AUCUN depivotage. Le format natif (long ou large) est preserve.
# ---------------------------------------------------------------------------
def cataloguer_source(df, theme, nom_source, table_pg, dossier_faits):
    entries = []

    if "indicateur" in df.columns and "valeur" in df.columns:
        # --- Format long : deja indicateur/valeur, une ligne dim_indicateur par valeur distincte ---
        df["indicateur"] = df["indicateur"].apply(nettoyer_indicateur)
        df["valeur"] = pd.to_numeric(df["valeur"], errors="coerce")
        for indic in sorted(df["indicateur"].dropna().unique()):
            unite = ""
            if "unite" in df.columns:
                u = df.loc[df["indicateur"] == indic, "unite"].dropna()
                unite = u.iloc[0] if len(u) else ""
            entries.append({
                "nom_indicateur": indic, "theme": theme, "table_pg": table_pg,
                "mode_stockage": "long", "colonne_valeur": "valeur",
                "filtre_indicateur": indic, "colonne_territoire": "territoire_id", "unite": unite,
            })
    else:
        # --- Format large : chaque colonne de mesure = un indicateur, la table n'est PAS depivotee ---
        mesure_cols = [c for c in df.columns if c not in COLONNES_NON_MESURE]
        for col in mesure_cols:
            if pd.to_numeric(df[col], errors="coerce").notna().sum() == 0:
                continue  # colonne texte, pas une mesure (ex: nom d'etablissement)
            entries.append({
                "nom_indicateur": col, "theme": theme, "table_pg": table_pg,
                "mode_stockage": "large", "colonne_valeur": col,
                "filtre_indicateur": None, "colonne_territoire": "territoire_id", "unite": "",
            })

    os.makedirs(f"{dossier_faits}/{theme}", exist_ok=True)
    if not entries:
        return entries  # aucune colonne numerique exploitable (ex: annuaire d'etablissements) -> ne rien sauvegarder
    df.to_csv(f"{dossier_faits}/{theme}/{table_pg}.csv", index=False, encoding="utf-8-sig")
    return entries


# ---------------------------------------------------------------------------
# Boucle principale
# ---------------------------------------------------------------------------
def main(dossier_racine, dim_territoire_path="dim_territoire.csv", dossier_faits="faits"):
    dim_territoire = pd.read_csv(dim_territoire_path)
    for col in ["territoire_id", "nom_normalise", "code_hcp", "code_hcp_douar"]:
        if col not in dim_territoire.columns:
            print(f"ERREUR : dim_territoire.csv doit contenir la colonne '{col}'")
            return
    lookups = construire_lookups(dim_territoire)

    dim_indicateur_rows = []
    rapport = []
    tables_vues = set()

    for theme in sorted(os.listdir(dossier_racine)):
        chemin_theme = os.path.join(dossier_racine, theme)
        if not os.path.isdir(chemin_theme) or theme not in THEMES_VALIDES:
            continue

        for fichier in sorted(os.listdir(chemin_theme)):
            if not (fichier.endswith(".csv") or fichier.endswith(".xlsx")) or fichier.startswith("~$"):
                continue
            chemin = os.path.join(chemin_theme, fichier)

            for source_result in charger_sources(chemin, fichier):
                if len(source_result) == 3:
                    nom_source, _, erreur = source_result
                    rapport.append({"theme": theme, "source": nom_source, "statut": "ERREUR_LECTURE", "detail": erreur})
                    continue
                nom_source, df = source_result

                deja_calcule = "territoire_id" in df.columns
                df, territoire_col = rattacher_territoire(df, lookups)
                if territoire_col is None:
                    print(f"  [IGNORE] {theme}/{nom_source} : aucune colonne territoire")
                    rapport.append({"theme": theme, "source": nom_source, "statut": "IGNORE_SANS_TERRITOIRE", "detail": ""})
                    continue

                avant = len(df)
                df = df.dropna(subset=["territoire_id"])
                perdu = avant - len(df)

                table_pg = slugify(f"{theme}_{nom_source.split('::')[0].replace('.csv', '').replace('.xlsx', '')}")
                if "::" in nom_source:
                    table_pg = slugify(table_pg + "_" + nom_source.split("::")[1])
                if table_pg in tables_vues:
                    i = 2
                    while f"{table_pg}_{i}" in tables_vues:
                        i += 1
                    table_pg = f"{table_pg}_{i}"
                tables_vues.add(table_pg)

                entries = cataloguer_source(df, theme, nom_source, table_pg, dossier_faits)
                if not entries:
                    print(f"  [IGNORE_PAS_UN_INDICATEUR] {theme}/{nom_source} : aucune colonne numerique "
                          f"exploitable (probablement un annuaire/liste, ex: etablissements) -- "
                          f"a deplacer vers referential/ si c'est le cas")
                    rapport.append({"theme": theme, "source": nom_source, "statut": "IGNORE_PAS_UN_INDICATEUR", "detail": ""})
                    continue
                dim_indicateur_rows.extend(entries)

                statut = "OK"
                if perdu == avant and avant > 0:
                    statut = "ALERTE_100PCT_PERDU"
                elif perdu > 0:
                    statut = "OK_AVEC_PERTES_PARTIELLES"
                if deja_calcule:
                    statut += "_TERRITOIRE_ID_PRECALCULE_NON_REVERIFIE"

                print(f"  [{statut}] {theme}/{nom_source} -> table '{table_pg}' "
                      f"({len(df)}/{avant} lignes gardees, {len(entries)} indicateurs, via '{territoire_col}')")
                rapport.append({"theme": theme, "source": nom_source, "table_pg": table_pg, "statut": statut,
                                 "lignes_gardees": len(df), "lignes_avant": avant,
                                 "nb_indicateurs": len(entries), "colonne_territoire_utilisee": territoire_col})

    dim_indicateur = pd.DataFrame(dim_indicateur_rows).drop_duplicates(subset=["theme", "table_pg", "nom_indicateur", "filtre_indicateur"])
    dim_indicateur.insert(0, "indicateur_id", range(1, len(dim_indicateur) + 1))
    dim_indicateur.to_csv("dim_indicateur.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(rapport).to_csv("rapport_construction.csv", index=False, encoding="utf-8-sig")

    print(f"\n{'='*70}")
    print(f"dim_indicateur.csv : {len(dim_indicateur)} indicateurs, pointant vers {len(tables_vues)} tables")
    print(f"Tables sauvegardees dans : {dossier_faits}/<theme>/<table>.csv")
    alertes = [r for r in rapport if r.get('statut', '').startswith('ALERTE')]
    if alertes:
        print(f"\n🔴 {len(alertes)} source(s) avec 100% de perte -- a verifier :")
        for a in alertes:
            print(f"   {a['theme']}/{a['source']}")
    print(f"{'='*70}")


if __name__ == "__main__":
    dossier = sys.argv[1] if len(sys.argv) > 1 else "data"
    main(dossier)
