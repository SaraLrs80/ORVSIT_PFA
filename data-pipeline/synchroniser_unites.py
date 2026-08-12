"""
Remettre la colonne `unite` en ordre, dans le catalogue ET dans PostgreSQL.

DEUX PROBLÈMES DISTINCTS, ET LE SECOND EST LE PLUS INSTRUCTIF

1. Deux unités n'en sont pas.
   « indice » : l'indice de pauvreté multidimensionnelle est un nombre sans
   dimension, produit de deux proportions. Écrire « 0,152 indice » n'a pas de
   sens, et le libellé annonce déjà « Indice de pauvreté ». L'unité est vidée.
   « nombre » : quatre indicateurs comptent des abonnés ou des mouvements
   d'avions. « 173 885 nombre » se lit mal ; on nomme la chose comptée.

2. Le catalogue et la base ne disent plus la même chose.
   Une correction d'unités faite plus tôt a été écrite dans le CSV mais jamais
   propagée : on avait cessé de recharger par charger_postgres.py — à raison,
   les tables de faits portent des clés étrangères vers dim_indicateur — mais
   aucun UPDATE ciblé n'a suivi. L'assistant répondait donc « 5 nombre » là où
   le catalogue disait « établissements ».

   La leçon vaut au-delà de cette colonne : dès lors qu'on renonce au
   rechargement global, chaque correction du CSV doit être suivie de sa
   propagation, sinon les deux sources divergent en silence.

Ce script ne corrige donc pas seulement les six lignes fautives : il aligne
TOUTE la colonne `unite` de PostgreSQL sur le catalogue, et dit combien de
lignes avaient divergé.

Usage :
    python synchroniser_unites.py              essai à blanc
    python synchroniser_unites.py --appliquer  écrit le CSV puis PostgreSQL
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

# indicateur_id -> (unité attendue avant, unité à écrire, justification)
CORRECTIONS = {
    496: ("indice", "", "un indice est sans dimension ; le libellé le nomme déjà"),
    526: ("indice", "", "idem, millésime 2014"),
    266: ("nombre", "abonnés", "on nomme la chose comptée"),
    302: ("nombre", "mouvements", "mouvements d'avions"),
    303: ("nombre", "mouvements", "mouvements d'avions"),
    304: ("nombre", "mouvements", "mouvements d'avions"),
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
    par_id = {int(l["indicateur_id"]): l for l in lignes}
    problemes = []
    for ind, (avant, _, _) in CORRECTIONS.items():
        if ind not in par_id:
            problemes.append(f"indicateur {ind} absent du catalogue")
            continue
        actuel = (par_id[ind]["unite"] or "").strip()
        if actuel != avant:
            problemes.append(
                f"indicateur {ind} : unite vaut « {actuel} », « {avant} » "
                f"était attendu — le catalogue a changé depuis l'analyse")
    return problemes


def ecarts_avec_la_base(lignes):
    """Les lignes dont l'unité diffère entre le catalogue et PostgreSQL."""
    attendu = {int(l["indicateur_id"]): (l["unite"] or "").strip() for l in lignes}
    with moteur().connect() as conn:
        en_base = {r[0]: (r[1] or "").strip() for r in conn.execute(text(
            "SELECT indicateur_id, unite FROM referential.dim_indicateur"))}
    return {i: (en_base.get(i), u) for i, u in attendu.items()
            if i in en_base and en_base[i] != u}


def essai_a_blanc(lignes):
    par_id = {int(l["indicateur_id"]): l for l in lignes}
    print(f"[i] {len(lignes)} lignes au catalogue\n")
    print("--- corrections du catalogue ---")
    for ind, (avant, apres, raison) in CORRECTIONS.items():
        print(f"    {ind:>4}  {par_id[ind]['libelle_court'][:44]:<44} "
              f"« {avant} » -> « {apres} »")
        print(f"          {raison}")

    try:
        divergents = ecarts_avec_la_base(lignes)
    except Exception as e:
        print(f"\n[!] PostgreSQL injoignable : {e}")
        return
    print(f"\n--- écarts entre le catalogue et PostgreSQL : {len(divergents)} ---")
    for ind, (en_base, au_catalogue) in sorted(divergents.items())[:25]:
        print(f"    {ind:>4}  base « {en_base} »  ->  catalogue « {au_catalogue} »")
    if len(divergents) > 25:
        print(f"    … et {len(divergents) - 25} autres")
    print("\n[·] Essai à blanc — rien n'a été écrit.")


def ecrire_csv(lignes, colonnes, marque):
    sauvegarde = f"dim_indicateur_avant_unites_{marque}.csv"
    shutil.copy2(CATALOGUE, sauvegarde)
    par_id = {int(l["indicateur_id"]): l for l in lignes}
    for ind, (_, apres, _) in CORRECTIONS.items():
        par_id[ind]["unite"] = apres
    with open(CATALOGUE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colonnes)
        w.writeheader()
        w.writerows(lignes)
    print(f"[✔] CSV corrigé  (sauvegarde : {sauvegarde})")
    return sauvegarde


def verifier_csv(sauvegarde, colonnes):
    avant, _ = lire(sauvegarde)
    apres, _ = lire(CATALOGUE)
    if len(avant) != len(apres):
        print(f"[!] nombre de lignes : {len(avant)} -> {len(apres)}")
        return False
    modifiees, parasites = set(), []
    for a, b in zip(avant, apres):
        if a["indicateur_id"] != b["indicateur_id"]:
            print("[!] l'ordre des lignes a changé")
            return False
        for col in colonnes:
            if a[col] == b[col]:
                continue
            if col == "unite":
                modifiees.add(int(b["indicateur_id"]))
            else:
                parasites.append((b["indicateur_id"], col, a[col], b[col]))
    print("\n--- vérification du CSV ---")
    print(f"    lignes                  : {len(apres)} (inchangé)")
    print(f"    colonnes modifiées      : "
          f"{'unite seulement' if not parasites else 'AUTRES !'}")
    print(f"    lignes dont unite bouge : {len(modifiees)} — {sorted(modifiees)}")
    if parasites:
        for ind, col, a, b in parasites[:10]:
            print(f"[!] modification non voulue — {ind} · {col} : "
                  f"« {a} » -> « {b} »")
        return False
    if modifiees != set(CORRECTIONS):
        print(f"[!] attendues : {sorted(CORRECTIONS)}")
        return False
    print("[✔] Aucune modification non voulue.")
    return True


def ecrire_postgres(lignes):
    """UPDATE ciblé de toutes les lignes divergentes. Jamais un rechargement."""
    divergents = ecarts_avec_la_base(lignes)
    if not divergents:
        print("\n[✔] PostgreSQL était déjà aligné sur le catalogue.")
        return True

    e = moteur()
    with e.begin() as conn:
        for ind, (_, au_catalogue) in divergents.items():
            conn.execute(text(
                "UPDATE referential.dim_indicateur SET unite = :u "
                "WHERE indicateur_id = :i"), {"u": au_catalogue, "i": ind})

    restants = ecarts_avec_la_base(lignes)
    print(f"\n--- vérification de PostgreSQL ---")
    print(f"    lignes alignées : {len(divergents)}")
    print(f"    écarts restants : {len(restants)}")
    if restants:
        for ind, (b, c) in sorted(restants.items())[:10]:
            print(f"[!] {ind} : base « {b} » ≠ catalogue « {c} »")
        return False
    print("[✔] Le catalogue et la base disent la même chose.")
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
        essai_a_blanc(lignes)
        return 0

    marque = datetime.now().strftime("%Y%m%d_%H%M%S")
    sauvegarde = ecrire_csv(lignes, colonnes, marque)
    if not verifier_csv(sauvegarde, colonnes):
        print(f"\n[!] Restaurer avec :  copy {sauvegarde} {CATALOGUE}")
        return 1

    lignes, _ = lire(CATALOGUE)          # on repart du CSV corrigé
    if not ecrire_postgres(lignes):
        return 1

    print("\n[✔] Unités cohérentes du catalogue jusqu'à la réponse de l'assistant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal("--appliquer" in sys.argv))
