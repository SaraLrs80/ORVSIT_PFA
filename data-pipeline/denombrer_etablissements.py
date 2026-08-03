# -*- coding: utf-8 -*-
"""Dénombre les établissements de santé recensés, par commune et par province.

Ce n'est pas un calcul : c'est un comptage de lignes d'un registre officiel,
exact et reproductible — de même nature que « Écoles publiques recensées ».

Règle de prudence sur le zéro :
  · si la province d'une commune figure dans le registre, une commune absente
    vaut 0 — le registre l'a bien parcourue et n'y a rien trouvé ;
  · si la province entière est absente du registre, ses communes restent
    NON RENSEIGNÉES. L'absence d'une province complète signale un export
    incomplet, pas une réalité de terrain.
"""
import pandas as pd

REG = {
 'etab_accouchement_nb': ('health_etablissements_accouchement',
   "Établissements avec module d'accouchement",
   "Nombre d'établissements de soins de santé primaires disposant d'un module d'accouchement, "
   "recensés par la Carte Sanitaire."),
 'etab_ump_nb': ('health_etablissements_ump',
   "Établissements avec unité UMP",
   "Nombre d'établissements disposant d'une unité médicale de proximité (UMP), "
   "recensés par la Carte Sanitaire."),
 'etab_ramed_nb': ('health_etablissements_ramed',
   "Établissements de rattachement RAMED",
   "Nombre d'établissements de rattachement au régime RAMED situés dans le territoire, "
   "recensés par la Carte Sanitaire."),
}

ter = pd.read_csv('dim_territoire.csv', encoding='utf-8-sig')
info = {int(r.territoire_id): r for _, r in ter.iterrows()}
def province(t):
    cur = t
    for _ in range(8):
        r = info.get(cur)
        if r is None: return None
        if r.niveau == 'prefecture_province': return int(r.territoire_id)
        if pd.isna(r.parent_id): return None
        cur = int(r.parent_id)
COMMUNES = [int(r.territoire_id) for _, r in ter.iterrows() if r.niveau == 'commune']
PROVINCES = [int(r.territoire_id) for _, r in ter.iterrows() if r.niveau == 'prefecture_province']
NOM_P = {int(r.territoire_id): r.nom for _, r in ter.iterrows() if r.niveau == 'prefecture_province'}

lignes, rapport = [], []
for cle, (table, lib, _) in REG.items():
    d = pd.read_csv('faits/health/%s.csv' % table, encoding='utf-8-sig')
    d['territoire_id'] = pd.to_numeric(d.territoire_id, errors='coerce')
    d = d.dropna(subset=['territoire_id'])
    d['territoire_id'] = d.territoire_id.astype(int)
    compte = d.groupby('territoire_id').size().to_dict()
    provs_vues = {province(t) for t in compte} - {None}
    for c in COMMUNES:
        p = province(c)
        if p not in provs_vues: continue          # province entière absente → non renseigné
        lignes.append({'territoire_id': c, 'indicateur': cle, 'valeur': compte.get(c, 0)})
    for p in PROVINCES:
        if p not in provs_vues: continue
        n = sum(v for t, v in compte.items() if province(t) == p)
        lignes.append({'territoire_id': p, 'indicateur': cle, 'valeur': n})
    absentes = [NOM_P[p] for p in PROVINCES if p not in provs_vues]
    rapport.append((lib, len(d), len(compte), len(provs_vues), absentes))

f = pd.DataFrame(lignes)
f.to_csv('faits/health/health_etablissements_denombrement.csv', index=False, encoding='utf-8-sig')

print('=== dénombrements produits ===')
for lib, n, nc, np_, ab in rapport:
    print('  %-44s %3d établissements · %3d territoires porteurs · %d/8 provinces' % (lib[:44], n, nc, np_))
    if ab: print('       provinces laissées NON RENSEIGNÉES : %s' % ', '.join(ab))
print()
print('  fichier : %d lignes' % len(f))
print(f.groupby('indicateur').agg(territoires=('valeur','size'), a_zero=('valeur', lambda s:(s==0).sum()),
                                  total=('valeur','sum')).to_string())
