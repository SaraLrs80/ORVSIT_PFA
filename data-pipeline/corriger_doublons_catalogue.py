"""
Correction stricte des DOUBLONS inter-thèmes du catalogue dim_indicateur.

Constat (vérifié par couverture territoriale) : certains indicateurs existent
en double dans deux thèmes. On garde à chaque fois la version COMPLÈTE
(8/8 provinces, 146/146 communes) et on retire la version VIDE / éparse.

  - Scolarisation 6-11 :
        GARDÉ  id115  (education)               8/8 · 146/146   [utilisé par l'IDT]
        RETIRÉ id339  (socio_economic)          0/8 · 0/146     (vide)
  - Handicap (prévalence) :
        GARDÉ  id394  (socio_economic)          8/8 · 146/146
        RETIRÉ id31   (demography)              0/8 · 0/146     (vide)
        (id32 « handicap par groupes d'âges » est un AUTRE indicateur -> conservé)
  - Internet / Ordinateur (5 ans et +) :
        GARDÉ  id367/id368 (fracture_numerique) 8/8            [utilisés par l'IDT]
        RETIRÉ id373/id374 (detail_milieu)      2/8 et 4/8     (épars)

⚠️  NON DESTRUCTIF pour les données : on ne touche qu'au CATALOGUE
    (dim_indicateur.csv). Les fichiers de faits restent intacts ; le pipeline et
    l'IDT (qui n'utilisent que les id canoniques) ne sont pas affectés.

Idempotent. Lancer :  python corriger_doublons_catalogue.py
"""

import os
import pandas as pd

FICHIER = "dim_indicateur.csv"
# id des DOUBLONS à retirer (versions vides/éparses ; les canoniques sont gardés)
A_RETIRER = {339, 31, 373, 374}

ind = pd.read_csv(FICHIER, encoding="utf-8-sig")

presents = A_RETIRER & set(ind["indicateur_id"])
if not presents:
    print("[i] Aucun doublon à retirer (déjà corrigé). Rien à faire.")
    raise SystemExit(0)

# Sauvegarde (une seule fois)
if not os.path.exists("dim_indicateur_avant_dedoublonnage.csv"):
    ind.to_csv("dim_indicateur_avant_dedoublonnage.csv", index=False, encoding="utf-8-sig")
    print("[✔] Sauvegarde : dim_indicateur_avant_dedoublonnage.csv")

avant = len(ind)
retires = ind[ind["indicateur_id"].isin(A_RETIRER)][["indicateur_id", "nom_indicateur", "theme"]]
ind = ind[~ind["indicateur_id"].isin(A_RETIRER)].copy()
ind.to_csv(FICHIER, index=False, encoding="utf-8-sig")

print(f"[✔] {FICHIER} : {avant} -> {len(ind)} indicateurs ({len(retires)} doublon(s) retiré(s))")
for _, r in retires.iterrows():
    print(f"    - id{r.indicateur_id}  {str(r.nom_indicateur)[:50]}  ({r.theme})")

# Contrôle : noms toujours uniques, aucune des tables n'a disparu
print(f"[✔] Noms uniques : {ind['nom_indicateur'].nunique()}/{len(ind)}")
print("[i] Les fichiers de faits ne sont PAS modifiés (données intactes).")
