"""
De quoi peut-on faire une carte d'identité régionale ?

POURQUOI CE SCRIPT
La Vue d'ensemble actuelle lit `referential.idt_territoire`, la table de
l'indicateur composite abandonné. La refaire suppose de savoir d'abord ce que
l'entrepôt sait dire de la RÉGION elle-même — territoire_id = 1 — et non des
huit provinces. Rien ne garantit que les tables de faits portent une ligne
régionale : certaines sources publient la région, d'autres s'arrêtent aux
provinces.

Concevoir avant de mesurer, ce serait dessiner une page sur des données
supposées. Ce script ne modifie rien : il compte.

    python diagnostic_vue_ensemble.py
"""

import collections
import csv
import os
import re
import urllib.parse

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

CATALOGUE = "dim_indicateur.csv"
REGION = 1
SECTEURS = ("Démographie", "Emploi", "Éducation", "Santé", "Conditions de vie")


def moteur():
    user = urllib.parse.quote_plus(os.getenv("DB_USER", "postgres"))
    mdp = urllib.parse.quote_plus(os.getenv("DB_PASSWORD", ""))
    hote = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    base = os.getenv("DB_NAME", "dwh_orvsit")
    return create_engine(f"postgresql://{user}:{mdp}@{hote}:{port}/{base}")


def identifiant(nom):
    """Un nom de table ou de schéma, refusé s'il n'est pas un simple mot."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nom or ""):
        raise ValueError(f"nom de table inattendu : {nom!r}")
    return nom


def publies(lignes):
    return [l for l in lignes
            if l["statut"] in ("actif", "validé")
            and "True" in (l["dispo_province"], l["dispo_commune"])]


def principal():
    with open(CATALOGUE, encoding="utf-8-sig") as f:
        catalogue = publies(list(csv.DictReader(f)))

    e = moteur()
    avec_region = []
    sans_region = []
    tables_absentes = set()

    with e.connect() as conn:
        for c in catalogue:
            schema, table = c["theme"], c["table_pg"]
            court = table[len(schema) + 1:] if table.startswith(schema + "_") else table
            try:
                n = conn.execute(text(
                    f"SELECT count(*) FROM {identifiant(schema)}.{identifiant(court)} "
                    f"WHERE indicateur_id = :i AND territoire_id = :t "
                    f"AND valeur IS NOT NULL"),
                    {"i": int(c["indicateur_id"]), "t": REGION}).scalar()
            except Exception:
                tables_absentes.add(f"{schema}.{court}")
                n = 0
            (avec_region if n else sans_region).append(c)

    print(f"Catalogue publié : {len(catalogue)} indicateurs\n")
    print(f"  valeur présente pour la RÉGION (territoire_id=1) : {len(avec_region)}")
    print(f"  absente                                          : {len(sans_region)}")
    if tables_absentes:
        print(f"  tables illisibles                                : "
              f"{sorted(tables_absentes)}")

    print("\n--- par secteur ---")
    par_secteur = collections.Counter(c["secteur"] for c in catalogue)
    ok_secteur = collections.Counter(c["secteur"] for c in avec_region)
    for s in sorted(par_secteur, key=lambda s: -par_secteur[s]):
        print(f"   {s:<24} {ok_secteur[s]:>3}/{par_secteur[s]:<3}")

    print("\n--- ce que la région sait dire, par secteur (30 premiers) ---")
    for s in SECTEURS:
        dedans = [c for c in avec_region if c["secteur"] == s]
        if not dedans:
            continue
        print(f"\n  {s} ({len(dedans)})")
        for c in dedans[:30]:
            print(f"     {c['indicateur_id']:>4}  {c['libelle_court'][:58]:<58} "
                  f"{(c['unite'] or ''):<14} {c['annee']}")

    print("\n--- millésimes présents au niveau régional ---")
    print("   ", dict(collections.Counter(c["annee"] for c in avec_region)))

    print("\n--- sources présentes au niveau régional ---")
    for src, n in collections.Counter(
            (c["source"] or "?")[:60] for c in avec_region).most_common():
        print(f"   {n:>4}  {src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
