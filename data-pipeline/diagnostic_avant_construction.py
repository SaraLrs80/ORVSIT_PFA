"""
ETAPE 1 -- DIAGNOSTIC (lecture seule, ne modifie et n'ecrit AUCUN fichier de donnees)

Objectif : verifier que chaque fichier CSV/XLSX est pret pour la construction de
dim_indicateur et des tables de faits, AVANT de construire quoi que ce soit.

Supporte .csv ET .xlsx. Pour un .xlsx, CHAQUE feuille non-vide est diagnostiquee
separement (une feuille = une "source" potentielle), les feuilles manifestement
vides ou de type "readme"/"notes" sont ignorees automatiquement.

Structure attendue :
    dossier_racine/
        demography/   *.csv, *.xlsx
        education/    *.csv, *.xlsx
        health/       *.csv, *.xlsx
        infrastructure/ *.csv, *.xlsx
        climate/      *.csv, *.xlsx
        socio_economic/ *.csv, *.xlsx
        referential/  *.csv, *.xlsx   (ignore : ce sont des dimensions, pas des faits)

Le nom du DOSSIER = le theme. Le nom du FICHIER (+ feuille si xlsx) = la source.

Lancer :
    python diagnostic_avant_construction.py /chemin/vers/dossier_racine

Ne modifie rien. Produit uniquement un rapport a l'ecran + diagnostic_rapport.csv
"""
import pandas as pd
import os
import sys
import re

TERRITOIRE_COLS = ["fk_territoire", "code_geo", "cg", "code_geo_douar", "territoire_code"]
THEMES_VALIDES = {"demography", "education", "health", "infrastructure", "climate", "socio_economic", "referential"}

# Feuilles a ignorer automatiquement (readme, notes, feuilles vides Excel par defaut)
NOMS_FEUILLES_A_IGNORER = re.compile(r"^(readme|notes?|concept|d[ée]finitions?|sheet\d*|feuil\d*)$", re.IGNORECASE)


def charger_sources(chemin, fichier):
    """
    Retourne une liste de (nom_source, DataFrame) a diagnostiquer.
    Pour un .csv : une seule source.
    Pour un .xlsx : une source par feuille "utile" (non vide, pas un readme).
    """
    ext = os.path.splitext(fichier)[1].lower()

    if ext == ".csv":
        try:
            # detection automatique du separateur (virgule ou point-virgule, cas frequent
            # avec Excel FR qui exporte en ';') plutot que de supposer la virgule
            df = pd.read_csv(chemin, encoding="utf-8-sig", sep=None, engine="python", nrows=100000)
            return [(fichier, df)]
        except Exception as e:
            return [(fichier, None, str(e))]

    if ext == ".xlsx":
        try:
            xls = pd.ExcelFile(chemin, engine="openpyxl")
        except Exception as e:
            return [(fichier, None, str(e))]

        sources = []
        feuilles_a_considerer = xls.sheet_names
        for feuille in feuilles_a_considerer:
            # on n'ignore par le NOM que s'il y a d'autres feuilles dans le fichier --
            # si "Sheet1"/"Feuil1" est la SEULE feuille, c'est tres probablement la vraie
            # donnee (nom par defaut d'un export pandas/Excel), pas un readme a sauter
            if len(feuilles_a_considerer) > 1 and NOMS_FEUILLES_A_IGNORER.match(feuille.strip()):
                continue
            try:
                df = xls.parse(feuille, nrows=100000)
            except Exception as e:
                sources.append((f"{fichier}::{feuille}", None, str(e)))
                continue
            # feuille vide ou quasi-vide (0-1 ligne de donnees, ou 1 seule colonne -> probablement du texte libre)
            if len(df) < 1 or df.shape[1] < 2:
                continue
            nom_source = fichier if len(xls.sheet_names) == 1 else f"{fichier}::{feuille}"
            sources.append((nom_source, df))

        if not sources:
            return [(fichier, None, "Aucune feuille exploitable trouvee (toutes vides ou ignorees)")]
        return sources

    return []  # extension non geree


def diagnostiquer_dataframe(df, source, theme):
    pb = []
    warn = []
    info = {}

    n = len(df)
    cols = list(df.columns)

    # 1. Format A ou B ?
    format_detecte = "A (long)" if "indicateur" in cols else "B (large)"
    info["format"] = format_detecte

    # 2. Colonne territoire presente ?
    territoire_col = next((c for c in TERRITOIRE_COLS if c in cols), None)
    if territoire_col is None:
        pb.append("Aucune colonne territoire trouvee (fk_territoire / code_geo / cg / code_geo_douar)")
    else:
        info["territoire_col"] = territoire_col
        taux_rempli = df[territoire_col].notna().mean() * 100
        if taux_rempli < 50:
            warn.append(f"Colonne territoire '{territoire_col}' remplie a seulement {taux_rempli:.0f}%")

    # 3. Format A : verifier indicateur + valeur
    if format_detecte == "A (long)":
        if "valeur" not in cols:
            pb.append("Colonne 'indicateur' presente mais pas de colonne 'valeur'")
        else:
            non_num = pd.to_numeric(df["valeur"], errors="coerce").isna() & df["valeur"].notna()
            if non_num.sum() > 0:
                warn.append(f"{non_num.sum()} valeurs dans 'valeur' ne sont pas numeriques")
        if "indicateur" in cols:
            vals = df["indicateur"].dropna().astype(str)
            nettoye = vals.str.strip().str.replace(r"\s+", " ", regex=True)
            suspects = set(vals[vals != nettoye].unique())
            if suspects:
                warn.append(f"{len(suspects)} valeurs 'indicateur' avec espaces/retours a la ligne mal nettoyes")
            if vals.str.contains("_x000", regex=False).any():
                pb.append("Artefacts d'encodage Excel detectes dans 'indicateur' (_x000D_ ou similaire)")
            n_indic = nettoye.nunique()
            info["nb_indicateurs_distincts"] = n_indic

    # 4. Format B : verifier noms de colonnes propres
    if format_detecte == "B (large)":
        mesure_cols = [c for c in cols if c not in TERRITOIRE_COLS + ["id", "collectivite", "region",
                       "province_prefecture", "territoire", "milieu", "sexe", "annee", "unite", "source", "theme"]]
        suspectes = [c for c in mesure_cols if re.match(r"^(col|column|unnamed)[\s_]*\d*$", str(c).lower())]
        if suspectes:
            pb.append(f"Noms de colonnes non explicites : {suspectes}")
        info["nb_colonnes_mesure"] = len(mesure_cols)

    # 5. Colonnes optionnelles presentes ?
    for c in ["annee", "sexe", "milieu", "unite"]:
        info[f"a_{c}"] = "oui" if c in cols else "non"

    statut = "BLOQUANT" if pb else ("A_VERIFIER" if warn else "OK")
    return {"fichier": source, "theme": theme, "statut": statut,
            "problemes": " | ".join(pb), "avertissements": " | ".join(warn),
            "lignes": n, **info}


def main(dossier_racine):
    rapports = []
    for theme in sorted(os.listdir(dossier_racine)):
        chemin_theme = os.path.join(dossier_racine, theme)
        if not os.path.isdir(chemin_theme):
            continue
        if theme not in THEMES_VALIDES:
            print(f"[IGNORE] Dossier '{theme}' non reconnu comme theme (ignore)")
            continue
        if theme == "referential":
            continue  # dimensions, pas des faits

        for fichier in sorted(os.listdir(chemin_theme)):
            if not (fichier.endswith(".csv") or fichier.endswith(".xlsx")):
                continue
            if fichier.startswith("~$"):
                continue  # fichier temporaire Excel (ouvert ailleurs)
            chemin = os.path.join(chemin_theme, fichier)

            for source_result in charger_sources(chemin, fichier):
                if len(source_result) == 3:
                    nom_source, _, erreur = source_result
                    rapports.append({"fichier": nom_source, "theme": theme, "statut": "ERREUR_LECTURE",
                                      "problemes": f"Impossible de lire : {erreur}",
                                      "avertissements": "", "lignes": 0})
                    continue
                nom_source, df = source_result
                rapports.append(diagnostiquer_dataframe(df, nom_source, theme))

    df_rapport = pd.DataFrame(rapports)

    if df_rapport.empty:
        print("\nAucun fichier .csv/.xlsx trouve dans les sous-dossiers de theme.")
        print("Verifiez le chemin fourni et la presence de sous-dossiers "
              "(demography, education, health, infrastructure, climate, socio_economic).")
        return

    df_rapport.to_csv("diagnostic_rapport.csv", index=False, encoding="utf-8-sig")

    print(f"\n{'='*70}")
    print(f"DIAGNOSTIC : {len(df_rapport)} sources analysees (fichiers + feuilles xlsx)")
    print(f"{'='*70}\n")
    print(df_rapport["statut"].value_counts().to_string())
    print()

    bloquants = df_rapport[df_rapport["statut"] == "BLOQUANT"]
    if len(bloquants) > 0:
        print(f"\n🔴 BLOQUANTS ({len(bloquants)}) -- a corriger avant de continuer :")
        for _, r in bloquants.iterrows():
            print(f"  [{r['theme']}/{r['fichier']}] {r['problemes']}")

    erreurs = df_rapport[df_rapport["statut"] == "ERREUR_LECTURE"]
    if len(erreurs) > 0:
        print(f"\n⛔ ERREURS DE LECTURE ({len(erreurs)}) :")
        for _, r in erreurs.iterrows():
            print(f"  [{r['theme']}/{r['fichier']}] {r['problemes']}")

    a_verifier = df_rapport[df_rapport["statut"] == "A_VERIFIER"]
    if len(a_verifier) > 0:
        print(f"\n🟡 A VERIFIER ({len(a_verifier)}) -- pas bloquant, mais a relire :")
        for _, r in a_verifier.iterrows():
            print(f"  [{r['theme']}/{r['fichier']}] {r['avertissements']}")

    ok = df_rapport[df_rapport["statut"] == "OK"]
    print(f"\n🟢 PRETS ({len(ok)}) : {', '.join(ok['fichier'].tolist())}")

    print(f"\nRapport complet sauvegarde : diagnostic_rapport.csv")


if __name__ == "__main__":
    dossier = sys.argv[1] if len(sys.argv) > 1 else "."
    main(dossier)
