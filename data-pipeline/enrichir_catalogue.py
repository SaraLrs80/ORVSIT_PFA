"""
Étape 4 bis — Enrichissement du catalogue pour l'assistant IA.

Objectif : rendre dim_indicateur NON AMBIGU, pour qu'un assistant IA (même
gratuit/léger) choisisse toujours le bon indicateur. Trois actions :

  1. NOMS UNIQUES ET CLAIRS
     Le sens réel de chaque indicateur est déjà encodé dans (table_pg,
     filtre_indicateur) : le nom n'était qu'une étiquette tronquée (« Urbain »,
     « Total », « Autre »...). On reconstruit un libellé lisible à partir du
     TITRE de la table source (donnée existante — rien d'inventé), en y ajoutant
     le qualificatif (milieu / catégorie). On garantit l'unicité.
     L'ancien nom est conservé dans `nom_origine` (traçabilité).

  2. MÉTADONNÉES que l'assistant lit pour trancher
     Colonnes ajoutées : definition, source, annee, statut.
     - unite : complétée par déduction sûre (%, hab, /10 000 hab, °C...).
     - source / annee : renseignées UNIQUEMENT pour les indicateurs dont on
       connaît la provenance avec certitude (population milieu = RGPH 2024 HCP ;
       capacités santé = Santé en chiffres 2024). Sinon laissées vides, à
       compléter par toi (on n'invente pas de source).

  3. STATUT de validité
     statut = 'validé' pour les indicateurs réellement utilisés (IDT, population
     milieu, capacités santé) ; 'actif' pour les autres.

Ré-exécutable sans risque (repart de nom_origine si présent).

Lancer un APERÇU :   python enrichir_catalogue.py
Appliquer :          python enrichir_catalogue.py --apply
"""

import re
import sys
import os
import pandas as pd

APPLY = "--apply" in sys.argv
FICHIER = "dim_indicateur.csv"

ind = pd.read_csv(FICHIER, encoding="utf-8-sig")

# Repartir des noms d'origine si le script a déjà tourné (idempotence).
if "nom_origine" in ind.columns:
    ind["nom_indicateur"] = ind["nom_origine"]
else:
    ind["nom_origine"] = ind["nom_indicateur"]

# --- Tables/indicateurs qu'on sait provenir d'une source datée précise ---
SOURCES = {
    "demo_population_milieu": ("HCP — RGPH 2024", 2024),
    "health_capacite_province": ("Ministère de la Santé — Santé en chiffres 2024", 2024),
}
# indicateurs utilisés dans les calculs -> statut « validé »
IDS_VALIDES = {115, 113, 106, 111, 358, 359, 357, 353, 40}  # IDT (éducation + conditions de vie) + population légale


def humaniser_table(theme, table_pg):
    """Transforme un nom de table technique en libellé lisible (titre source)."""
    s = str(table_pg)
    # retirer le préfixe du thème (éventuellement répété : demography_demography_)
    while s.startswith(theme + "_"):
        s = s[len(theme) + 1:]
    s = re.sub(r"^cleaned_", "", s)
    s = re.sub(r"^sante_\d+_", "", s)          # « sante_16_ » -> ''
    s = re.sub(r"^\d+_", "", s)
    s = s.replace("_", " ").strip()
    # supprimer les mots consécutifs répétés (population population -> population)
    mots, dedup = s.split(), []
    for w in mots:
        if not dedup or dedup[-1].lower() != w.lower():
            dedup.append(w)
    s = " ".join(dedup)
    s = re.sub(r"\bpar (region|province|prefecture|milieu)\b.*$", "", s).strip()
    if len(s) > 80:
        s = s[:80].rsplit(" ", 1)[0]
    return s[:1].upper() + s[1:] if s else str(table_pg)


def humaniser_filtre(f):
    f = str(f).strip()
    remap = {"nan": "", "Ensemble": "ensemble", "Total": "total", "Autre": "autre",
             "total_general": "total", "Urbain": "milieu urbain", "Rural": "milieu rural"}
    return remap.get(f, f)


def deduire_unite(nom, filtre, unite):
    if isinstance(unite, str) and unite.strip():
        return unite.strip()
    t = f"{nom} {filtre}".lower()
    if "pour_10000" in t or "/10 000" in t:
        return "/10 000 hab"
    if "pour_100000" in t or "/100 000" in t:
        return "/100 000 hab"
    if "(%)" in t or re.search(r"\btaux\b", t) or "pct" in t or "indice_" in t or "urbanisation" in t:
        return "%"
    if "humidite" in t:
        return "%"
    if "temp_" in t or "temperature" in t:
        return "°C"
    if str(filtre).startswith("nb_") or "nombre" in t or "effectif" in t:
        return "nombre"
    if "population" in t:
        return "hab"
    if any(k in t for k in ["menages", "entrees", "sorties"]):
        return "nombre"
    return ""


# Un nom est « déjà bon » s'il est assez long et non générique.
GENERIQUES = {"urbain", "rural", "ensemble", "total", "autre", "autres", "condom",
              "diu", "pilules", "injections", "entrees", "sorties", "menages",
              "population", "sage femme", "infirmier polyvalent", "total_general",
              "natifs", "temp_max", "temp_min", "humidite"}


def besoin_renommage(nom, est_duplique):
    n = str(nom).strip().lower()
    return est_duplique or len(n) < 12 or n in GENERIQUES


compte_noms = ind["nom_origine"].value_counts()
nouveaux = []
for _, r in ind.iterrows():
    est_dup = compte_noms.get(r["nom_origine"], 0) > 1
    if besoin_renommage(r["nom_origine"], est_dup):
        base = humaniser_table(r["theme"], r["table_pg"])
        qual = humaniser_filtre(r["filtre_indicateur"])
        nom = f"{base} — {qual}" if qual and qual.lower() not in base.lower() else base
    else:
        nom = r["nom_origine"]
    nouveaux.append(nom)
ind["nom_indicateur"] = nouveaux

# Garantir l'unicité absolue : suffixe discret si collision résiduelle.
vus = {}
finaux = []
for _, r in ind.iterrows():
    nom = r["nom_indicateur"]
    if nom in vus:
        vus[nom] += 1
        nom = f"{nom} ({r['theme']}, id{r['indicateur_id']})"
    else:
        vus[nom] = 1
    finaux.append(nom)
ind["nom_indicateur"] = finaux

# Métadonnées.
ind["unite"] = [deduire_unite(n, f, u) for n, f, u in
                zip(ind["nom_indicateur"], ind["filtre_indicateur"], ind.get("unite", ""))]
ind["source"] = [SOURCES.get(t, ("", None))[0] for t in ind["table_pg"]]
ind["annee"] = [SOURCES.get(t, ("", None))[1] for t in ind["table_pg"]]
ind["statut"] = ["validé" if (i in IDS_VALIDES or t in SOURCES) else "actif"
                 for i, t in zip(ind["indicateur_id"], ind["table_pg"])]
ind["definition"] = [f"{n}. Thème : {th}." for n, th in
                     zip(ind["nom_indicateur"], ind["theme"])]

# Ordre de colonnes lisible.
cols = ["indicateur_id", "nom_indicateur", "nom_origine", "theme", "definition",
        "unite", "source", "annee", "statut", "table_pg", "mode_stockage",
        "colonne_valeur", "filtre_indicateur", "colonne_territoire"]
ind = ind[[c for c in cols if c in ind.columns]]

# --- Rapport ---
n_renommes = int((ind["nom_indicateur"] != ind["nom_origine"]).sum())
n_uniques = ind["nom_indicateur"].nunique()
n_unite = int((ind["unite"].astype(str).str.strip() != "").sum())
print(f"Indicateurs        : {len(ind)}")
print(f"Noms uniques       : {n_uniques} / {len(ind)}  {'✔ tous uniques' if n_uniques==len(ind) else '�“ COLLISIONS'}")
print(f"Renommés (clarifiés): {n_renommes}")
print(f"Avec unité          : {n_unite} / {len(ind)}")
print(f"Statut validé       : {int((ind.statut=='validé').sum())}")
print("\n--- Échantillon avant / après (anciens doublons) ---")
apercu = ind[ind.nom_origine.isin(["Urbain","Rural","Total","Autre","population","total_general"])]
for _, r in apercu.head(16).iterrows():
    print(f"  id{r.indicateur_id:<3} '{r.nom_origine}'  ->  '{r.nom_indicateur}'  [{r.unite or '-'}]")

if APPLY:
    if not os.path.exists("dim_indicateur_pre_enrichissement.csv"):
        pd.read_csv(FICHIER, encoding="utf-8-sig").to_csv(
            "dim_indicateur_pre_enrichissement.csv", index=False, encoding="utf-8-sig")
        print("\n[✔] Sauvegarde : dim_indicateur_pre_enrichissement.csv")
    ind.to_csv(FICHIER, index=False, encoding="utf-8-sig")
    print(f"[✔] {FICHIER} enrichi et réécrit ({len(ind)} indicateurs).")
else:
    print("\n[i] APERÇU seulement. Relance avec  --apply  pour écrire dim_indicateur.csv.")
