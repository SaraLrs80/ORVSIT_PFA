# -*- coding: utf-8 -*-
"""Extraction pour la fiche territoriale.
 · une valeur par territoire ET par modalité de ventilation (sexe, milieu)
 · les indicateurs sont regroupés en familles : ce qui suit « — » est une
   modalité, ce qui est entre parenthèses est une ventilation
 · la forme du graphique est décidée ici, sur la donnée, pas dans le navigateur
"""
import pandas as pd, json, glob, os, re

SECTEURS = ['Démographie','Emploi','Éducation','Santé','Conditions de vie']
STRUCT = {'territoire_id','indicateur','valeur','fk_territoire','theme','unite','territoire',
          'type_territoire','annee','source','code_geo','collectivite','cg','iso'}
TOT = {'ensemble','total','les deux sexes','deux sexes','tous','national'}

cat = pd.read_csv('dim_indicateur.csv', encoding='utf-8-sig')
cat = cat[cat.secteur.isin(SECTEURS)]
ter = pd.read_csv('dim_territoire.csv', encoding='utf-8-sig')
info = {int(r.territoire_id): r for _, r in ter.iterrows()}
def prov(t):
    cur = t
    for _ in range(8):
        r = info.get(cur)
        if r is None: return None
        if r.niveau == 'prefecture_province': return int(r.territoire_id)
        if pd.isna(r.parent_id): return None
        cur = int(r.parent_id)
GARDE = {int(r.territoire_id) for _, r in ter.iterrows()
         if r.niveau in ('region','prefecture_province','commune')}
fich = {os.path.basename(f)[:-4]: f for f in glob.glob('faits/*/*.csv') if '_archive' not in f}
def trv(tp):
    if tp in fich: return fich[tp]
    for k, v in fich.items():
        if k.startswith(tp) or tp.startswith(k[:50]): return v
cache = {}

def extraire(r):
    f = trv(r.table_pg)
    if f is None: return {}, None
    if f not in cache: cache[f] = pd.read_csv(f, encoding='utf-8-sig', low_memory=False)
    df = cache[f]
    if 'territoire_id' not in df.columns: return {}, None
    if r.mode_stockage == 'long' and isinstance(r.filtre_indicateur, str) and 'indicateur' in df.columns:
        sub = df[df['indicateur'].astype(str) == str(r.filtre_indicateur)]; col = 'valeur'
    elif r.mode_stockage == 'large' and r.colonne_valeur in df.columns:
        sub = df; col = r.colonne_valeur
    else: return {}, None
    axe = None
    for c in sub.columns:
        if c in STRUCT or c == col: continue
        if sub[c].dtype == object and sub.groupby('territoire_id')[c].nunique().max() > 1:
            axe = c; break
    sub = sub.dropna(subset=[col])
    out = {}
    if axe:
        for m, g in sub.groupby(axe):
            m = str(m); d = {}
            for t, gg in g.groupby('territoire_id'):
                t = int(t)
                if t in GARDE: d[str(t)] = round(float(gg[col].iloc[0]), 4)
            if d: out[m] = d
    else:
        d = {}
        for t, g in sub.groupby('territoire_id'):
            t = int(t)
            if t in GARDE: d[str(t)] = round(float(g[col].iloc[0]), 4)
        out['—'] = d
    return out, axe

def cle(nom, secteur):
    if ' — ' in nom: return (secteur, nom.split(' — ')[0].strip()), 'modalite', nom.split(' — ',1)[1].strip()
    m = re.match(r'^(.*?)\s*\(([^()]*)\)\s*$', nom)
    if m and len(m.group(2)) < 40: return (secteur, m.group(1).strip()), 'ventilation', m.group(2).strip()
    return (secteur, nom), 'seul', nom

ind = []
for _, r in cat.iterrows():
    mods, axe = extraire(r)
    if not mods: continue
    k, typ, etiq = cle(r.libelle_court, r.secteur)
    niv = {info[int(t)].niveau for d in mods.values() for t in d}
    ind.append({'id': int(r.indicateur_id), 'nom': r.libelle_court, 'unite': str(r.unite),
        'secteur': r.secteur, 'annee': str(r.annee), 'source': str(r.source)[:180],
        'def': ('' if pd.isna(r.definition) else str(r.definition).split('[Traçabilité')[0].strip())[:200],
        'fam': k[1], 'typ': typ, 'etiq': etiq, 'axe': axe or '',
        'prov': 'prefecture_province' in niv, 'comm': 'commune' in niv, 'm': mods})

# ---- forme du graphique, décidée sur la donnée ----
fam = {}
for i in ind: fam.setdefault((i['secteur'], i['fam']), []).append(i)
familles = []
for (s, f), l in fam.items():
    typ = l[0]['typ']
    somme = None
    if len(l) > 2 and all(x['unite'] == '%' for x in l) and typ == 'modalite':
        tot = {}
        for x in l:
            for t, v in (x['m'].get('Ensemble') or x['m'].get('—') or {}).items():
                tot[t] = tot.get(t, 0) + v
        if tot:
            mn, mx = min(tot.values()), max(tot.values())
            somme = (98 <= mn and mx <= 102)
    if len(l) == 1:                      forme = 'chiffre'
    elif f == 'Âge quinquennal':         forme = 'pyramide'
    elif somme:                          forme = 'anneau' if len(l) <= 3 else 'empile'
    elif typ == 'ventilation':           forme = 'groupe'
    else:                                forme = 'barres'
    familles.append({'secteur': s, 'nom': f, 'forme': forme, 'typ': typ,
        'unite': l[0]['unite'], 'annee': l[0]['annee'], 'source': l[0]['source'],
        'def': l[0]['def'], 'axe': l[0]['axe'],
        'prov': any(x['prov'] for x in l), 'comm': any(x['comm'] for x in l),
        'membres': [{'id': x['id'], 'etiq': x['etiq'], 'nom': x['nom'], 'unite': x['unite'],
                     'axe': x['axe'], 'm': x['m']} for x in l]})

terr = {str(int(r.territoire_id)): {'nom': r.nom, 'niveau': r.niveau, 'prov': prov(int(r.territoire_id))}
        for _, r in ter.iterrows() if int(r.territoire_id) in GARDE}
json.dump({'familles': familles, 'territoires': terr},
          open('/tmp/fiche.json','w'), ensure_ascii=False, separators=(',',':'))
from collections import Counter
c = Counter(f['forme'] for f in familles)
print('%d indicateurs → %d objets' % (len(ind), len(familles)))
print('formes :', dict(c))
print('taille : %.1f ko' % (os.path.getsize('/tmp/fiche.json')/1024))
for s in SECTEURS:
    l = [f for f in familles if f['secteur']==s]
    print('  %-18s %2d objets  (%s)' % (s, len(l),
        ', '.join('%s×%d'%(k,v) for k,v in Counter(x['forme'] for x in l).items())))
