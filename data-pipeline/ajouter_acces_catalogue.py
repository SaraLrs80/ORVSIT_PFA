"""
Ajoute au catalogue (dim_indicateur.csv) les indicateurs d'ACCÈS COMMUNAL
produits par generer_acces_communal.py (table demo_acces_communal).
Ce sont des indicateurs de NIVEAU COMMUNE (rural) : ils servent au futur
indicateur communal, PAS à l'IDT province.

Idempotent : n'ajoute rien si 'demo_acces_communal' est déjà dans le catalogue.
Lancer :  python ajouter_acces_catalogue.py   (puis relancer charger_postgres.py)
"""

import pandas as pd

ind = pd.read_csv("dim_indicateur.csv", encoding="utf-8-sig")

if (ind["table_pg"] == "demo_acces_communal").any():
    print("[i] Accès communal déjà présent dans le catalogue. Rien à faire.")
    raise SystemExit(0)

acces = [
    ("acces_sante_km", "Accès aux soins — distance moyenne au centre de santé (commune rurale)", "km", -1),
    ("acces_route_goudronnee_km", "Enclavement routier — distance moyenne à la route goudronnée (commune rurale)", "km", -1),
    ("acces_ecole_primaire_km", "Accès à l'école primaire — distance moyenne (commune rurale)", "km", -1),
    ("acces_college_km", "Accès au collège — distance moyenne (commune rurale)", "km", -1),
    ("pct_douars_sante_plus5km", "Part des douars à plus de 5 km d'un centre de santé", "%", -1),
]

nid = int(ind["indicateur_id"].max()) + 1
rows = []
for i, (cle, libelle, unite, sens) in enumerate(acces):
    rows.append({
        "indicateur_id": nid + i,
        "nom_indicateur": libelle,
        "nom_origine": libelle,
        "theme": "demography",
        "definition": f"{libelle}. Dérivé des distances au niveau douar (RGPH), agrégées par commune.",
        "unite": unite,
        "source": "HCP — RGPH (distances douar agrégées par commune)",
        "annee": 2024,
        "statut": "validé",
        "table_pg": "demo_acces_communal",
        "mode_stockage": "long",
        "colonne_valeur": "valeur",
        "filtre_indicateur": cle,
        "colonne_territoire": "territoire_id",
    })

ind = pd.concat([ind, pd.DataFrame(rows)[ind.columns]], ignore_index=True)
ind.to_csv("dim_indicateur.csv", index=False, encoding="utf-8-sig")
print(f"[✔] {len(rows)} indicateurs d'accès communal ajoutés  ->  {len(ind)} indicateurs au total")
