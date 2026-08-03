"""
Étape 0 bis — Population par milieu (urbain / rural), propre et traçable.

La bonne donnée urbain/rural par province EXISTE DÉJÀ dans l'entrepôt :
    faits/demography/demography_demography_population_population_legale_2025_urba.csv
(source officielle HCP — RGPH 2024, « Population légale selon le milieu de
résidence »). Elle distingue le milieu via la colonne `milieu`
(Ensemble / Urbain / Rural).

Le problème n'était donc PAS la donnée, mais le fait que :
  - le catalogue lisait l'urbain/rural depuis les indicateurs SANTÉ 163/164/165
    (« populations cibles des programmes de santé »), qui sous-estiment la
    population urbaine (≈ 62 % au lieu de 65,48 %) ;
  - l'indicateur démographique 72 « population » ne filtrait pas le milieu.

Ce script produit une table de faits DÉRIVÉE, déjà filtrée et prête à l'emploi :
    faits/demography/demo_population_milieu.csv   (format long)
      territoire_id, indicateur, valeur
      indicateur ∈ { pop_urbain, pop_rural, taux_urbanisation }
pour la région (territoire_id 1) et les 8 préfectures/provinces (2..9).

Contrôle : somme urbaine des 8 provinces = 2 638 815, rurale = 1 391 407,
soit exactement le total régional (65,48 % urbain) — cohérent avec le HCP.

Lancer :  python generer_faits_population.py
"""

import os
import pandas as pd

SRC = "faits/demography/demography_demography_population_population_legale_2025_urba.csv"
OUT = "faits/demography/demo_population_milieu.csv"

df = pd.read_csv(SRC, encoding="utf-8-sig")

# On ne garde que la population (pas les ménages) et les 3 milieux utiles.
df = df[df["indicateur"].astype(str).str.strip() == "population"]
df = df[df["milieu"].astype(str).str.strip().isin(["Ensemble", "Urbain", "Rural"])]

# territoire_id : région (1) + 8 préfectures/provinces (2..9).
df["territoire_id"] = pd.to_numeric(df["territoire_id"], errors="coerce")
df = df[df["territoire_id"].between(1, 9)]
df["valeur"] = pd.to_numeric(df["valeur"], errors="coerce")

# Le fichier source contient des lignes en double (région répétée) : on dédoublonne.
df = df.drop_duplicates(subset=["territoire_id", "milieu"])

# Un tableau territoire × milieu, puis on reconstruit un format long propre.
pivot = df.pivot_table(index="territoire_id", columns="milieu", values="valeur", aggfunc="first")

lignes = []
for tid, row in pivot.iterrows():
    ens = row.get("Ensemble")
    urb = row.get("Urbain")
    rur = row.get("Rural")
    if pd.notna(urb):
        lignes.append((int(tid), "pop_urbain", int(urb)))
    if pd.notna(rur):
        lignes.append((int(tid), "pop_rural", int(rur)))
    if pd.notna(urb) and pd.notna(ens) and ens:
        lignes.append((int(tid), "taux_urbanisation", round(urb / ens * 100, 2)))

faits = pd.DataFrame(lignes, columns=["territoire_id", "indicateur", "valeur"])
os.makedirs("faits/demography", exist_ok=True)
faits.to_csv(OUT, index=False, encoding="utf-8-sig")

# Contrôle de cohérence affiché à l'écran.
prov = faits[(faits.territoire_id.between(2, 9))]
tot_urb = int(prov[prov.indicateur == "pop_urbain"].valeur.sum())
tot_rur = int(prov[prov.indicateur == "pop_rural"].valeur.sum())
print(f"[✔] {OUT} créé ({len(faits)} lignes)")
print(f"    Somme provinces  -> urbain = {tot_urb:,}  rural = {tot_rur:,}".replace(",", " "))
print(f"    Attendu (région) -> urbain = 2 638 815  rural = 1 391 407")
print(faits.to_string(index=False))
