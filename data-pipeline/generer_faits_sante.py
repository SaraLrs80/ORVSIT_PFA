"""
Étape 1 du nettoyage santé.
Génère le fichier de faits `faits/health/health_capacite_province.csv`
(format long : territoire_id, indicateur, valeur) à partir des comptages
officiels (sante_capacite_province.csv) + la population légale (RGPH),
en y ajoutant les taux per-capita.

Lancer :  python generer_faits_sante.py
"""

import glob
import os
import pandas as pd

terr = pd.read_csv("dim_territoire.csv", encoding="utf-8-sig")
niveau = dict(zip(terr.territoire_id, terr.niveau))
ind = pd.read_csv("dim_indicateur.csv", encoding="utf-8-sig")


def csv_for(table_pg):
    for f in glob.glob("faits/*/*.csv"):
        if os.path.splitext(os.path.basename(f))[0].startswith(str(table_pg)[:40]):
            return f
    return None


def population_legale():
    """Population légale par province (indicateur_id = 40)."""
    r = ind[ind.indicateur_id == 40].iloc[0]
    df = pd.read_csv(csv_for(r["table_pg"]), encoding="utf-8-sig")
    icol = next(c for c in df.columns if c.strip().lower() in ("indicateur", "filtre_indicateur"))
    sub = df[df[icol].astype(str) == str(r["filtre_indicateur"])]
    sub = sub[sub["territoire_id"].map(lambda x: niveau.get(int(x))) == "prefecture_province"]
    return {int(t): float(v) for t, v in zip(sub["territoire_id"], pd.to_numeric(sub["valeur"], errors="coerce"))}


pop = population_legale()
sante = pd.read_csv("sante_capacite_province.csv", encoding="utf-8-sig")

lignes = []
for _, r in sante.iterrows():
    t = int(r["territoire_id"])
    p = pop.get(t)
    # comptages bruts
    lignes.append((t, "nb_essp", r["essp"]))
    lignes.append((t, "nb_hopitaux", r["hopitaux"]))
    lignes.append((t, "nb_medecins_public", r["medecins_public"]))
    lignes.append((t, "nb_paramedical_public", r["paramedical_public"]))
    # taux per-capita
    if p:
        lignes.append((t, "medecins_pour_10000_hab", round(r["medecins_public"] / p * 10000, 2)))
        lignes.append((t, "paramedical_pour_10000_hab", round(r["paramedical_public"] / p * 10000, 2)))
        lignes.append((t, "essp_pour_100000_hab", round(r["essp"] / p * 100000, 2)))

faits = pd.DataFrame(lignes, columns=["territoire_id", "indicateur", "valeur"])
os.makedirs("faits/health", exist_ok=True)
faits.to_csv("faits/health/health_capacite_province.csv", index=False, encoding="utf-8-sig")
print("[✔] faits/health/health_capacite_province.csv créé (", len(faits), "lignes )")
print(faits.head(14).to_string(index=False))
