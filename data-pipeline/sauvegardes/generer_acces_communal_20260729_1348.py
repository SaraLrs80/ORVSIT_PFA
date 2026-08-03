"""
Accès communal aux services — dérivé des distances au niveau douar (RGPH, HCP).

Comble (au niveau COMMUNE) les manques réels : accès aux soins et enclavement
routier. On agrège les distances des douars (fichier population_rural, colonne
`commune_rurale`) à leur commune : distance moyenne + médiane au centre de santé,
à la route goudronnée, à l'école, au collège ; plus % de douars « éloignés »
(> 5 km d'un centre de santé) et le nombre de douars.

C'est une mesure d'ACCÈS (distance), pas de capacité (nb de médecins) — et c'est
justement la bonne mesure pour l'enclavement. Concerne les communes RURALES
(les communes urbaines n'ont pas de douars : services sur place, distance ~0).

Sorties :
  - acces_communal_TTA.csv                 (large, lisible : une ligne/commune)
  - faits/demography/demo_acces_communal.csv (long : territoire_id, indicateur, valeur)

Lancer :  python generer_acces_communal.py
"""

import re
import unicodedata
import pandas as pd

SRC = "faits/demography/demography_demography_population_population_rural.csv"
DISTS = {
    "distance_centre_sante_km": "acces_sante_km",
    "distance_route_goudronnee_km": "acces_route_goudronnee_km",
    "distance_ecole_primaire_km": "acces_ecole_primaire_km",
    "distance_college_km": "acces_college_km",
}


def norm(s):
    """Normalise un nom pour l'appariement (sans accents, sans arabe, minuscules)."""
    s = str(s)
    s = "".join(c for c in s if not ("؀" <= c <= "ۿ"))   # retire l'arabe
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")   # retire accents
    s = s.lower()
    s = re.sub(r"^commune (de |d')", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


# --- Données douar ---
df = pd.read_csv(SRC, encoding="utf-8-sig")
df["valeur"] = pd.to_numeric(df["valeur"], errors="coerce")
sub = df[df["indicateur"].isin(DISTS)].copy()

piv = sub.pivot_table(index=["province_prefecture", "commune_rurale", "douar"],
                      columns="indicateur", values="valeur", aggfunc="first").reset_index()

g = piv.groupby(["province_prefecture", "commune_rurale"])
agg = g.agg(
    nb_douars=("douar", "nunique"),
    acces_sante_km=("distance_centre_sante_km", "mean"),
    acces_sante_med=("distance_centre_sante_km", "median"),
    acces_route_goudronnee_km=("distance_route_goudronnee_km", "mean"),
    acces_ecole_primaire_km=("distance_ecole_primaire_km", "mean"),
    acces_college_km=("distance_college_km", "mean"),
).reset_index()
# % de douars à plus de 5 km d'un centre de santé (indicateur d'enclavement sanitaire)
loin = piv.assign(loin=(piv["distance_centre_sante_km"] > 5)).groupby(
    ["province_prefecture", "commune_rurale"])["loin"].mean().mul(100).reset_index(name="pct_douars_sante_plus5km")
agg = agg.merge(loin, on=["province_prefecture", "commune_rurale"])
for c in agg.columns:
    if c not in ("province_prefecture", "commune_rurale", "nb_douars"):
        agg[c] = agg[c].round(1)

# --- Appariement au territoire_id (dim_territoire) ---
terr = pd.read_csv("dim_territoire.csv", encoding="utf-8-sig")
terr_com = terr[terr["niveau"] == "commune"].copy()
terr_com["clef"] = terr_com["nom"].map(norm)
map_nom = dict(zip(terr_com["clef"], terr_com["territoire_id"]))
agg["clef"] = agg["commune_rurale"].map(norm)
agg["territoire_id"] = agg["clef"].map(map_nom)

# Appariements explicites (variantes d'orthographe Bni/Beni, Zarqt/Zarkt…),
# tous vérifiés par le nom ET la province (aucun doute).
ALIAS = {
    "beni gmil": 107,            # -> Commune de Bni Gmil (Al Hoceima)
    "bni abdallah": 117,         # -> Commune de Bni Abdellah (Al Hoceima)
    "zarqt": 124,                # -> Commune de Zarkt (Al Hoceima)
    "sebt azzinate zinat": 41,   # -> Commune de Sebt Azzinate (Tanger-Assilah)
    "bni said bni said": 71,     # -> Commune de Bni Said (Tétouan)
    "bou jedyane": 85,           # -> Commune de Boujedyane (Larache)
    "moqrisset": 176,            # -> Commune de Moqrissat (Ouezzane)
    "ounnana": 170,              # -> Commune d'Ouannana (Ouezzane)
}
manque = agg["territoire_id"].isna()
agg.loc[manque, "territoire_id"] = agg.loc[manque, "clef"].map(ALIAS)

n_match = agg["territoire_id"].notna().sum()
print(f"Communes rurales agrégées : {len(agg)}  |  appariées à un territoire_id : {n_match}")
if n_match < len(agg):
    print("Non appariées (à vérifier) :",
          list(agg[agg["territoire_id"].isna()]["commune_rurale"].head(12)))

agg_out = agg.drop(columns=["clef"]).sort_values("acces_sante_km", ascending=False)
agg_out.to_csv("acces_communal_TTA.csv", index=False, encoding="utf-8-sig")
print("[✔] acces_communal_TTA.csv écrit")

# --- Format long pour le pipeline (seulement les communes appariées) ---
longs = []
ok = agg.dropna(subset=["territoire_id"])
for _, r in ok.iterrows():
    tid = int(r["territoire_id"])
    for col in ["acces_sante_km", "acces_route_goudronnee_km", "acces_ecole_primaire_km",
                "acces_college_km", "pct_douars_sante_plus5km"]:
        if pd.notna(r[col]):
            longs.append((tid, col, r[col]))
faits = pd.DataFrame(longs, columns=["territoire_id", "indicateur", "valeur"])
faits.to_csv("faits/demography/demo_acces_communal.csv", index=False, encoding="utf-8-sig")
print(f"[✔] faits/demography/demo_acces_communal.csv écrit ({len(faits)} lignes, {ok['territoire_id'].nunique()} communes)")
