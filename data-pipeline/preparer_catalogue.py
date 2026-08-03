# -*- coding: utf-8 -*-
"""
Prépare trois colonnes d'affichage pour le catalogue ORVSIT.
N'ajoute rien d'autre : aucune valeur de fait n'est touchée, aucune ligne
supprimée. Les colonnes existantes sont recopiées à l'identique.

  libelle_court : le titre affichable sur une carte d'indicateur
  secteur       : Démographie · Emploi · Éducation · Santé · Conditions de vie
  unite         : comblée uniquement quand le libellé ou la donnée la donnent

Règle de prudence : quand l'unité n'est pas déductible avec certitude,
elle reste vide. On préfère un blanc à une invention.
"""
import pandas as pd, re, sys

SRC = 'dim_indicateur.csv'
d = pd.read_csv(SRC, encoding='utf-8-sig')
cov = pd.read_csv('/tmp/couverture.csv')[['id', 'niveaux']]
d = d.merge(cov, left_on='indicateur_id', right_on='id', how='left').drop(columns=['id'])

# ------------------------------------------------------------------ libellés
# Écrits à la main là où le nom d'origine est un nom de colonne technique.
LIB = {
 # --- climat -------------------------------------------------------------
 1:"Humidité relative moyenne", 2:"Température maximale moyenne",
 3:"Température minimale moyenne", 4:"Température moyenne",
 # --- migration : durée de vie (table qui porte « natifs ») ---------------
 5:"Entrées migratoires (durée de vie)", 6:"Indice d'entrées migratoires (durée de vie)",
 7:"Indice de sorties migratoires (durée de vie)", 8:"Natifs du territoire",
 9:"Natifs résidant dans leur territoire de naissance", 10:"Population sédentaire",
 11:"Sorties migratoires (durée de vie)",
 # --- migration : 5 ans (table qui porte « residents_recents_5ans ») ------
 12:"Entrées migratoires (5 dernières années)", 13:"Indice d'entrées migratoires (5 ans)",
 14:"Indice de sorties migratoires (5 ans)", 15:"Résidents non migrants (5 ans)",
 16:"Population sédentaire de 5 ans et plus", 17:"Résidents installés depuis moins de 5 ans",
 18:"Sorties migratoires (5 dernières années)",
 # --- migration : 10 ans (table qui porte « residents_recents_10ans ») ----
 19:"Entrées migratoires (10 dernières années)", 20:"Indice d'entrées migratoires (10 ans)",
 21:"Indice de sorties migratoires (10 ans)", 22:"Résidents non migrants (10 ans)",
 23:"Population sédentaire (référence 10 ans)", 24:"Résidents installés depuis moins de 10 ans",
 25:"Sorties migratoires (10 dernières années)",
 26:"Migrants internationaux",
 # --- population ---------------------------------------------------------
 35:"Descendance finale des femmes", 37:"Population de 10 ans et plus",
 38:"Population de 15 ans et plus", 39:"Population de 7 à 12 ans",
 65:"Ménages (2014)", 66:"Ménages (2024)",
 67:"Population légale (2014)", 68:"Population légale (2024)",
 69:"Taux d'accroissement annuel des ménages", 70:"Taux d'accroissement annuel de la population",
 71:"Ménages (2025)",
 # --- éducation ----------------------------------------------------------
 112:"Population alphabète de 10 ans et plus",
 113:"Taux d'analphabétisme des 10 ans et plus", 114:"Taux d'analphabétisme des 15 ans et plus",
 116:"Collèges publics recensés", 117:"Écoles primaires publiques recensées",
 118:"Lycées publics recensés",
 119:"Collèges publics recensés (commune)", 120:"Écoles primaires publiques recensées (commune)",
 121:"Lycées publics recensés (commune)",
 486:"Privation — scolarisation des enfants", 487:"Privation — années de scolarité",
 # --- santé --------------------------------------------------------------
 430:"Privation — mortalité infantile", 431:"Privation — handicap",
 433:"Répertoire — équipements biomédicaux lourds",
 434:"Répertoire — établissements avec module d'accouchement",
 435:"Répertoire — établissements avec unité UMP",
 436:"Répertoire — établissements de rattachement RAMED",
 437:"Répertoire — personnel administratif",
 438:"Répertoire — personnel technique",
 439:"Répertoire — cliniques privées",
 440:"Répertoire — lits en cliniques privées",
 441:"Répertoire — lits hospitaliers par discipline",
 442:"Répertoire — autres infrastructures privées",
 443:"Répertoire — médecins du secteur privé",
 444:"Répertoire — médecins du secteur public",
 445:"Répertoire — personnel paramédical public",
 446:"Répertoire — salles de radiologie",
 447:"Répertoire — salles de bloc opératoire",
 448:"Répertoire — moyens de mobilité sanitaire",
 449:"Répertoire — établissements de santé par réseau",
 394:"Taux de prévalence du handicap",
 # --- infrastructure -----------------------------------------------------
 266:"Abonnés à l'électricité (ONEE)", 267:"Production d'électricité (ONEE)",
 268:"Ventes d'électricité aux abonnés", 269:"Ventes d'électricité aux régies et concessions",
 302:"Mouvements d'avions — total", 303:"Mouvements d'avions — trafic commercial",
 304:"Mouvements d'avions — trafic non commercial",
 311:"Autoroutes", 317:"Routes nationales", 318:"Routes provinciales", 319:"Routes régionales",
 313:"Part des autoroutes dans le réseau", 314:"Part des routes provinciales",
 315:"Réseau revêtu", 316:"Réseau routier total", 321:"Taux de revêtement du réseau",
 322:"Ventes d'électricité par distributeur (2022)",
 323:"Ventes d'électricité par distributeur (2023)",
 324:"Ventes d'électricité par distributeur (2024)",
 325:"Ventes d'électricité (2022)", 326:"Ventes d'électricité (2023)",
 327:"Ventes d'électricité (2024)",
 # --- socio-économique ---------------------------------------------------
 367:"Utilisation d'Internet (5 ans et plus)",
 368:"Ordinateur personnel (5 ans et plus)",
 369:"Téléphone mobile (5 ans et plus)",
 375:"Téléphone mobile (5 ans et plus, détail milieu)",
 370:"Ordinateur personnel (doublon du mode large)",
 371:"Utilisation d'Internet (doublon du mode large)",
 372:"Téléphone mobile (doublon du mode large)",
 489:"Privation — électricité", 490:"Privation — accès à l'eau",
 491:"Privation — assainissement", 492:"Privation — logement",
 493:"Privation — combustible de cuisson", 494:"Privation — communication",
}

PREFIXES = re.compile(
  r'^(Climat region tta|La base de donn es excel de la migration(?: \d)?|'
  r'Population rgph2024 population demogra|Population legale 2025 urba|'
  r'Etab scoalires mesures rgph2024 population educati|'
  r'Rgph2024 population socio econo rgph2024 popu|'
  r'Capital humain cleaned capital humain|Population rural|'
  r'Activit de l office national d electr|Mouvements des avions selon les a rop|'
  r'Dataset fracture numerique[a-z ]*|Table brute)\s*—\s*')

def nettoyer(nom):
    """Nettoyage conservateur : on retire le préfixe technique et les scories
    de mise en forme, on ne réécrit jamais le fond."""
    n = str(nom).strip()
    n = PREFIXES.sub('', n)
    n = n.replace(' (%) - ', ' — ').replace(' - ', ' — ')
    n = re.sub(r'\s+\(%\)$', '', n)
    n = re.sub(r'\s{2,}', ' ', n).strip()
    return n

def libelle(r):
    if r.indicateur_id in LIB: return LIB[r.indicateur_id]
    return nettoyer(r.nom_indicateur)

d['libelle_court'] = d.apply(libelle, axis=1)

# ------------------------------------------------------------------- unités
# Comblées seulement quand le libellé d'origine porte l'unité sans ambiguïté.
UNITE = {
 35:'enfants/femme', 71:'ménages',
 8:'hab', 9:'hab', 15:'hab', 17:'hab', 22:'hab', 24:'hab',
 302:'nombre', 303:'nombre', 304:'nombre',
 311:'km', 315:'km', 316:'km', 317:'km', 318:'km', 319:'km',
 # relevées sur la donnée elle-même, jamais devinées
 36:'enfants/femme',        # valeurs 1,02 à 4,50
 44:'ans',                  # valeurs 18,0 à 37,7
 450:'hab', 451:'ménages', 452:'pers./ménage', 453:'ménages',
 460:'pers./pièce',         # valeurs 1,4 à 1,6
 496:'indice',              # MPI, valeurs 0,009 à 0,167
 498:'%',                   # intensité A, valeurs 34,5 à 43,7
 500:'hab',                # effectif, 1 233 à 1 106 000
}
def unite(r):
    if r.indicateur_id in UNITE: return UNITE[r.indicateur_id]
    if pd.notna(r.unite) and str(r.unite).strip() not in ('', 'nan'): return r.unite
    n = str(r.nom_indicateur)
    if n.endswith('_km') or ' (Km)' in n: return 'km'
    if '(%)' in n or n.endswith('_pct') or 'Taux ' in n or 'Part ' in n: return '%'
    return ''                      # jamais deviné

d['unite'] = d.apply(unite, axis=1)

# ------------------------------------------------------------------ secteurs
# 370/371/372 reprennent au chiffre près 367/368/369 : vérifié sur les
# 8 provinces, écart nul. On les écarte de l'affichage sans les supprimer.
DOUBLONS = {370, 371, 372}

# Ratios reconstitués par le pipeline à partir des 4 longueurs publiées :
#   reseau_total_km   = somme des 4 catégories, écart 0,0 km sur les 8 provinces
#   taux_revetement   = 100 × revêtu/total, écart max 0,04 point
#   part_autoroute / part_routes_provinciales : mêmes divisions
#   reseau_revetu_km  = égal au total sur 6 provinces sur 8, la source ne
#                       recensant que le réseau classé et revêtu
# Retirés de l'affichage : le catalogue ne montre que du publié.
RATIOS_PIPELINE = {313, 314, 315, 316, 321}

def secteur(r):
    if r.indicateur_id in DOUBLONS: return 'doublon'
    if r.indicateur_id in RATIOS_PIPELINE: return 'calculé par le pipeline'
    if r.statut in ('calcule_observatoire', 'non_officiel'): return 'retiré'
    niv = str(r.niveaux) if pd.notna(r.niveaux) else ''
    if 'prefecture_province' not in niv and 'commune' not in niv: return 'non cartographiable'
    if r.statut == 'table_reference': return 'Santé — répertoires'
    t, n = str(r.table_pg), str(r.nom_indicateur)
    if r.theme == 'health':    return 'Santé'
    if r.theme == 'education': return 'Éducation'
    if r.theme == 'demography':return 'Démographie'
    if r.theme == 'climate':   return 'Conditions de vie'
    if r.theme == 'infrastructure':
        return 'Conditions de vie' if 'routes' in t else 'hors secteur'
    if 'rgph2024_population_socio_econo' in t:
        if 'Langues' in n:            return 'Démographie'
        if 'handicap' in n.lower():   return 'Santé'
        return 'Emploi'
    return 'Conditions de vie'

d['secteur'] = d.apply(secteur, axis=1)

# ------------------------------------------------------------------ millésime
d['annee'] = d['annee'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

d = d.drop(columns=['niveaux'])
d.to_csv('/tmp/dim_indicateur_prepare.csv', index=False, encoding='utf-8-sig')
print('écrit /tmp/dim_indicateur_prepare.csv —', len(d), 'lignes,', len(d.columns), 'colonnes')
