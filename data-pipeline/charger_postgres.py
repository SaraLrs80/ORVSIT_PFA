"""
ETAPE 3 -- CHARGEMENT PostgreSQL de l'architecture catalogue.

Prerequis : avoir deja lance construire_catalogue.py (etape 2), qui produit :
    - dim_indicateur.csv
    - faits/<theme>/<table>.csv   (une table par source, deja avec territoire_id)
    - dim_territoire.csv          (deja existant, construit avant)

Principe : AUCUNE fusion. Chaque CSV de faits/ devient sa PROPRE table
PostgreSQL, dans le schema correspondant a son theme. dim_indicateur et
dim_territoire vont dans le schema 'referential'.

⚠️  DESTRUCTIF : ce script fait DROP SCHEMA ... CASCADE puis recree, pour
    chaque theme (demography, education, health, infrastructure, climate,
    socio_economic, referential) -- comme ton ancien build_dwh.py. Toute
    table existante dans ces schemas sera perdue. Si tu as des tables a
    garder dans 'dwh_orvsit' issues de l'ancien pipeline, fais une sauvegarde
    ou charge dans une base separee (voir DB_NAME plus bas) avant de lancer.

Necessite un fichier .env a la racine avec :
    DB_HOST=localhost
    DB_PORT=5432
    DB_USER=postgres
    DB_PASSWORD=...
    DB_NAME=dwh_orvsit

Lancer :
    python charger_postgres.py
    (les fichiers CSV sont lus depuis le dossier courant : dim_indicateur.csv,
     dim_territoire.csv, et faits/<theme>/*.csv)
"""
import pandas as pd
import os
import sys
import urllib.parse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

THEMES_VALIDES = ["demography", "education", "health", "infrastructure", "climate", "socio_economic"]

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "dwh_orvsit")


def get_engine():
    user = urllib.parse.quote_plus(DB_USER)
    pwd = urllib.parse.quote_plus(DB_PASSWORD)
    return create_engine(f"postgresql://{user}:{pwd}@{DB_HOST}:{DB_PORT}/{DB_NAME}")


def creer_base_si_absente(engine_defaut):
    with engine_defaut.connect() as conn:
        conn.execute(text("COMMIT"))  # sortir d'une eventuelle transaction implicite
        existe = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": DB_NAME}).fetchone()
        if not existe:
            conn.execute(text("COMMIT"))
            conn.execute(text(f'CREATE DATABASE "{DB_NAME}"'))
            print(f"[+] Base '{DB_NAME}' creee.")
        else:
            print(f"[i] Base '{DB_NAME}' deja existante.")


def recreer_schemas(engine):
    with engine.begin() as conn:
        for schema in THEMES_VALIDES + ["referential"]:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    print(f"[✔] Schemas recrees : {', '.join(THEMES_VALIDES + ['referential'])}")


def charger_dimensions(engine):
    dim_territoire = pd.read_csv("dim_territoire.csv", encoding="utf-8-sig")
    dim_territoire.to_sql("dim_territoire", engine, schema="referential", if_exists="replace", index=False)
    print(f"[✔] referential.dim_territoire : {len(dim_territoire)} lignes")

    dim_indicateur = pd.read_csv("dim_indicateur.csv", encoding="utf-8-sig")
    dim_indicateur.to_sql("dim_indicateur", engine, schema="referential", if_exists="replace", index=False)
    print(f"[✔] referential.dim_indicateur : {len(dim_indicateur)} lignes")

    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE referential.dim_territoire ADD PRIMARY KEY (territoire_id)'))
        conn.execute(text('ALTER TABLE referential.dim_indicateur ADD PRIMARY KEY (indicateur_id)'))
    print("[✔] Cles primaires ajoutees sur les 2 dimensions")

    if os.path.exists("dim_etablissement_scolaire.csv"):
        dim_etab = pd.read_csv("dim_etablissement_scolaire.csv", encoding="utf-8-sig")
        dim_etab.to_sql("dim_etablissement_scolaire", engine, schema="referential", if_exists="replace", index=False)
        with engine.begin() as conn:
            conn.execute(text('ALTER TABLE referential.dim_etablissement_scolaire ADD PRIMARY KEY (etablissement_id)'))
            conn.execute(text(
                'ALTER TABLE referential.dim_etablissement_scolaire '
                'ADD CONSTRAINT fk_etablissement_territoire '
                'FOREIGN KEY (territoire_id_commune) REFERENCES referential.dim_territoire(territoire_id)'
            ))
        print(f"[✔] referential.dim_etablissement_scolaire : {len(dim_etab)} lignes (avec cle etrangere territoire)")


def nom_table_pg(theme, table_pg):
    """Retire le prefixe theme_ deja present dans table_pg (redondant une fois dans le schema)."""
    prefixe = f"{theme}_"
    if table_pg.startswith(prefixe):
        return table_pg[len(prefixe):]
    return table_pg


def charger_faits(engine, dossier_faits="faits"):
    total_tables = 0
    total_lignes = 0
    erreurs = []

    for theme in THEMES_VALIDES:
        chemin_theme = os.path.join(dossier_faits, theme)
        if not os.path.isdir(chemin_theme):
            continue
        for fichier in sorted(os.listdir(chemin_theme)):
            if not fichier.endswith(".csv"):
                continue
            table_pg = fichier[:-4]  # retire .csv
            table_finale = nom_table_pg(theme, table_pg)
            chemin = os.path.join(chemin_theme, fichier)
            try:
                df = pd.read_csv(chemin, encoding="utf-8-sig")
                if "territoire_id" in df.columns:
                    df["territoire_id"] = pd.to_numeric(df["territoire_id"], errors="coerce").astype("Int64")
                df.to_sql(table_finale, engine, schema=theme, if_exists="replace", index=False)

                if "territoire_id" in df.columns:
                    with engine.begin() as conn:
                        conn.execute(text(
                            f'CREATE INDEX IF NOT EXISTS idx_{theme}_{table_finale}_territoire '
                            f'ON "{theme}"."{table_finale}" (territoire_id)'
                        ))

                total_tables += 1
                total_lignes += len(df)
                print(f"  [✔] {theme}.{table_finale} : {len(df)} lignes")
            except Exception as e:
                erreurs.append((theme, table_finale, str(e)))
                print(f"  [✘] {theme}.{table_finale} : ERREUR -- {e}")

    return total_tables, total_lignes, erreurs


def ajouter_cles_etrangeres(engine, dossier_faits="faits"):
    """Optionnel : relie chaque territoire_id a referential.dim_territoire.
    Non bloquant si ca echoue sur une table (juste un avertissement)."""
    echecs = []
    for theme in THEMES_VALIDES:
        chemin_theme = os.path.join(dossier_faits, theme)
        if not os.path.isdir(chemin_theme):
            continue
        for fichier in sorted(os.listdir(chemin_theme)):
            if not fichier.endswith(".csv"):
                continue
            table_finale = nom_table_pg(theme, fichier[:-4])
            try:
                with engine.begin() as conn:
                    conn.execute(text(
                        f'ALTER TABLE "{theme}"."{table_finale}" '
                        f'ADD CONSTRAINT fk_{theme}_{table_finale}_territoire '
                        f'FOREIGN KEY (territoire_id) REFERENCES referential.dim_territoire(territoire_id)'
                    ))
            except Exception as e:
                echecs.append((theme, table_finale, str(e)))
    if echecs:
        print(f"\n[i] {len(echecs)} contrainte(s) de cle etrangere non ajoutee(s) (non bloquant) :")
        for theme, table, err in echecs[:10]:
            print(f"    {theme}.{table} : {err.splitlines()[0]}")
    else:
        print("\n[✔] Toutes les cles etrangeres territoire_id -> dim_territoire ajoutees")


def main():
    print("=" * 70)
    print(f"CHARGEMENT POSTGRESQL -- base cible : {DB_NAME}")
    print("=" * 70)

    for fichier_requis in ["dim_territoire.csv", "dim_indicateur.csv"]:
        if not os.path.exists(fichier_requis):
            print(f"ERREUR : '{fichier_requis}' introuvable dans le dossier courant.")
            return
    if not os.path.isdir("faits"):
        print("ERREUR : dossier 'faits/' introuvable. Lance construire_catalogue.py d'abord.")
        return

    engine_defaut = create_engine(
        f"postgresql://{urllib.parse.quote_plus(DB_USER)}:{urllib.parse.quote_plus(DB_PASSWORD)}"
        f"@{DB_HOST}:{DB_PORT}/postgres"
    )
    creer_base_si_absente(engine_defaut)
    engine_defaut.dispose()

    engine = get_engine()

    reponse = input(f"\n⚠️  Ceci va SUPPRIMER puis recreer les schemas {THEMES_VALIDES + ['referential']} "
                     f"dans '{DB_NAME}'. Continuer ? (o/n) : ")
    if reponse.strip().lower() != "o":
        print("Annule.")
        return

    recreer_schemas(engine)
    charger_dimensions(engine)

    print("\n--- Chargement des tables de faits ---")
    n_tables, n_lignes, erreurs = charger_faits(engine)

    ajouter_cles_etrangeres(engine)

    print(f"\n{'='*70}")
    print(f"TERMINE : {n_tables} tables chargees, {n_lignes} lignes au total")
    if erreurs:
        print(f"\n🔴 {len(erreurs)} erreur(s) de chargement :")
        for theme, table, err in erreurs:
            print(f"   {theme}.{table} : {err}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
