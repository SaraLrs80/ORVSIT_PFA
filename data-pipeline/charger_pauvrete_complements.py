"""
Compléments de la cartographie de la pauvreté (HCP, mai 2025).

Deux ajouts, tirés du même fichier que le chargement précédent :

  A. Le millésime 2014 des QUATRE indicateurs de tête — indice, taux, intensité,
     vulnérabilité. Ce sont les seuls du catalogue à recevoir une série
     temporelle, et c'est voulu : l'évolution se raconte sur un indice de
     synthèse, pas sur chaque privation prise isolément. Charger 2014 pour les
     dix-sept ferait passer Conditions de vie de 72 à 89 indicateurs pour une
     lecture que personne ne demandera au détail.

  B. La contribution de CHACUNE des dix privations au MPI. Vérifié : ces dix
     valeurs totalisent exactement 100,00 sur les 154 territoires. Elles
     forment donc une seule famille, que la fiche affichera en barre empilée —
     une carte qui répond d'un regard à « qu'est-ce qui fait la pauvreté ici ».

POURQUOI DE NOUVEAUX IDENTIFIANTS PLUTÔT QU'UNE COLONNE `millesime`
Une colonne de millésime aurait été plus élégante : la fiche aurait affiché un
sélecteur, comme pour urbain/rural. Mais `fiche.py` lit ces tables directement,
par `SELECT indicateur, valeur`, et construit un dictionnaire. Deux lignes par
indicateur au lieu d'une, et ce dictionnaire garderait SILENCIEUSEMENT la
dernière — la valeur de 2014 présentée comme celle de 2024. L'ancienne fiche et
Comparer se mettraient à mentir sans lever la moindre erreur.
Les nouveaux identifiants vivent dans de NOUVELLES tables : aucune requête
existante ne les rencontre.

Usage :  python charger_pauvrete_complements.py [--appliquer]
"""

import csv
import os
import shutil
import sys
from datetime import datetime

import openpyxl

SOURCE = "data/socio_economic/cartographie_pauvrete_hcp_mai2025.xlsx"
FEUILLE = "Ensemble"

# --- A. le millésime 2014 des quatre indicateurs de tête --------------------
# (colonne du fichier, identifiant 2024 à renommer, nouveau libellé de famille)
HISTORIQUE = [
    (4, 496, "Indice de pauvreté multidimensionnelle MPI", "indice", "bas_mieux"),
    (5, 497, "Taux de pauvreté multidimensionnelle incidence H", "%", "bas_mieux"),
    (6, 498, "Intensité de la pauvreté multidimensionnelle A", "%", "bas_mieux"),
    (7, 499, "Taux de vulnérabilité à la pauvreté multidimensionnelle", "%", "bas_mieux"),
]
TABLE_HISTORIQUE = "socio_economic_pauvrete_indice_2014"

# --- B. la contribution de chaque privation au MPI --------------------------
# La convention « — » les regroupe en une seule famille. Toutes en Conditions
# de vie : c'est la décomposition d'un indicateur de ce secteur, et les séparer
# par dimension casserait le total à 100 % qui justifie la barre empilée.
CONTRIBUTIONS = [
    (18, "Mortalité infantile", "contrib_ind_mortalite_infantile"),
    (19, "Handicap", "contrib_ind_handicap"),
    (20, "Scolarisation des enfants", "contrib_ind_scolarisation"),
    (21, "Années de scolarité", "contrib_ind_annees_scolarite"),
    (22, "Électricité", "contrib_ind_electricite"),
    (23, "Eau", "contrib_ind_eau"),
    (24, "Assainissement", "contrib_ind_assainissement"),
    (25, "Logement", "contrib_ind_logement"),
    (26, "Mode de cuisson", "contrib_ind_cuisson"),
    (27, "Moyens de communication", "contrib_ind_communication"),
]
TABLE_CONTRIBUTIONS = "socio_economic_pauvrete_decomposition_mpi"
FAMILLE_CONTRIBUTIONS = "Contribution au MPI"

SOURCE_TEXTE = ("HCP — Cartographie de la pauvreté multidimensionnelle (Mai 2025), "
                "niveaux commune et province")


def horodatage():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def principal(appliquer: bool):
    if not os.path.exists(SOURCE):
        print(f"[!] Fichier source introuvable : {SOURCE}")
        return 1

    lignes_cat = list(csv.DictReader(open("dim_indicateur.csv", encoding="utf-8-sig")))
    champs = list(lignes_cat[0].keys())
    par_id = {int(l["indicateur_id"]): l for l in lignes_cat}
    suivant = max(int(l["indicateur_id"]) for l in lignes_cat) + 1

    # --- territoires servis, indexés par code, comme le fichier ------------
    territoires = {}
    for x in csv.DictReader(open("dim_territoire.csv", encoding="utf-8-sig")):
        if x["code_hcp"] and x["niveau"] in ("commune", "prefecture_province"):
            territoires[int(float(x["code_hcp"]))] = x
    print(f"[i] {len(territoires)} territoires servis dans le référentiel")

    # --- la source, par code et par millésime -------------------------------
    ws = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)[FEUILLE]
    source = {}
    for l in ws.iter_rows(min_row=7, max_col=35, values_only=True):
        if l[1] is None:
            continue
        code = int(l[1])
        if code in territoires:
            source[(code, str(l[3]).strip())] = l
    for annee in ("2014", "2024"):
        n = sum(1 for (c, a) in source if a == annee)
        print(f"[i] {n} territoires trouvés pour {annee}")
        if n != len(territoires):
            print(f"[!] Millésime {annee} incomplet ({n}/{len(territoires)}). "
                  f"Chargement interrompu : mieux vaut rien qu'une donnée partielle.")
            return 1

    nouveaux, faits = [], {TABLE_HISTORIQUE: [], TABLE_CONTRIBUTIONS: []}
    renommages = []

    # ---------------- A. le millésime 2014 ---------------------------------
    for col, id_2024, famille, unite, sens in HISTORIQUE:
        ancien = par_id[id_2024]
        renommages.append((id_2024, ancien["libelle_court"], f"{famille} (2024)"))
        nouveaux.append({
            **{c: "" for c in champs},
            "indicateur_id": str(suivant),
            "nom_indicateur": f"{famille} (2014)",
            "nom_origine": ancien["nom_origine"],
            "theme": "socio_economic",
            "definition": (f"{famille}, millésime 2014. Valeur publiée par le HCP sur le "
                           f"découpage territorial actuel, donc comparable à celle de 2024."),
            "unite": unite,
            "source": f"{SOURCE_TEXTE}, 2014",
            "annee": "2014",
            "statut": "validé",
            "table_pg": TABLE_HISTORIQUE,
            "mode_stockage": "long",
            "colonne_valeur": "valeur",
            "filtre_indicateur": f"{ancien['filtre_indicateur']}_2014",
            "colonne_territoire": "territoire_id",
            "libelle_court": f"{famille} (2014)",
            "secteur": "Conditions de vie",
            "dispo_province": "True",
            "dispo_commune": "True",
            "sens": sens,
        })
        for (code, annee), ligne in source.items():
            if annee != "2014":
                continue
            v = ligne[col]
            if not isinstance(v, (int, float)):
                print(f"[!] Valeur absente : {famille} 2014, code {code}")
                return 1
            faits[TABLE_HISTORIQUE].append({
                "territoire_id": territoires[code]["territoire_id"],
                "indicateur": f"{ancien['filtre_indicateur']}_2014",
                "valeur": repr(float(v)),
                "indicateur_id": str(suivant),
            })
        suivant += 1

    # ---------------- B. les contributions par privation --------------------
    for col, etiquette, filtre in CONTRIBUTIONS:
        nouveaux.append({
            **{c: "" for c in champs},
            "indicateur_id": str(suivant),
            "nom_indicateur": f"{FAMILLE_CONTRIBUTIONS} — {etiquette}",
            "nom_origine": filtre,
            "theme": "socio_economic",
            "definition": (f"Part de la privation « {etiquette} » dans l'indice de pauvreté "
                           f"multidimensionnelle. Les dix privations totalisent 100 %."),
            "unite": "%",
            "source": f"{SOURCE_TEXTE}, 2024",
            "annee": "2024",
            "statut": "validé",
            "table_pg": TABLE_CONTRIBUTIONS,
            "mode_stockage": "long",
            "colonne_valeur": "valeur",
            "filtre_indicateur": filtre,
            "colonne_territoire": "territoire_id",
            "libelle_court": f"{FAMILLE_CONTRIBUTIONS} — {etiquette}",
            "secteur": "Conditions de vie",
            "dispo_province": "True",
            "dispo_commune": "True",
            # Une part de contribution n'est ni bonne ni mauvaise : elle dit
            # d'où vient la pauvreté, pas si c'est mieux ou pire.
            "sens": "neutre",
        })
        for (code, annee), ligne in source.items():
            if annee != "2024":
                continue
            v = ligne[col]
            if not isinstance(v, (int, float)):
                print(f"[!] Valeur absente : contribution {etiquette}, code {code}")
                return 1
            faits[TABLE_CONTRIBUTIONS].append({
                "territoire_id": territoires[code]["territoire_id"],
                "indicateur": filtre,
                "valeur": repr(float(v)),
                "indicateur_id": str(suivant),
            })
        suivant += 1

    print(f"\n[i] {len(nouveaux)} indicateurs à créer, "
          f"{len(renommages)} libellés à renommer")
    for t, l in faits.items():
        print(f"[i] {len(l):>5} valeurs -> faits/socio_economic/{t}.csv")

    if not appliquer:
        print("\n[·] Essai à blanc — rien n'a été écrit.")
        for i, ancien, neuf in renommages:
            print(f"    [{i}] « {ancien} »\n          -> « {neuf} »")
        for n in nouveaux:
            print(f"    [{n['indicateur_id']}] {n['libelle_court']}")
        return 0

    # ---------------- écriture ---------------------------------------------
    marque = horodatage()
    shutil.copy2("dim_indicateur.csv", f"dim_indicateur_avant_complements_{marque}.csv")

    for i, _, neuf in renommages:
        par_id[i]["libelle_court"] = neuf
        par_id[i]["nom_indicateur"] = neuf
    lignes_cat.extend(nouveaux)
    with open("dim_indicateur.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=champs)
        w.writeheader()
        w.writerows(lignes_cat)
    print(f"[✔] Catalogue : {len(lignes_cat)} lignes "
          f"({len(nouveaux)} ajoutées, {len(renommages)} renommées)")

    os.makedirs("faits/socio_economic", exist_ok=True)
    for table, lignes in faits.items():
        chemin = f"faits/socio_economic/{table}.csv"
        if os.path.exists(chemin):
            print(f"[!] {chemin} existe déjà. Le script refuse d'écraser.")
            return 1
        with open(chemin, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["territoire_id", "indicateur",
                                              "valeur", "indicateur_id"])
            w.writeheader()
            w.writerows(lignes)
        print(f"[✔] {len(lignes):>5} lignes -> {chemin}")

    return verifier(territoires, source, nouveaux)


def verifier(territoires, source, nouveaux):
    """Relit ce qui vient d'être écrit et le compare à la source."""
    print("\n--- vérification ---")
    colonne = {}
    for col, id_2024, famille, *_ in HISTORIQUE:
        colonne[f"{famille} (2014)"] = (col, "2014")
    for col, etiquette, _ in CONTRIBUTIONS:
        colonne[f"{FAMILLE_CONTRIBUTIONS} — {etiquette}"] = (col, "2024")

    faits = {}
    for table in (TABLE_HISTORIQUE, TABLE_CONTRIBUTIONS):
        for l in csv.DictReader(open(f"faits/socio_economic/{table}.csv",
                                     encoding="utf-8-sig")):
            faits[(int(l["indicateur_id"]), int(l["territoire_id"]))] = float(l["valeur"])

    controles = ecarts = 0
    for n in nouveaux:
        col, annee = colonne[n["libelle_court"]]
        for code, t in territoires.items():
            ligne = source.get((code, annee))
            attendu = ligne[col]
            obtenu = faits.get((int(n["indicateur_id"]), int(t["territoire_id"])))
            if obtenu is None:
                print(f"[!] Absent : {n['libelle_court']} / {t['nom']}")
                ecarts += 1
                continue
            controles += 1
            if abs(float(attendu) - obtenu) > 1e-9:
                print(f"[!] Écart : {n['libelle_court']} / {t['nom']} — "
                      f"source {attendu}, base {obtenu}")
                ecarts += 1

    # Contrôle de cohérence propre à ce jeu : les dix contributions doivent
    # totaliser 100 % pour chaque territoire. C'est une vérification de la
    # DONNÉE, pas du transfert — elle prouve qu'on a pris les bonnes colonnes.
    ids = [int(n["indicateur_id"]) for n in nouveaux
           if n["libelle_court"].startswith(FAMILLE_CONTRIBUTIONS)]
    pires = []
    for t in territoires.values():
        somme = sum(faits.get((i, int(t["territoire_id"])), 0) for i in ids)
        pires.append((abs(somme - 100), t["nom"], somme))
    pires.sort(reverse=True)
    print(f"[i] {controles} valeurs relues et comparées à la source")
    print(f"[i] Somme des dix contributions — écart maximal à 100 % : "
          f"{pires[0][0]:.6f} ({pires[0][1]})")
    if pires[0][0] > 0.01:
        print("[!] Les contributions ne totalisent pas 100 % : colonnes suspectes.")
        ecarts += 1

    if ecarts:
        print(f"[!] {ecarts} anomalie(s). Restaurer les sauvegardes.")
        return 1
    print("[✔] Aucun écart.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal("--appliquer" in sys.argv))
