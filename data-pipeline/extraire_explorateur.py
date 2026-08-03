# -*- coding: utf-8 -*-
"""Extrait, pour chaque indicateur affichable du catalogue, une valeur par
territoire. Les ventilations (sexe, milieu…) sont ramenées à leur modalité
d'ensemble : on n'agrège jamais, on choisit la ligne que la source publie
déjà comme total."""
import pandas as pd, json, glob, os

SECTEURS = ['Démographie', 'Emploi', 'Éducation', 'Santé', 'Conditions de vie']
STRUCT = {'territoire_id','indicateur','valeur','fk_territoire','theme','unite',
          'territoire','type_territoire','annee','source','code_geo','collectivite','cg','iso'}
TOTAUX = {'ensemble','total','les deux sexes','deux sexes','tous','national'}

cat = pd.read_csv('dim_indicateur.csv', encoding='utf-8-sig')
cat = cat[cat.secteur.isin(SECTEURS)]
ter = pd.read_csv('dim_territoire.csv', encoding='utf-8-sig')

info = {int(r.territoire_id): r for _, r in ter.iterrows()}
def province(tid):
    cur = tid
    for _ in range(8):
        r = info.get(cur)
        if r is None: return None
        if r.niveau == 'prefecture_province': return int(r.territoire_id)
        if pd.isna(r.parent_id): return None
        cur = int(r.parent_id)
    return None

GARDES = {int(r.territoire_id) for _, r in ter.iterrows()
          if r.niveau in ('region','prefecture_province','commune')}

fich = {os.path.basename(f)[:-4]: f for f in glob.glob('faits/*/*.csv') if '_archive' not in f}
def trouver(tp):
    if tp in fich: return fich[tp]
    for k, v in fich.items():
        if k.startswith(tp) or tp.startswith(k[:50]): return v

cache = {}
def lire(f):
    if f not in cache:
        cache[f] = pd.read_csv(f, encoding='utf-8-sig', low_memory=False)
    return cache[f]

def valeurs(r):
    """Renvoie {territoire_id: valeur} pour un indicateur, ventilations
    ramenées à l'ensemble."""
    f = trouver(r.table_pg)
    if f is None: return {}, []
    df = lire(f)
    if 'territoire_id' not in df.columns: return {}, []
    sub = df
    if r.mode_stockage == 'long' and isinstance(r.filtre_indicateur, str) and 'indicateur' in df.columns:
        sub = df[df['indicateur'].astype(str) == str(r.filtre_indicateur)]
        col = 'valeur'
    elif r.mode_stockage == 'large' and r.colonne_valeur in df.columns:
        col = r.colonne_valeur
    else:
        return {}, []
    # ventilations : une colonne est un axe si elle prend plusieurs valeurs
    # pour un même territoire
    axes = []
    for c in sub.columns:
        if c in STRUCT or c == col: continue
        if sub[c].dtype == object and sub.groupby('territoire_id')[c].nunique().max() > 1:
            axes.append(c)
    for c in axes:
        mods = sub[c].dropna().astype(str)
        tot = [m for m in mods.unique() if m.strip().lower() in TOTAUX]
        if tot: sub = sub[sub[c].astype(str) == tot[0]]
    sub = sub.dropna(subset=[col])
    out = {}
    for tid, g in sub.groupby('territoire_id'):
        tid = int(tid)
        if tid not in GARDES: continue
        out[tid] = round(float(g[col].iloc[0]), 4)
    return out, axes

ind, sans = [], []
for _, r in cat.iterrows():
    v, axes = valeurs(r)
    if not v: sans.append(r.libelle_court); continue
    niv = {info[t].niveau for t in v}
    ind.append({
        'id': int(r.indicateur_id), 'nom': r.libelle_court, 'unite': str(r.unite),
        'secteur': r.secteur, 'annee': str(r.annee), 'source': str(r.source)[:190],
        'def': ('' if pd.isna(r.definition) else str(r.definition).split('[Traçabilité')[0].strip())[:230],
        'axes': axes,
        'prov': 'prefecture_province' in niv, 'comm': 'commune' in niv,
        'v': {str(k): val for k, val in v.items()}
    })

terr = {}
for _, r in ter.iterrows():
    t = int(r.territoire_id)
    if t not in GARDES: continue
    terr[str(t)] = {'nom': r.nom, 'niveau': r.niveau, 'prov': province(t)}

json.dump({'indicateurs': ind, 'territoires': terr},
          open('/tmp/explorateur.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('%d indicateurs extraits · %d sans valeur' % (len(ind), len(sans)))
for s in sans[:8]: print('   sans valeur :', s)
print('province : %d · commune : %d' % (sum(i['prov'] for i in ind), sum(i['comm'] for i in ind)))
print('avec ventilation : %d' % sum(1 for i in ind if i['axes']))
print('taille : %.1f ko' % (os.path.getsize('/tmp/explorateur.json')/1024))
