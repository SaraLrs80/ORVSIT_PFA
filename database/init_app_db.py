"""
Initialise la base applicative « orvsit_app » (utilisateurs, demandes d'accès,
assistant IA, journal d'usage). SÉPARÉE du data warehouse « dwh_orvsit ».

Étapes :
    1. crée la base orvsit_app si elle n'existe pas ;
    2. exécute orvsit_app_schema.sql (tables, index, trigger, données de départ).

Prérequis : un fichier .env à la racine du projet avec
    DB_HOST=localhost
    DB_PORT=5432
    DB_USER=postgres
    DB_PASSWORD=...
    APP_DB_NAME=orvsit_app      # (optionnel, défaut : orvsit_app)

Lancer :
    python database/init_app_db.py
"""
import os
import urllib.parse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
APP_DB_NAME = os.getenv("APP_DB_NAME", "orvsit_app")

SCHEMA_SQL = os.path.join(os.path.dirname(__file__), "orvsit_app_schema.sql")


def _url(dbname):
    user = urllib.parse.quote_plus(DB_USER)
    pwd = urllib.parse.quote_plus(DB_PASSWORD)
    return f"postgresql://{user}:{pwd}@{DB_HOST}:{DB_PORT}/{dbname}"


def creer_base_si_absente():
    engine = create_engine(_url("postgres"), isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        existe = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": APP_DB_NAME}
        ).fetchone()
        if existe:
            print(f"[i] Base '{APP_DB_NAME}' déjà existante.")
        else:
            conn.execute(text(f'CREATE DATABASE "{APP_DB_NAME}"'))
            print(f"[+] Base '{APP_DB_NAME}' créée.")
    engine.dispose()


def executer_schema():
    with open(SCHEMA_SQL, "r", encoding="utf-8") as f:
        sql = f.read()
    engine = create_engine(_url(APP_DB_NAME))
    with engine.begin() as conn:
        conn.execute(text(sql))
    engine.dispose()
    print(f"[✔] Schéma appliqué depuis {os.path.basename(SCHEMA_SQL)}")


if __name__ == "__main__":
    print("=" * 60)
    print(f"INITIALISATION DE LA BASE APPLICATIVE : {APP_DB_NAME}")
    print("=" * 60)
    creer_base_si_absente()
    executer_schema()
    print("Terminé. Pense à remplacer le mot de passe admin par défaut.")
