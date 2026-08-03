"""
Étape 2 du nettoyage santé.
Nettoie et enrichit le catalogue dim_indicateur.csv :
  - SAUVEGARDE d'abord dim_indicateur.csv -> dim_indicateur_backup.csv
  - RETIRE les indicateurs santé défaillants (couverture < 8 provinces OU >= 3 zéros)
  - RETIRE les indicateurs urbain/rural incohérents (163, 164, 165)
  - AJOUTE les nouveaux indicateurs de capacité santé (table health_capacite_province)

À lancer APRÈS generer_faits_sante.py, puis relancer charger_postgres.py.
Lancer :  python nettoyer_catalogue.py
"""

import glob
import os
import pandas as pd

terr = pd.read_csv("dim_territoire.csv", encoding="utf-8-sig")
niveau = dict(zip(terr.territoire_id, terr.niveau))
ind = pd.read_csv("dim_indicateur.csv", encoding="utf-8-sig")

# --- Garde-fou : ne pas relancer si déjà nettoyé ---
if (ind["table_pg"] == "health_capacite_province").any():
    print("[i] Le catalogue semble déjà nettoyé (capacités présentes). Rien à faire.")
    raise SystemExit(0)

# --- Sauvegarde (une seule fois : on n'écrase pas une sauvegarde existante) ---
if not os.path.exists("dim_indicateur_backup.csv"):
    ind.to_csv("dim_indicateur_backup.csv", index=False, encoding="utf-8-sig")
    print("[✔] Sauvegarde : dim_indicateur_backup.csv")
else:
    print("[i] dim_indicateur_backup.csv existe déjà (conservé).")


def csv_for(table_pg):
    for f in glob.glob("faits/*/*.csv"):
        if os.path.splitext(os.path.basename(f))[0].startswith(str(table_pg)[:40]):
            return f
    return None


_cache = {}
def load(tp):
    if tp not in _cache:
        f = csv_for(tp)
        _cache[tp] = pd.read_csv(f, encoding="utf-8-sig") if f else None
    return _cache[tp]


def est_defaillant(r):
    """True si l'indicateur couvre moins de 8 provinces OU a >= 3 zéros."""
    df = load(r["table_pg"])
    if df is None:
        return True
    tcol = next((c for c in df.columns if c.strip().lower() == "territoire_id"), None)
    icol = next((c for c in df.columns if c.strip().lower() in ("indicateur", "filtre_indicateur")), None)
    vcol = next((c for c in df.columns if c.strip().lower() in ("valeur", "value")), None)
    if not tcol or vcol is None:
        return True
    sub = df[df[icol].astype(str) == str(r["filtre_indicateur"])] if icol and pd.notna(r["filtre_indicateur"]) else df
    prov = sub[sub[tcol].map(lambda x: niveau.get(int(x)) if str(x).replace(".", "", 1).isdigit() else None) == "prefecture_province"]
    v = pd.to_numeric(prov[vcol], errors="coerce")
    return (prov[tcol].nunique() < 8) or (int((v == 0).sum()) >= 3)


# --- Repérer ce qu'on retire ---
sante = ind[ind.theme == "health"]
ids_defaillants = [int(r["indicateur_id"]) for _, r in sante.iterrows() if est_defaillant(r)]
ids_urbain_rural = [163, 164, 165]  # Population totale Ensemble/Rural/Urbain (incohérents)
a_retirer = set(ids_defaillants) | set(ids_urbain_rural)
print(f"[i] Retrait : {len(ids_defaillants)} indicateurs santé défaillants + {len(ids_urbain_rural)} urbain/rural")

ind = ind[~ind.indicateur_id.isin(a_retirer)].copy()

# --- Ajouter les indicateurs de capacité santé ---
prochaine_id = int(ind.indicateur_id.max()) + 1
capacites = [
    ("nb_essp", "Nombre d'établissements de soins primaires (ESSP)", ""),
    ("nb_hopitaux", "Nombre d'hôpitaux", ""),
    ("nb_medecins_public", "Nombre de médecins (secteur public)", ""),
    ("nb_paramedical_public", "Personnel paramédical (secteur public)", ""),
    ("medecins_pour_10000_hab", "Médecins pour 10 000 habitants", "/10 000 hab"),
    ("paramedical_pour_10000_hab", "Personnel paramédical pour 10 000 habitants", "/10 000 hab"),
    ("essp_pour_100000_hab", "ESSP pour 100 000 habitants", "/100 000 hab"),
]
nouvelles = []
for i, (cle, libelle, unite) in enumerate(capacites):
    nouvelles.append({
        "indicateur_id": prochaine_id + i,
        "nom_indicateur": libelle,
        "theme": "health",
        "table_pg": "health_capacite_province",
        "mode_stockage": "long",
        "colonne_valeur": "valeur",
        "filtre_indicateur": cle,
        "colonne_territoire": "territoire_id",
        "unite": unite,
    })
ind = pd.concat([ind, pd.DataFrame(nouvelles)], ignore_index=True)

# --- Ajouter les indicateurs de population par milieu (urbain / rural) ---
# Ils remplacent les 163/164/165 retirés : la bonne donnée urbain/rural vient
# désormais de la table démographique dérivée demo_population_milieu (RGPH 2024,
# HCP), produite par generer_faits_population.py.
prochaine_id = int(ind.indicateur_id.max()) + 1
population = [
    ("pop_urbain", "Population urbaine (RGPH 2024)", "hab"),
    ("pop_rural", "Population rurale (RGPH 2024)", "hab"),
    ("taux_urbanisation", "Taux d'urbanisation", "%"),
]
pop_rows = []
for i, (cle, libelle, unite) in enumerate(population):
    pop_rows.append({
        "indicateur_id": prochaine_id + i,
        "nom_indicateur": libelle,
        "theme": "demography",
        "table_pg": "demo_population_milieu",
        "mode_stockage": "long",
        "colonne_valeur": "valeur",
        "filtre_indicateur": cle,
        "colonne_territoire": "territoire_id",
        "unite": unite,
    })
ind = pd.concat([ind, pd.DataFrame(pop_rows)], ignore_index=True)

ind.to_csv("dim_indicateur.csv", index=False, encoding="utf-8-sig")
print(f"[✔] dim_indicateur.csv mis à jour : {len(ind)} indicateurs "
      f"(+{len(nouvelles)} capacités santé, +{len(pop_rows)} population milieu)")
