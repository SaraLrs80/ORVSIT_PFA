"""
Récupération du niveau PROVINCE de la cartographie de la pauvreté (HCP, mai 2025).

Le fichier source porte huit niveaux d'agrégation. Seul le niveau communal avait
été chargé — probablement parce que l'extraction avait été faite à la main. Les
dix-sept indicateurs de pauvreté n'existaient donc qu'à la commune, alors que le
fichier donne aussi les huit préfectures et provinces de la région.

Trois précautions gouvernent ce script.

1. LE RAPPROCHEMENT SE FAIT PAR CODE, JAMAIS PAR LIBELLÉ DE NIVEAU.
   Les intitulés du fichier sont décalés : le niveau nommé « commune » contient
   des arrondissements, et « Commune de Tanger » y est rangée sous
   « préfecture d'arrondissement ». Se fier à ces mots reproduirait la confusion
   qui avait déjà produit des doublons dans le fonds cartographique.

2. ON NE CHARGE QUE LA FEUILLE « ENSEMBLE ».
   Les feuilles Urbain et Rural ne comptent pas de cellules vides, mais des
   territoires ABSENTS : 818 communes seulement dans Urbain contre 3 076 dans
   Ensemble, parce qu'une commune entièrement rurale n'y figure pas. Un
   classement établi sur ces feuilles écarterait silencieusement les deux tiers
   du territoire — juste dans son calcul, faux dans sa lecture.

3. RIEN N'EST ÉCRIT SANS SAUVEGARDE NI VÉRIFICATION APRÈS COUP.
   Le script se termine en relisant ce qu'il a écrit et en le comparant à la
   source. S'il ne peut pas prouver son résultat, il le dit.

Usage :  python charger_pauvrete_province.py [--appliquer]
Sans --appliquer, le script ne fait qu'un essai à blanc et n'écrit rien.
"""

import csv
import glob
import os
import shutil
import sys
from datetime import datetime

import openpyxl

SOURCE = "data/socio_economic/cartographie_pauvrete_hcp_mai2025.xlsx"
FEUILLE = "Ensemble"
MILLESIME = "2024"

# Colonne du fichier -> identifiant d'indicateur du catalogue.
# Ce mappage n'est pas supposé : il a été prouvé en comparant les 2 482 valeurs
# communales déjà chargées à celles du fichier, sans un seul écart.
COLONNES = {
    4: 496,   # Indice de pauvreté multidimensionnelle (MPI = H*A)
    5: 497,   # Taux de pauvreté : proportion de la population pauvre
    6: 498,   # Intensité de la pauvreté (A)
    7: 499,   # Taux de vulnérabilité
    8: 430,   # % privé — mortalité infantile
    9: 431,   # % privé — handicap
    10: 486,  # % privé — scolarisation des enfants
    11: 487,  # % privé — années de scolarité
    12: 489,  # % privé — électricité
    13: 490,  # % privé — eau
    14: 491,  # % privé — assainissement
    15: 492,  # % privé — logement
    16: 493,  # % privé — mode de cuisson
    17: 494,  # % privé — moyens de communication
    28: 432,  # décomposition du MPI — santé
    29: 488,  # décomposition du MPI — éducation
    30: 495,  # décomposition du MPI — conditions de vie
}


def horodatage():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def charger_catalogue():
    lignes = list(csv.DictReader(open("dim_indicateur.csv", encoding="utf-8-sig")))
    return lignes, {int(l["indicateur_id"]): l for l in lignes}


def fichier_de_faits(table_pg):
    for f in glob.glob("faits/**/*.csv", recursive=True):
        if "sauvegarde" in f or "_archive" in f:
            continue
        if os.path.basename(f)[:-4] == table_pg:
            return f
    return None


def principal(appliquer: bool):
    if not os.path.exists(SOURCE):
        print(f"[!] Fichier source introuvable : {SOURCE}")
        print("    Déposez-y le classeur HCP, ou corrigez la constante SOURCE.")
        return 1

    lignes_cat, cat = charger_catalogue()

    # --- référentiel indexé par code, comme le fichier ---------------------
    territoires = list(csv.DictReader(open("dim_territoire.csv", encoding="utf-8-sig")))
    provinces = {}
    for x in territoires:
        if x["niveau"] == "prefecture_province" and x["code_hcp"]:
            provinces[int(float(x["code_hcp"]))] = x
    print(f"[i] {len(provinces)} préfectures et provinces dans le référentiel")

    # --- la source ---------------------------------------------------------
    ws = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)[FEUILLE]
    trouvees = {}
    for l in ws.iter_rows(min_row=7, max_col=35, values_only=True):
        if l[1] is None or str(l[3]).strip() != MILLESIME:
            continue
        code = int(l[1])
        if code in provinces:
            trouvees[code] = l
    print(f"[i] {len(trouvees)} provinces retrouvées dans la source pour {MILLESIME}")

    manquantes = [p["nom"] for c, p in provinces.items() if c not in trouvees]
    if manquantes:
        print(f"[!] {len(manquantes)} province(s) absente(s) de la source : "
              f"{', '.join(manquantes)}")
        print("    Chargement interrompu : mieux vaut aucune donnée qu'une donnée partielle.")
        return 1

    # --- constitution des lignes à ajouter, par table de faits -------------
    par_fichier = {}
    vides = []
    for col, ind in COLONNES.items():
        c = cat.get(ind)
        if c is None:
            print(f"[!] L'indicateur {ind} n'est pas au catalogue.")
            return 1
        chemin = fichier_de_faits(c["table_pg"])
        if chemin is None:
            print(f"[!] Table de faits introuvable : {c['table_pg']}")
            return 1
        for code, ligne in trouvees.items():
            valeur = ligne[col]
            if not isinstance(valeur, (int, float)):
                vides.append((c["filtre_indicateur"], provinces[code]["nom"]))
                continue
            par_fichier.setdefault(chemin, []).append({
                "territoire_id": provinces[code]["territoire_id"],
                "indicateur": c["filtre_indicateur"],
                "valeur": repr(float(valeur)),
                "indicateur_id": str(ind),
            })

    total = sum(len(v) for v in par_fichier.values())
    print(f"[i] {total} valeurs à ajouter "
          f"({len(COLONNES)} indicateurs x {len(trouvees)} provinces)")
    if vides:
        print(f"[!] {len(vides)} valeur(s) absente(s) dans la source : {vides[:5]}")

    # --- doublons : ne jamais réécrire une ligne déjà présente -------------
    for chemin, ajouts in par_fichier.items():
        existant = list(csv.DictReader(open(chemin, encoding="utf-8-sig")))
        deja = {(int(l["indicateur_id"]), int(float(l["territoire_id"]))) for l in existant}
        conflits = [a for a in ajouts
                    if (int(a["indicateur_id"]), int(a["territoire_id"])) in deja]
        if conflits:
            print(f"[!] {len(conflits)} ligne(s) déjà présentes dans {chemin}.")
            print("    Le script refuse d'écraser. Vérifier avant de relancer.")
            return 1

    if not appliquer:
        print("\n[·] Essai à blanc — rien n'a été écrit.")
        print("    Relancer avec --appliquer pour enregistrer.")
        for chemin, ajouts in par_fichier.items():
            print(f"    {len(ajouts):>3} lignes -> {chemin}")
        return 0

    # --- écriture, après sauvegarde ---------------------------------------
    marque = horodatage()
    os.makedirs("sauvegardes", exist_ok=True)
    for chemin, ajouts in par_fichier.items():
        sauve = f"sauvegardes/{os.path.basename(chemin)[:-4]}_avant_province_{marque}.csv"
        shutil.copy2(chemin, sauve)
        with open(chemin, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["territoire_id", "indicateur",
                                              "valeur", "indicateur_id"])
            w.writerows(ajouts)
        print(f"[✔] {len(ajouts):>3} lignes ajoutées -> {chemin}  (sauvegarde : {sauve})")

    # --- le catalogue : ces indicateurs descendent maintenant à la province -
    shutil.copy2("dim_indicateur.csv", f"dim_indicateur_avant_province_{marque}.csv")
    for l in lignes_cat:
        if int(l["indicateur_id"]) in COLONNES.values():
            l["dispo_province"] = "True"
            l["source"] = l["source"].replace("niveau commune, 2024",
                                              "niveaux commune et province, 2024")
    with open("dim_indicateur.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes_cat[0].keys()))
        w.writeheader()
        w.writerows(lignes_cat)
    print(f"[✔] Catalogue : dispo_province = True pour {len(COLONNES)} indicateurs")

    return verifier(provinces, trouvees, cat)


def verifier(provinces, trouvees, cat):
    """Relit ce qui vient d'être écrit et le compare à la source.

    Un script qui affirme sans prouver ne vaut pas mieux qu'une saisie manuelle.
    """
    print("\n--- vérification ---")
    faits = {}
    for f in glob.glob("faits/**/*pauvrete*.csv", recursive=True):
        if "sauvegarde" in f or "_archive" in f:
            continue
        for l in csv.DictReader(open(f, encoding="utf-8-sig")):
            faits[(int(l["indicateur_id"]), int(float(l["territoire_id"])))] = float(l["valeur"])

    controles = ecarts = 0
    for col, ind in COLONNES.items():
        for code, ligne in trouvees.items():
            tid = int(provinces[code]["territoire_id"])
            attendu = ligne[col]
            obtenu = faits.get((ind, tid))
            if obtenu is None:
                print(f"[!] Absent après écriture : indicateur {ind}, territoire {tid}")
                ecarts += 1
                continue
            controles += 1
            if abs(float(attendu) - obtenu) > 1e-9:
                print(f"[!] Écart : indicateur {ind}, territoire {tid} — "
                      f"source {attendu}, base {obtenu}")
                ecarts += 1

    print(f"[i] {controles} valeurs relues et comparées à la source")
    if ecarts:
        print(f"[!] {ecarts} écart(s). Restaurer les sauvegardes.")
        return 1
    print("[✔] Aucun écart. Les provinces portent exactement les valeurs du fichier.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal("--appliquer" in sys.argv))
