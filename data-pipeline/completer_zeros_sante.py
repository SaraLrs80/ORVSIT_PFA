"""
Les zéros manquants des registres d'établissements de santé.

CE QUI EST CORRIGÉ
Trois indicateurs — module d'accouchement, unité UMP, rattachement RAMED —
n'ont de valeur que pour les territoires figurant au registre. Les autres n'ont
aucune ligne, et l'application les présente donc comme « non renseignés ».
C'est faux : ce sont des zéros.

POURQUOI C'EST UN ZÉRO ET NON UNE ABSENCE
Un registre d'établissements ne liste que les territoires qui en ont. La
question n'est donc pas « le territoire figure-t-il ? » mais « le registre
est-il exhaustif ? ». Trois preuves qu'il l'est :

  1. Le fichier des cliniques privées, issu de la même source, couvre les
     57 provinces du Maroc — y compris celles qui n'ont qu'UNE clinique
     (Ouezzane, Sefrou, Guercif, Ifrane). Un extrait partiel aurait coupé les
     petites valeurs ; celui-ci ne coupe nulle part.
  2. Les trois registres régionaux enregistrent eux aussi des provinces à 1, 3
     ou 5 établissements. Un registre qui note une province ayant un seul
     établissement note tout ce qu'il connaît.
  3. Le contenu est cohérent : une unité médicale de proximité est un
     dispositif rural, et son absence à Tanger-Assilah — la province la plus
     urbaine — s'explique, elle n'étonne pas.

CE QUI N'EST PAS CORRIGÉ
Un territoire qui FIGURE au fichier avec un tiret reste non renseigné. Et un
registre manifestement partiel — qui ne couvrirait que quelques provinces sans
descendre aux petites valeurs — garderait le traitement inverse. La règle n'est
pas « absence = zéro », elle est « absence dans un registre exhaustif = zéro ».

Usage :  python completer_zeros_sante.py [--appliquer]
"""

import csv
import glob
import os
import shutil
import sys
from datetime import datetime

INDICATEURS = [523, 524, 525]

PREUVE = ("[Traçabilité : registre exhaustif — le fichier de même source couvre les "
          "57 provinces du Maroc, y compris celles n'ayant qu'un seul établissement. "
          "Un territoire absent du registre n'a donc aucun établissement : sa valeur "
          "est zéro, et non une donnée manquante.]")


def fichier_de_faits(table_pg):
    for f in glob.glob("faits/**/*.csv", recursive=True):
        if "sauvegarde" in f or "_archive" in f:
            continue
        if os.path.basename(f)[:-4] == table_pg:
            return f
    return None


def principal(appliquer: bool):
    cat = {int(l["indicateur_id"]): l
           for l in csv.DictReader(open("dim_indicateur.csv", encoding="utf-8-sig"))}
    territoires = [x for x in csv.DictReader(open("dim_territoire.csv", encoding="utf-8-sig"))
                   if x["niveau"] in ("commune", "prefecture_province")]
    attendus = {int(x["territoire_id"]): x["nom"] for x in territoires}
    print(f"[i] {len(attendus)} territoires servis "
          f"({sum(1 for x in territoires if x['niveau'] == 'commune')} communes, "
          f"{sum(1 for x in territoires if x['niveau'] == 'prefecture_province')} provinces)")

    ajouts = {}
    for ind in INDICATEURS:
        c = cat.get(ind)
        if c is None:
            print(f"[!] Indicateur {ind} absent du catalogue.")
            return 1
        chemin = fichier_de_faits(c["table_pg"])
        if chemin is None:
            print(f"[!] Table de faits introuvable : {c['table_pg']}")
            return 1

        lignes = list(csv.DictReader(open(chemin, encoding="utf-8-sig")))
        champs = list(lignes[0].keys())
        presents = {int(float(l["territoire_id"])) for l in lignes
                    if l.get("indicateur_id") == str(ind)}
        manquants = sorted(set(attendus) - presents)

        print(f"\n[{ind}] {c['libelle_court'][:52]}")
        print(f"      colonnes : {champs}")
        print(f"      {len(presents)}/{len(attendus)} territoires renseignés, "
              f"{len(manquants)} zéros à poser")

        nouvelles = []
        for tid in manquants:
            ligne = {ch: "" for ch in champs}
            ligne.update({"territoire_id": str(tid),
                          "indicateur": c["filtre_indicateur"],
                          "valeur": "0.0",
                          "indicateur_id": str(ind)})
            # Une colonne de ventilation éventuelle reprend la valeur déjà
            # employée par les lignes existantes : on ne crée pas une modalité
            # nouvelle en posant un zéro.
            for ch in champs:
                if ch in ("territoire_id", "indicateur", "valeur", "indicateur_id"):
                    continue
                vues = {l[ch] for l in lignes if l.get("indicateur_id") == str(ind)}
                if len(vues) == 1:
                    ligne[ch] = vues.pop()
            nouvelles.append(ligne)

        ajouts[chemin] = ajouts.get(chemin, []) + nouvelles

    total = sum(len(v) for v in ajouts.values())
    print(f"\n[i] {total} zéros à poser au total")

    if not appliquer:
        print("\n[·] Essai à blanc — rien n'a été écrit.")
        for chemin, l in ajouts.items():
            print(f"    {len(l):>3} lignes -> {chemin}")
        return 0

    marque = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("sauvegardes", exist_ok=True)
    for chemin, nouvelles in ajouts.items():
        if not nouvelles:
            continue
        sauve = f"sauvegardes/{os.path.basename(chemin)[:-4]}_avant_zeros_{marque}.csv"
        shutil.copy2(chemin, sauve)
        champs = list(csv.DictReader(open(chemin, encoding="utf-8-sig")).fieldnames)
        with open(chemin, "a", encoding="utf-8-sig", newline="") as f:
            csv.DictWriter(f, fieldnames=champs).writerows(nouvelles)
        print(f"[✔] {len(nouvelles):>3} zéros -> {chemin}  (sauvegarde : {sauve})")

    # --- la preuve d'exhaustivité voyage avec la donnée --------------------
    shutil.copy2("dim_indicateur.csv", f"dim_indicateur_avant_zeros_{marque}.csv")
    lignes_cat = list(csv.DictReader(open("dim_indicateur.csv", encoding="utf-8-sig")))
    for l in lignes_cat:
        if int(l["indicateur_id"]) in INDICATEURS and "registre exhaustif" not in l["definition"]:
            l["definition"] = f"{l['definition'].rstrip()} {PREUVE}"
    with open("dim_indicateur.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes_cat[0].keys()))
        w.writeheader()
        w.writerows(lignes_cat)
    print("[✔] Preuve d'exhaustivité inscrite dans les trois définitions")

    return verifier(attendus)


def verifier(attendus):
    print("\n--- vérification ---")
    cat = {int(l["indicateur_id"]): l
           for l in csv.DictReader(open("dim_indicateur.csv", encoding="utf-8-sig"))}
    ecarts = 0
    for ind in INDICATEURS:
        chemin = fichier_de_faits(cat[ind]["table_pg"])
        lignes = [l for l in csv.DictReader(open(chemin, encoding="utf-8-sig"))
                  if l.get("indicateur_id") == str(ind)]
        vus = [int(float(l["territoire_id"])) for l in lignes]
        doublons = len(vus) - len(set(vus))
        manquants = set(attendus) - set(vus)
        zeros = sum(1 for l in lignes if float(l["valeur"]) == 0)
        print(f"[{ind}] {len(set(vus))}/{len(attendus)} territoires · {zeros} à zéro · "
              f"{doublons} doublon(s)")
        if manquants or doublons:
            print(f"[!] {len(manquants)} manquant(s), {doublons} doublon(s)")
            ecarts += 1
    if ecarts:
        print("[!] Restaurer les sauvegardes.")
        return 1
    print("[✔] Les trois indicateurs couvrent tous les territoires servis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal("--appliquer" in sys.argv))
