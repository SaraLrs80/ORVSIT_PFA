"""
Ajouter au catalogue les mots que les gens emploient réellement.

LE PROBLÈME MESURÉ
Sur les 65 questions du jeu d'évaluation, quatre familles contiennent le mot
« population » dans leur nom. À la question « la population de Tétouan ? »
elles obtiennent toutes la même couverture, le même mot dans leur nom, la même
précision : le classement n'a plus rien pour les départager, et l'ordre final
est celui du dictionnaire Python. « Population légale » n'apparaît même pas
dans les trois premiers candidats.

Aucune règle de calcul ne peut corriger cela. Que « population » désigne
« Population légale » n'est pas déductible du texte : c'est une connaissance
sur les données, elle appartient donc au catalogue.

DEUX EMPLOIS D'UN MOT-CLÉ
  1. combler un manque   « habitants » sur Population légale, dont le libellé
                          ne contient pas ce mot ;
  2. désigner le canonique  « population » sur Population légale, alors que le
                          mot est déjà dans son nom, pour trancher entre quatre
                          familles à égalité.

CE QU'UN MOT-CLÉ NE PEUT PAS FAIRE
Il n'intervient qu'à couverture ÉGALE. « habitants par médecin » couvre deux
mots pour « Habitants par médecin » contre un seul pour « Population légale » :
le mot-clé ne renversera jamais ce résultat. C'est ce qui rend l'ajout sûr.

POURQUOI SI PEU DE LIGNES
Quatre familles seulement. Chaque mot-clé répond à une question qui échoue
aujourd'hui — pas d'ajout « au cas où ». Ce qui n'améliore rien à la mesure
suivante sera retiré.

Usage :
    python ajouter_mots_cles.py              essai à blanc
    python ajouter_mots_cles.py --appliquer  écrit le CSV puis PostgreSQL
"""

import csv
import os
import shutil
import sys
import urllib.parse
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

CATALOGUE = "dim_indicateur.csv"
COLONNE = "mots_cles"

# Les mots-clés sont posés sur CHAQUE membre de la famille, pas seulement sur
# le premier : l'indicateur 67 n'existe qu'au niveau province, et la famille
# perdrait ses mots-clés au niveau communal s'ils ne tenaient qu'à lui.
MOTS_CLES = {
    # Population légale — départage quatre familles « population » à égalité,
    # et comble l'absence du mot « habitants » dans le libellé (A3, C3, B2,
    # C1, C4, N10).
    #
    # « gens » et « personnes » ont été RETIRÉS après mesure : aucune question
    # du jeu ne les emploie pour désigner la population, et ils causaient deux
    # régressions — « combien de gens qui travaillent pas » répondait la
    # population au lieu du chômage, et « ordinateur personnel » réveillait la
    # population par la racine commune de « personnel » et « personnes ».
    # Règle appliquée : pas de mot-clé sans une question qui le justifie.
    40:  "population habitants",
    67:  "population habitants",

    # Taux de pauvreté — désigne le canonique face aux quatre familles de
    # « Contribution au MPI » et à « Taux de vulnérabilité » (B1, F3, A4).
    497: "pauvreté pauvres",
    527: "pauvreté pauvres",

    # Taux de chômage — « chômeurs » ne partage pas la racine de « chômage »
    # une fois tronquée à six lettres (chomag / chomeu).
    393: "chômeurs",

    # Ordinateur personnel — « informatique » est absent du libellé (N5).
    368: "informatique",
}


def moteur():
    user = urllib.parse.quote_plus(os.getenv("DB_USER", "postgres"))
    mdp = urllib.parse.quote_plus(os.getenv("DB_PASSWORD", ""))
    hote = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    base = os.getenv("DB_NAME", "dwh_orvsit")
    return create_engine(f"postgresql://{user}:{mdp}@{hote}:{port}/{base}")


def lire(chemin):
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        lecteur = csv.DictReader(f)
        return list(lecteur), list(lecteur.fieldnames)


def controler(lignes):
    """Les indicateurs visés existent-ils, et la colonne est-elle déjà là ?"""
    presents = {int(l["indicateur_id"]) for l in lignes}
    manquants = sorted(set(MOTS_CLES) - presents)
    if manquants:
        return [f"indicateur(s) absent(s) du catalogue : {manquants}"]
    return []


def essai_a_blanc(lignes, colonnes):
    par_id = {int(l["indicateur_id"]): l for l in lignes}
    deja = COLONNE in colonnes
    print(f"[i] {len(lignes)} lignes au catalogue")
    print(f"[i] colonne « {COLONNE} » : {'déjà présente' if deja else 'à créer'}")
    print(f"[i] {len(MOTS_CLES)} lignes recevront des mots-clés, "
          f"{len(lignes) - len(MOTS_CLES)} resteront vides\n")
    for ind, mots in MOTS_CLES.items():
        print(f"    {ind:>4}  {par_id[ind]['libelle_court'][:44]:<44}  <- {mots}")
    print("\n[·] Essai à blanc — rien n'a été écrit.")
    print("    Relancer avec --appliquer pour écrire.")


def ecrire_csv(lignes, colonnes, marque):
    sauvegarde = f"dim_indicateur_avant_mots_cles_{marque}.csv"
    shutil.copy2(CATALOGUE, sauvegarde)

    if COLONNE not in colonnes:
        colonnes = colonnes + [COLONNE]
    for ligne in lignes:
        ligne.setdefault(COLONNE, "")
        ligne[COLONNE] = MOTS_CLES.get(int(ligne["indicateur_id"]),
                                       ligne.get(COLONNE) or "")

    with open(CATALOGUE, "w", encoding="utf-8-sig", newline="") as f:
        redacteur = csv.DictWriter(f, fieldnames=colonnes)
        redacteur.writeheader()
        redacteur.writerows(lignes)

    print(f"[✔] CSV écrit  (sauvegarde : {sauvegarde})")
    return sauvegarde, colonnes


def verifier_csv(sauvegarde, colonnes_avant):
    """Aucune colonne existante ne doit bouger. Seule `mots_cles` apparaît."""
    avant, cols_avant = lire(sauvegarde)
    apres, cols_apres = lire(CATALOGUE)

    print("\n--- vérification du CSV ---")
    if len(avant) != len(apres):
        print(f"[!] nombre de lignes : {len(avant)} -> {len(apres)}")
        return False
    if cols_apres != cols_avant + [COLONNE] and cols_apres != cols_avant:
        print(f"[!] colonnes inattendues : {cols_apres}")
        return False

    remplies, parasites = set(), []
    for a, b in zip(avant, apres):
        if a["indicateur_id"] != b["indicateur_id"]:
            print("[!] l'ordre des lignes a changé")
            return False
        # Les anciennes colonnes seulement — et jamais mots_cles elle-même,
        # sans quoi le script ne pourrait pas être rejoué pour corriger un
        # mot-clé qui s'est révélé mauvais à la mesure.
        for col in cols_avant:
            if col == COLONNE:
                continue
            if a[col] != b[col]:
                parasites.append((b["indicateur_id"], col, a[col], b[col]))
        if (b.get(COLONNE) or "").strip():
            remplies.add(int(b["indicateur_id"]))

    print(f"    lignes                 : {len(apres)} (inchangé)")
    print(f"    colonnes d'origine     : {'intactes' if not parasites else 'MODIFIÉES !'}")
    print(f"    lignes avec mots-clés  : {len(remplies)} — {sorted(remplies)}")

    if parasites:
        for ind, col, a, b in parasites[:10]:
            print(f"[!] modification non voulue — {ind} · {col} : « {a} » -> « {b} »")
        return False
    if remplies != set(MOTS_CLES):
        print(f"[!] attendues : {sorted(MOTS_CLES)}")
        return False

    print("[✔] Aucune colonne d'origine modifiée.")
    return True


def ecrire_postgres():
    """
    ALTER TABLE puis UPDATE — jamais un rechargement.

    Les tables de faits portent des clés étrangères vers dim_indicateur :
    la supprimer pour la recréer échouerait. Ajouter une colonne est additif
    et se défait par un DROP COLUMN.
    """
    e = moteur()
    with e.begin() as conn:
        conn.execute(text(
            f"ALTER TABLE referential.dim_indicateur "
            f"ADD COLUMN IF NOT EXISTS {COLONNE} text DEFAULT ''"))
        conn.execute(text(
            f"UPDATE referential.dim_indicateur SET {COLONNE} = '' "
            f"WHERE {COLONNE} IS NULL"))
        for ind, mots in MOTS_CLES.items():
            conn.execute(text(
                f"UPDATE referential.dim_indicateur SET {COLONNE} = :m "
                f"WHERE indicateur_id = :i"), {"m": mots, "i": ind})

    with e.connect() as conn:
        total = conn.execute(text(
            "SELECT count(*) FROM referential.dim_indicateur")).scalar()
        remplies = conn.execute(text(
            f"SELECT indicateur_id, {COLONNE} FROM referential.dim_indicateur "
            f"WHERE coalesce({COLONNE}, '') <> '' ORDER BY indicateur_id")).all()

    print("\n--- vérification de PostgreSQL ---")
    print(f"    lignes de dim_indicateur : {total}")
    for ind, mots in remplies:
        etat = "ok" if MOTS_CLES.get(ind) == mots else "ÉCART"
        print(f"    {ind:>4}  {mots:<38} {etat}")
    obtenues = {i: m for i, m in remplies}
    if obtenues != MOTS_CLES:
        print(f"[!] la base ne correspond pas à ce qui était demandé")
        return False
    print("[✔] Colonne ajoutée et renseignée.")
    return True


def principal(appliquer):
    lignes, colonnes = lire(CATALOGUE)

    problemes = controler(lignes)
    if problemes:
        print("[!] État inattendu, rien n'est tenté :")
        for p in problemes:
            print("   ", p)
        return 1

    if not appliquer:
        essai_a_blanc(lignes, colonnes)
        return 0

    marque = datetime.now().strftime("%Y%m%d_%H%M%S")
    sauvegarde, _ = ecrire_csv(lignes, colonnes, marque)

    if not verifier_csv(sauvegarde, colonnes):
        print(f"\n[!] Restaurer avec :  copy {sauvegarde} {CATALOGUE}")
        return 1

    if not ecrire_postgres():
        return 1

    print("\n[✔] Le catalogue porte désormais le vocabulaire des utilisateurs.")
    print("    Prochaine étape : remesurer, et retirer ce qui n'améliore rien.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal("--appliquer" in sys.argv))
