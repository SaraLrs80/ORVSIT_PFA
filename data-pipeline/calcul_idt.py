"""
calcul_idt.py — Indice de Développement Territorial (IDT) au niveau
préfecture/province (8 territoires), en 6 dimensions.

Principe (voir rapport, partie « calcul des indicateurs ») :
  1. On sélectionne des indicateurs FIABLES, disponibles pour les 8 provinces,
     et exprimés en TAUX / RATIOS pour être comparables.
  2. On les range en 6 DIMENSIONS :
        Éducation · Conditions de vie · Santé · Emploi · Numérique · Accessibilité
  3. On NORMALISE chaque indicateur sur 0-100 (min-max entre les 8 territoires),
     en inversant les indicateurs « négatifs » (100 = toujours le mieux).
  4. score d'une dimension = moyenne de ses indicateurs normalisés.
  5. IDT = moyenne des 6 dimensions (POIDS ÉGAUX, aligné sur l'IPM du HCP).
     On calcule aussi une variante PONDÉRÉE (éducation/santé renforcées) pour
     l'analyse de sensibilité : on vérifie que le classement reste robuste.
  6. On écrit le résultat dans referential.idt_territoire (lu ensuite par l'API).

Lancement :  python calcul_idt.py   (depuis data-pipeline, avec le .env renseigné)
"""

import os
import glob
import urllib.parse

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# --- Connexion à l'entrepôt ---
load_dotenv()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "dwh_orvsit")


def get_engine():
    user = urllib.parse.quote_plus(DB_USER)
    pwd = urllib.parse.quote_plus(DB_PASSWORD)
    return create_engine(f"postgresql://{user}:{pwd}@{DB_HOST}:{DB_PORT}/{DB_NAME}")


# --- Indicateurs traités par valeurs_province() (taux %, un par province) ---
# (id, libellé, sens, dimension).  sens = +1 « haut = mieux », -1 « haut = pire »
INDICATEURS = [
    # Éducation
    (115, "Scolarisation 6-11",    +1, "Éducation"),
    (113, "Analphabétisme 10+",    -1, "Éducation"),
    (106, "Aucun niveau d'études", -1, "Éducation"),
    (111, "Niveau supérieur",      +1, "Éducation"),
    # Conditions de vie (RGPH 2024, Ménages, milieu Ensemble — corrige un bug où
    # la table précédente contenait en réalité des données milieu URBAIN
    # étiquetées à tort comme valeur globale, voir dim_indicateur ids 450-485)
    (472, "Accès eau",             +1, "Conditions de vie"),
    (471, "Accès électricité",     +1, "Conditions de vie"),
    (473, "Assainissement",        +1, "Conditions de vie"),
    (457, "Habitat précaire",      -1, "Conditions de vie"),
    # Emploi
    (393, "Taux de chômage",       -1, "Emploi"),
    (392, "Taux d'activité",       +1, "Emploi"),
    # Numérique
    (367, "Utilisation internet",  +1, "Numérique"),
    (368, "Ordinateur personnel",  +1, "Numérique"),
]

# Poids de la variante pondérée (éducation + santé renforcées) — somme = 1.
POIDS = {
    "Éducation": 0.25, "Santé": 0.25,
    "Conditions de vie": 0.125, "Emploi": 0.125,
    "Numérique": 0.125, "Accessibilité": 0.125,
}

DIM_TERR = pd.read_csv("dim_territoire.csv", encoding="utf-8-sig")
DIM_IND = pd.read_csv("dim_indicateur.csv", encoding="utf-8-sig")
NIVEAU = dict(zip(DIM_TERR.territoire_id, DIM_TERR.niveau))
NOM = dict(zip(DIM_TERR.territoire_id, DIM_TERR.nom))


def slug(dim):
    """Nom de dimension -> suffixe de colonne (score_education, etc.)."""
    return {"Éducation": "education", "Conditions de vie": "conditions_vie",
            "Santé": "sante", "Emploi": "emploi", "Numérique": "numerique",
            "Accessibilité": "accessibilite"}[dim]


def csv_du_fait(table_pg):
    for f in glob.glob("faits/*/*.csv"):
        if os.path.splitext(os.path.basename(f))[0] == str(table_pg):
            return f
    return None


def valeurs_province(indicateur_id):
    """{territoire_id: valeur} d'un indicateur, pour les 8 préfectures/provinces."""
    r = DIM_IND[DIM_IND.indicateur_id == indicateur_id].iloc[0]
    df = pd.read_csv(csv_du_fait(r["table_pg"]), encoding="utf-8-sig")
    tcol = "territoire_id"
    icol = next((c for c in df.columns if c.strip().lower() in ("indicateur", "filtre_indicateur")), None)
    vcol = next((c for c in df.columns if c.strip().lower() in ("valeur", "value")), None)

    # 1) ne garder que les lignes de CET indicateur
    sub = df[df[icol].astype(str) == str(r["filtre_indicateur"])] if icol and pd.notna(r["filtre_indicateur"]) else df
    # 2) s'il y a une ventilation sexe/milieu, prendre « ensemble »
    for scol in [c for c in sub.columns if c.strip().lower() in ("sexe", "sex", "milieu")]:
        m = sub[scol].astype(str).str.contains("ensemble|deux|total", case=False, na=False)
        if m.any():
            sub = sub[m]
    # 3) niveau préfecture/province uniquement
    sub = sub[sub[tcol].map(lambda x: NIVEAU.get(int(x)) if str(x).replace(".", "", 1).isdigit() else None) == "prefecture_province"]
    # 4) en nombre, moyenne par territoire (au cas où)
    sub = sub.copy()
    sub["v"] = pd.to_numeric(sub[vcol], errors="coerce")
    return sub.groupby(tcol)["v"].mean()


def normaliser(colonne, sens):
    """0-100 (min-max), inversé si sens=-1 (pour que 100 = toujours le mieux)."""
    lo, hi = colonne.min(), colonne.max()
    if hi == lo:
        return pd.Series(100.0, index=colonne.index)
    note = (colonne - lo) / (hi - lo) * 100
    return note if sens > 0 else 100 - note


def rates_sante():
    """
    Densité médicale et hospitalière (public + privé), ratios OFFICIELS
    (Carte Sanitaire, Ministère de la Santé — TBI 2024, voir
    sante_offre_province_2024_SOURCE.md). AUCUN calcul de notre part.

    Remplace l'ancienne rates_sante() (secteur public seul), qui créait un
    biais « per-capita » favorisant les petites provinces rurales à
    nombreux petits dispensaires, et masquait la concentration réelle de
    l'offre spécialisée (CHU, cliniques privées) à Tanger-Assilah.

    On ne retient QUE 2 indicateurs pour le score composite : médecins et
    lits hospitaliers (public + privé), les deux mesures OMS-standard de
    « densité de l'offre de soins ». Le ratio ESSP/habitant est volontairement
    exclu du score (il mesure la proximité des soins primaires, structurellement
    favorable aux petites provinces rurales à réseau de dispensaires dense —
    un phénomène réel, pas un biais, mais qui ne doit pas être moyenné avec la
    densité médicale/hospitalière sous peine de recréer le même artefact).
    Il reste affiché dans la fiche territoriale à titre informatif
    (cf. rates_sante_extra), sans peser sur le score.
    """
    df = pd.read_csv("sante_offre_province_2024.csv", encoding="utf-8-sig").set_index("territoire_id")
    r = pd.DataFrame(index=df.index)
    r["Hab. / médecin (pub+privé)"] = df["hab_par_medecin_public_prive"]
    r["Hab. / lit hosp. (pub+privé)"] = df["hab_par_lit_public_prive"]
    return r


def rates_sante_extra():
    """
    Indicateurs santé complémentaires (mêmes ratios officiels), affichés
    dans la fiche territoriale à titre informatif MAIS non inclus dans le
    score composite score_sante (voir justification dans rates_sante()).
    """
    df = pd.read_csv("sante_offre_province_2024.csv", encoding="utf-8-sig").set_index("territoire_id")
    r = pd.DataFrame(index=df.index)
    r["Hab. / ESSP"]                 = df["hab_par_essp_total"]
    r["Hab. / infirmier (public)"]   = df["hab_par_infirmier_public"]
    r["Hab. / dentiste (pub+privé)"] = df["hab_par_dentiste_public_prive"]
    r["Hab. / officine pharmacie"]   = df["hab_par_officine_total"]
    return r


def rates_acces():
    """
    Accessibilité au niveau province : distance moyenne (sur les douars ruraux)
    au centre de santé et à la route goudronnée. Indicateurs « négatifs »
    (plus la distance est grande, plus le territoire est enclavé).
    """
    df = pd.read_csv("faits/demography/demography_demography_population_population_rural.csv",
                     encoding="utf-8-sig")
    df["valeur"] = pd.to_numeric(df["valeur"], errors="coerce")
    dists = ["distance_centre_sante_km", "distance_route_goudronnee_km"]
    sub = df[df["indicateur"].isin(dists)].copy()
    # rattacher chaque province_prefecture à son territoire_id (mot-clé français)
    KW = {"tanger": 2, "fnideq": 3, "tétouan": 4, "tetouan": 4, "fahs": 5,
          "larache": 6, "hoceima": 7, "chefchaouen": 8, "ouazzane": 9}
    def prov_id(s):
        s = str(s).lower()
        return next((v for k, v in KW.items() if k in s), None)
    sub["tid"] = sub["province_prefecture"].map(prov_id)
    piv = sub.pivot_table(index=["tid", "douar"], columns="indicateur",
                          values="valeur", aggfunc="first").reset_index()
    agg = piv.groupby("tid")[dists].mean()
    r = pd.DataFrame(index=agg.index.astype(int))
    r["Dist. santé (km)"] = agg["distance_centre_sante_km"].values
    r["Dist. route (km)"] = agg["distance_route_goudronnee_km"].values
    return r


def main():
    # 1) Valeurs brutes des indicateurs « valeurs_province » -> territoires × indicateurs
    brut = {lib: valeurs_province(iid) for (iid, lib, sens, dim) in INDICATEURS}
    M = pd.DataFrame(brut)

    # 2) Normalisation 0-100 de chacun
    N = pd.DataFrame({lib: normaliser(M[lib], sens) for (iid, lib, sens, dim) in INDICATEURS})

    # 3) Score des dimensions « valeurs_province » = moyenne de leurs indicateurs
    for dim in ["Éducation", "Conditions de vie", "Emploi", "Numérique"]:
        libs = [lib for (iid, lib, s, d) in INDICATEURS if d == dim]
        N["score_" + slug(dim)] = N[libs].mean(axis=1)

    # 3 bis) Santé : médecins + lits (public+privé), ratios "hab. par unité"
    # -> sens NÉGATIF (plus la valeur est grande, moins l'accès est bon).
    S = rates_sante()
    for col in S.columns:
        N[col] = normaliser(S[col], -1)
    # Cas Fahs-Anjra : aucun hôpital recensé -> valeur manquante, mais ce n'est
    # PAS une donnée à ignorer : capacité hospitalière nulle = pire situation
    # possible -> score forcé à 0 (et non moyenné en excluant l'indicateur,
    # ce qui gonflerait artificiellement son score sur le seul indicateur médecin).
    col_lits = "Hab. / lit hosp. (pub+privé)"
    N.loc[S[col_lits].isna(), col_lits] = 0.0
    N["score_sante"] = N[list(S.columns)].mean(axis=1)

    # Indicateurs santé complémentaires : informatifs uniquement (fiche
    # territoriale), volontairement EXCLUS du score_sante (voir rates_sante_extra).
    S_extra = rates_sante_extra()

    # 3 ter) Accessibilité : 2 distances, normalisées en « négatif » (loin = pire)
    A = rates_acces()
    for col in A.columns:
        N[col] = normaliser(A[col], -1)
    N["score_accessibilite"] = N[list(A.columns)].mean(axis=1)

    # 4) IDT = moyenne des 6 dimensions (POIDS ÉGAUX)
    dims = ["score_education", "score_conditions_vie", "score_sante",
            "score_emploi", "score_numerique", "score_accessibilite"]
    N["idt"] = N[dims].mean(axis=1)

    # 4 bis) Variante PONDÉRÉE (sensibilité : éducation/santé renforcées)
    N["idt_pondere"] = sum(N["score_" + slug(d)] * w for d, w in POIDS.items())

    # 5) Tableau final
    resultat = pd.DataFrame({
        "territoire_id": N.index.astype(int),
        "nom": [NOM.get(int(i)) for i in N.index],
        "score_education": N["score_education"].round(1),
        "score_conditions_vie": N["score_conditions_vie"].round(1),
        "score_sante": N["score_sante"].round(1),
        "score_emploi": N["score_emploi"].round(1),
        "score_numerique": N["score_numerique"].round(1),
        "score_accessibilite": N["score_accessibilite"].round(1),
        "idt": N["idt"].round(1),
        "idt_pondere": N["idt_pondere"].round(1),
    }).sort_values("idt", ascending=False)
    print(resultat.to_string(index=False))

    # 6) Écriture dans referential.idt_territoire
    engine = get_engine()
    resultat.to_sql("idt_territoire", engine, schema="referential",
                    if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE referential.idt_territoire ADD PRIMARY KEY (territoire_id)"))
    print("\n[✔] referential.idt_territoire écrite (", len(resultat), "territoires ).")

    # 7) Principales disparités (plus gros écarts entre territoires)
    noms = {i: NOM.get(int(i)) for i in N.index}

    def dispar(serie, libelle, unite):
        s = serie.dropna()
        hi, lo = s.idxmax(), s.idxmin()
        return {"indicateur": libelle, "unite": unite,
                "max_nom": noms[hi], "max_val": round(float(s[hi]), 1),
                "min_nom": noms[lo], "min_val": round(float(s[lo]), 1),
                "ecart": round(float(s[hi] - s[lo]), 1)}

    disparites = pd.DataFrame([
        dispar(M["Accès eau"], "Accès à l'eau", "%"),
        dispar(M["Taux de chômage"], "Chômage", "%"),
        dispar(M["Utilisation internet"], "Accès internet", "%"),
        dispar(S["Hab. / médecin (pub+privé)"], "Habitants par médecin (pub+privé)", ""),
        dispar(A["Dist. santé (km)"], "Éloignement centre de santé", "km"),
    ]).sort_values("ecart", ascending=False)
    disparites.to_sql("disparites", engine, schema="referential", if_exists="replace", index=False)
    print("[✔] referential.disparites écrite (", len(disparites), "indicateurs ).")

    # 8) Valeurs BRUTES par territoire et dimension — pour afficher la vraie
    #    valeur à côté du score (le score min-max n'est qu'une position 0-100).
    UNITES = {
        "Scolarisation 6-11": "%", "Analphabétisme 10+": "%", "Aucun niveau d'études": "%",
        "Niveau supérieur": "%", "Accès eau": "%", "Accès électricité": "%",
        "Assainissement": "%", "Habitat précaire": "%", "Taux de chômage": "%",
        "Taux d'activité": "%", "Utilisation internet": "%", "Ordinateur personnel": "%",
        "Hab. / médecin (pub+privé)": "hab./médecin", "Hab. / lit hosp. (pub+privé)": "hab./lit",
        "Hab. / ESSP": "hab./ESSP", "Hab. / infirmier (public)": "hab./infirmier",
        "Hab. / dentiste (pub+privé)": "hab./dentiste", "Hab. / officine pharmacie": "hab./officine",
        "Dist. santé (km)": "km", "Dist. route (km)": "km",
    }
    DIM_OF = {lib: dim for (iid, lib, s, dim) in INDICATEURS}
    for c in S.columns:
        DIM_OF[c] = "Santé"
    for c in S_extra.columns:
        DIM_OF[c] = "Santé"
    for c in A.columns:
        DIM_OF[c] = "Accessibilité"

    RAW = pd.concat([M, S, S_extra, A], axis=1)   # territoires × tous les indicateurs bruts
    det = []
    for tid in RAW.index:
        for col in RAW.columns:
            v = RAW.loc[tid, col]
            if pd.notna(v):
                det.append({"territoire_id": int(tid), "dimension": DIM_OF.get(col, ""),
                            "indicateur": col, "valeur": round(float(v), 1),
                            "unite": UNITES.get(col, "")})
    details = pd.DataFrame(det)
    details.to_sql("idt_details", engine, schema="referential", if_exists="replace", index=False)
    print("[✔] referential.idt_details écrite (", len(details), "lignes de valeurs brutes ).")


if __name__ == "__main__":
    main()
