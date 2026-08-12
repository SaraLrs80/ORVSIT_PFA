"""
Rendre la colonne `annee` cohérente : une ligne, une valeur, un millésime.

LA RÈGLE
`annee` désigne la période de référence de la VALEUR de cette ligne :
    - une année civile          -> 2024
    - une année scolaire        -> 2023-2024
    - une moyenne pluriannuelle -> 2020-2024
Elle ne désigne JAMAIS la date de publication de la source, ni l'étendue
couverte par une famille d'indicateurs.

POURQUOI C'EST NÉCESSAIRE
Le code annonce littéralement « millésime {annee} » — dans la fiche, dans
Comparer et dans les réponses de l'assistant. Une colonne qui porte tantôt le
millésime, tantôt l'année de publication, fait dire au système « millésime
2024 » pour une valeur de 2014.

CE QUI EST CORRIGÉ, ET CE QUI NE L'EST PAS
Corrigé : 8 lignes dont le libellé porte une année différente de la colonne.
    - 65 et 67 portaient l'année de publication du RGPH (2024) pour des
      valeurs de 2014 ;
    - 322 à 327 portaient « 2022-2024 », qui décrit la FAMILLE et non la
      ligne : chacune de ces lignes est une valeur annuelle distincte.

NON corrigé, parce que ces plages sont exactes :
    - 1 à 4      « 2020-2024 » : moyennes climatiques calculées sur cinq ans.
                 Une valeur, une période.
    - 513 à 522  « 2023-2024 » : année scolaire. Une valeur, une année scolaire.

Ces quatorze lignes ne sont pas des anomalies et le script n'y touche pas.

Usage :
    python corriger_millesimes.py              essai à blanc
    python corriger_millesimes.py --appliquer  écrit le CSV puis PostgreSQL
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

# indicateur_id -> (valeur attendue avant, valeur à écrire, justification)
# La valeur « avant » est vérifiée : si elle ne correspond pas, le script
# s'arrête. On ne corrige jamais une ligne dont on n'a pas reconnu l'état.
CORRECTIONS = {
    65:  ("2024", "2014", "Ménages (2014) : 2024 était l'année de publication du RGPH"),
    67:  ("2024", "2014", "Population légale (2014) : idem"),
    322: ("2022-2024", "2022", "la plage décrivait la famille, la ligne vaut 2022"),
    323: ("2022-2024", "2023", "la plage décrivait la famille, la ligne vaut 2023"),
    324: ("2022-2024", "2024", "la plage décrivait la famille, la ligne vaut 2024"),
    325: ("2022-2024", "2022", "la plage décrivait la famille, la ligne vaut 2022"),
    326: ("2022-2024", "2023", "la plage décrivait la famille, la ligne vaut 2023"),
    327: ("2022-2024", "2024", "la plage décrivait la famille, la ligne vaut 2024"),
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
    """Vérifie que chaque ligne à corriger est bien dans l'état attendu."""
    par_id = {int(l["indicateur_id"]): l for l in lignes}
    problemes = []
    for ind, (avant, _, _) in CORRECTIONS.items():
        if ind not in par_id:
            problemes.append(f"indicateur {ind} absent du catalogue")
            continue
        actuel = str(par_id[ind]["annee"]).strip()
        if actuel != avant:
            problemes.append(
                f"indicateur {ind} : annee vaut « {actuel} », "
                f"« {avant} » était attendu — le catalogue a changé depuis l'analyse")
    return problemes


def essai_a_blanc(lignes):
    par_id = {int(l["indicateur_id"]): l for l in lignes}
    print(f"[i] {len(lignes)} lignes au catalogue, {len(CORRECTIONS)} à corriger\n")
    for ind, (avant, apres, raison) in CORRECTIONS.items():
        libelle = par_id[ind]["libelle_court"][:46]
        print(f"    {ind:>4}  {libelle:<46}  {avant:>9} -> {apres}")
        print(f"          {raison}")
    print("\n[·] Essai à blanc — rien n'a été écrit.")
    print("    Relancer avec --appliquer pour corriger.")


def ecrire_csv(lignes, colonnes, marque):
    sauvegarde = f"dim_indicateur_avant_millesimes_{marque}.csv"
    shutil.copy2(CATALOGUE, sauvegarde)

    par_id = {int(l["indicateur_id"]): l for l in lignes}
    for ind, (_, apres, _) in CORRECTIONS.items():
        par_id[ind]["annee"] = apres

    with open(CATALOGUE, "w", encoding="utf-8-sig", newline="") as f:
        redacteur = csv.DictWriter(f, fieldnames=colonnes)
        redacteur.writeheader()
        redacteur.writerows(lignes)

    print(f"[✔] CSV corrigé  (sauvegarde : {sauvegarde})")
    return sauvegarde


def verifier_csv(sauvegarde, colonnes):
    """Compare ligne à ligne, colonne à colonne. Seule `annee` doit bouger."""
    avant, _ = lire(sauvegarde)
    apres, _ = lire(CATALOGUE)

    if len(avant) != len(apres):
        print(f"[!] nombre de lignes différent : {len(avant)} -> {len(apres)}")
        return False

    modifiees, parasites = set(), []
    for a, b in zip(avant, apres):
        if a["indicateur_id"] != b["indicateur_id"]:
            print("[!] l'ordre des lignes a changé")
            return False
        for col in colonnes:
            if a[col] == b[col]:
                continue
            if col == "annee":
                modifiees.add(int(b["indicateur_id"]))
            else:
                parasites.append((b["indicateur_id"], col, a[col], b[col]))

    print(f"\n--- vérification du CSV ---")
    print(f"    lignes                 : {len(apres)} (inchangé)")
    print(f"    colonnes modifiées     : {'annee seulement' if not parasites else 'AUTRES !'}")
    print(f"    lignes dont annee bouge: {len(modifiees)} — {sorted(modifiees)}")

    if parasites:
        for ind, col, a, b in parasites[:10]:
            print(f"[!] modification non voulue — {ind} · {col} : « {a} » -> « {b} »")
        return False
    if modifiees != set(CORRECTIONS):
        print(f"[!] attendues : {sorted(CORRECTIONS)}")
        return False

    print("[✔] Aucune modification non voulue.")
    return True


def ecrire_postgres():
    """
    UPDATE ciblé, jamais un rechargement.

    Recharger la table par `to_sql(if_exists="replace")` exigerait de la
    supprimer, ce que PostgreSQL refuse : les tables de faits portent des
    clés étrangères vers dim_indicateur. Un UPDATE de huit lignes est
    additif, réversible, et ne touche à aucune contrainte.
    """
    e = moteur()
    with e.begin() as conn:
        avant = {r[0]: str(r[1]) for r in conn.execute(text(
            "SELECT indicateur_id, annee FROM referential.dim_indicateur "
            "WHERE indicateur_id = ANY(:ids)"), {"ids": list(CORRECTIONS)})}

        ecarts = [f"{i} : base « {avant.get(i)} » ≠ attendu « {v[0]} »"
                  for i, v in CORRECTIONS.items() if avant.get(i) != v[0]]
        if ecarts:
            print("[!] PostgreSQL n'est pas dans l'état attendu :")
            for x in ecarts:
                print("   ", x)
            print("    Rien n'a été écrit en base.")
            return False

        for ind, (_, apres, _) in CORRECTIONS.items():
            conn.execute(text(
                "UPDATE referential.dim_indicateur SET annee = :a "
                "WHERE indicateur_id = :i"), {"a": apres, "i": ind})

    with e.connect() as conn:
        apres = {r[0]: str(r[1]) for r in conn.execute(text(
            "SELECT indicateur_id, annee FROM referential.dim_indicateur "
            "WHERE indicateur_id = ANY(:ids)"), {"ids": list(CORRECTIONS)})}
        total = conn.execute(text(
            "SELECT count(*) FROM referential.dim_indicateur")).scalar()

    print(f"\n--- vérification de PostgreSQL ---")
    print(f"    lignes de dim_indicateur : {total}")
    mauvais = [i for i, v in CORRECTIONS.items() if apres.get(i) != v[1]]
    for ind, (_, attendu, _) in CORRECTIONS.items():
        etat = "ok" if apres.get(ind) == attendu else "ÉCART"
        print(f"    {ind:>4}  annee = {apres.get(ind):<10} {etat}")
    if mauvais:
        print(f"[!] {len(mauvais)} ligne(s) non conforme(s) : {mauvais}")
        return False
    print("[✔] Les huit lignes sont corrigées en base.")
    return True


def principal(appliquer):
    lignes, colonnes = lire(CATALOGUE)

    problemes = controler(lignes)
    if problemes:
        print("[!] État inattendu, aucune correction n'est tentée :")
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

    if not ecrire_postgres():
        return 1

    print("\n[✔] Catalogue et base cohérents : une ligne, une valeur, un millésime.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal("--appliquer" in sys.argv))
