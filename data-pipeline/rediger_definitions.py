"""
Rédiger les définitions manquantes des secteurs Démographie et Emploi.

POURQUOI
Sur les 234 indicateurs publiés, 75 seulement portaient une définition
réellement rédigée — mesuré en passant chaque ligne dans la fonction que
l'assistant utilise lui-même pour juger si une définition apporte quelque
chose. La Démographie en comptait zéro sur 65, l'Emploi zéro sur 13 : la
colonne contenait le nom de la colonne d'origine, parfois le thème, souvent
la note de provenance. L'assistant répondait donc « le catalogue ne comporte
pas de définition rédigée », ce qui est honnête mais inutile.

Après ce script : Démographie 58/65, Emploi 13/13, ensemble 146/234 (62 %).

CE QU'EST UNE BONNE DÉFINITION ICI
Elle dit ce que l'indicateur mesure, et surtout ce qu'il ne mesure pas quand
la confusion est probable. Cette règle vient d'une erreur : le libellé
« Établissements avec unité UMP » avait été lu comme « unités médicales de
proximité », et une phrase fausse en avait été tirée. La correction n'a pas
consisté à faire attention mais à écrire la mise en garde dans la définition
— puisque c'est elle que l'assistant lit.

CE QUI N'EST PAS RÉDIGÉ ICI
Trois notions — population sédentaire, résidents non migrants, résidents
récemment installés — soit sept lignes, dont je ne peux pas garantir le
périmètre exact sans le document de métadonnées du HCP que cite déjà leur
source. Elles restent sans définition et sont listées à la fin de l'essai à
blanc. Une définition inventée serait pire qu'une définition absente.

Usage :
    python rediger_definitions.py              essai à blanc
    python rediger_definitions.py --appliquer  écrit le CSV puis PostgreSQL
"""

import csv
import os
import shutil
import sys
import urllib.parse
from datetime import datetime

CATALOGUE = "dim_indicateur.csv"

# La traçabilité déjà présente est conservée : on n'écrit que le corps.
MARQUE = "[Traçabilité"

# --------------------------------------------------------------------------
# Les définitions, par identifiant.
# --------------------------------------------------------------------------
D = {}


def poser(ids, texte):
    for i in ids:
        D[i] = " ".join(texte.split())


# --- Démographie · effectifs de population --------------------------------
poser([40, 67], """
Effectif officiel de la population d'un territoire au recensement, seule
référence opposable pour les usages administratifs. Elle additionne la
population municipale et la population comptée à part, c'est-à-dire les
personnes rattachées au territoire mais résidant dans une collectivité :
casernes, internats, établissements de soins de longue durée.
Elle ne mesure pas le nombre de personnes présentes un jour donné : un recensement
compte les résidents habituels, non les présents.
""")

poser([41], """
Population résidant habituellement dans les ménages et les collectivités du
territoire, à l'exclusion des personnes comptées à part. C'est la composante
principale de la population légale, dont elle diffère de quelques milliers de
personnes à l'échelle régionale.
""")

poser([402], """
Population résidant dans les communes classées urbaines par le découpage
administratif en vigueur. Le caractère urbain relève d'un statut administratif
et non d'un seuil de densité ou de taille.
""")
poser([403], """
Population résidant dans les communes classées rurales par le découpage
administratif en vigueur.
""")
poser([404], """
Part de la population résidant en milieu urbain, rapportée à la population
totale du territoire. Il ne mesure pas l'étalement urbain ni la densité : une
commune entièrement rurale mais très peuplée reste à zéro.
""")

poser([37], "Effectif de la population âgée de 10 ans et plus. Sert de dénominateur aux indicateurs d'alphabétisation et de scolarisation.")
poser([38], "Effectif de la population âgée de 15 ans et plus. Sert de dénominateur aux indicateurs d'activité, de chômage et d'état matrimonial.")
poser([39], "Effectif de la population âgée de 7 à 12 ans, tranche correspondant à l'âge théorique de la scolarité primaire.")

poser([69], """
Rythme moyen d'évolution annuelle du nombre de ménages entre les deux derniers
recensements, exprimé en pourcentage. C'est une moyenne géométrique sur la
période, non la variation d'une année particulière.
""")
poser([70], """
Rythme moyen d'évolution annuelle de la population entre les deux derniers
recensements, exprimé en pourcentage. Une valeur négative signale une perte de
population. C'est une moyenne géométrique sur la période, non la variation
d'une année particulière, et elle ne distingue pas ce qui relève du solde
naturel de ce qui relève des migrations.
""")

poser([65, 71], """
Nombre de ménages du territoire. Un ménage réunit les personnes qui partagent
le même logement et le même budget, qu'elles soient apparentées ou non ; une
personne vivant seule constitue un ménage à elle seule.
""")

# --- Démographie · structure ----------------------------------------------
poser([42, 43], """
Répartition de la population par sexe, en pourcentage de l'effectif total du
territoire. Les deux parts se complètent à cent.
""")

poser(list(range(45, 61)), """
Répartition de la population par groupe d'âges de cinq ans, en pourcentage de
l'effectif total. L'ensemble des groupes se complète à cent, et leur profil
dessine la pyramide des âges du territoire.
""")

poser([61, 62, 63, 64], """
Répartition de la population âgée de 15 ans et plus selon la situation
matrimoniale déclarée au recensement — célibataire, marié, divorcé, veuf — en
pourcentage de cette population. Elle ne renseigne pas les unions non enregistrées ni
les séparations de fait.
""")

poser([44], """
Âge moyen au premier mariage, estimé à partir des proportions de célibataires
observées à chaque âge. Il s'agit d'une construction statistique portant sur
une génération fictive : ce n'est pas la moyenne des âges des personnes
mariées au cours de l'année.
""")

poser([36], """
Nombre moyen d'enfants qu'aurait une femme au terme de sa vie féconde si elle
connaissait, à chaque âge, les taux de fécondité observés l'année du
recensement. Indicateur du moment, portant sur une génération fictive : il
décrit une conjoncture, non la descendance réellement atteinte par une
génération de femmes.
""")
poser([35], """
Nombre moyen d'enfants effectivement mis au monde par les femmes ayant achevé
leur vie féconde. Contrairement à l'indicateur conjoncturel de fécondité,
celui-ci porte sur des générations réelles et se rapporte donc au passé.
""")

poser([376, 377, 378, 379, 380], """
Part de la population déclarant utiliser cette langue locale. Les réponses
sont non exclusives : une même personne peut en déclarer plusieurs, et la
somme des parts dépasse donc cent. Elles ne doivent jamais être additionnées
ni présentées comme une répartition.
""")

# --------------------------------------------------------------------------
# Démographie · migration
#
# Ce bloc suit le document de métadonnées du HCP (« Métadonnées et
# méthodologie de calcul des indicateurs relatifs à la migration », RGPH
# 2024), et chaque affirmation de dénominateur a été REVÉRIFIÉE sur les
# 179 territoires des trois classeurs source — voir verifier_migration.py.
#
# Ce que la vérification a établi, et qui ne se devinait pas :
#   · indice d'entrées   = entrées / population sédentaire        179/179
#   · indice de sorties  = sorties / natifs        (durée de vie) 178/179
#   · indice de sorties  = sorties / résidents il y a 5 ans       173/179
#   · indice de sorties  = sorties / résidents il y a 10 ans      179/179
#     -> les trois horizons n'ont donc PAS le même dénominateur de sortie.
#   · natifs = natifs résidant sur place + sorties                179/179
#   · la population sédentaire du classeur 5 ans exclut 8,18 % de la
#     population, celle du classeur 10 ans 17,75 % : exactement les parts
#     publiées des 0-4 ans (8,2 %) et des 0-9 ans (17,8 %). Ces colonnes
#     sont donc les populations de 5 ans et plus, et de 10 ans et plus.
# --------------------------------------------------------------------------
poser([10], """
Ensemble des personnes résidant dans le territoire au moment du recensement,
hors ménages nomades et sans-abri. C'est la population de référence de tous
les indicateurs de migration, et le dénominateur de l'indice d'entrées de
durée de vie.
""")
poser([16], """
Population sédentaire du territoire restreinte aux personnes de 5 ans et plus,
seules interrogées sur leur résidence cinq ans auparavant. Elle sert de
dénominateur à l'indice d'entrées des cinq dernières années.
""")
poser([23], """
Population sédentaire du territoire restreinte aux personnes de 10 ans et
plus, seules interrogées sur leur résidence dix ans auparavant. Elle sert de
dénominateur à l'indice d'entrées des dix dernières années.
""")

poser([5], """
Nombre de personnes résidant dans le territoire mais nées dans une autre zone
du pays. La migration « durée de vie » compare le lieu de naissance au lieu de
résidence au recensement, sans tenir compte des déplacements intermédiaires ni
des retours.
""")
poser([12], """
Nombre de personnes résidant dans le territoire au recensement et qui
résidaient dans une autre zone, au Maroc ou à l'étranger, cinq ans auparavant.
Ce sont les migrants récents.
""")
poser([19], """
Nombre de personnes résidant dans le territoire au recensement et qui
résidaient dans une autre zone, au Maroc ou à l'étranger, dix ans auparavant.
""")

poser([11], """
Nombre de personnes nées dans le territoire et résidant ailleurs, au Maroc ou
à l'étranger, au moment du recensement.
""")
poser([18], """
Nombre de personnes qui résidaient dans le territoire cinq ans avant le
recensement et vivaient ailleurs, au Maroc ou à l'étranger, au moment du
recensement.
""")
poser([25], """
Nombre de personnes qui résidaient dans le territoire dix ans avant le
recensement et vivaient ailleurs, au Maroc ou à l'étranger, au moment du
recensement.
""")

poser([6], """
Part des entrées de durée de vie dans la population sédentaire du territoire.
Attention : l'indice de sorties n'a pas le même dénominateur — il est rapporté
aux natifs du territoire. Les deux indices ne se soustraient pas et leur
différence ne constitue pas un solde migratoire.
""")
poser([13], """
Part des entrées des cinq dernières années dans la population sédentaire de
5 ans et plus du territoire. Attention : l'indice de sorties à cinq ans n'a
pas le même dénominateur — il est rapporté à la population qui résidait dans
le territoire cinq ans auparavant. Les deux indices ne se soustraient pas.
""")
poser([20], """
Part des entrées des dix dernières années dans la population sédentaire de
10 ans et plus du territoire. Attention : l'indice de sorties à dix ans n'a
pas le même dénominateur — il est rapporté à la population qui résidait dans
le territoire dix ans auparavant. Les deux indices ne se soustraient pas.
""")

poser([7], """
Part des sorties de durée de vie dans l'ensemble des natifs du territoire.
Attention : l'indice d'entrées n'a pas le même dénominateur — il est rapporté
à la population résidente. Les deux indices ne se soustraient pas et leur
différence ne constitue pas un solde migratoire.
""")
poser([14], """
Part des sorties des cinq dernières années dans la population qui résidait
dans le territoire cinq ans auparavant. Attention : l'indice d'entrées à cinq
ans n'a pas le même dénominateur — il est rapporté à la population sédentaire
de 5 ans et plus. Les deux indices ne se soustraient pas.
""")
poser([21], """
Part des sorties des dix dernières années dans la population qui résidait dans
le territoire dix ans auparavant. Attention : l'indice d'entrées à dix ans n'a
pas le même dénominateur — il est rapporté à la population sédentaire de
10 ans et plus. Les deux indices ne se soustraient pas.
""")

poser([8], """
Nombre de personnes nées dans le territoire, qu'elles y résident encore ou
non. Avec les sorties de durée de vie, les natifs résidant sur place en
composent l'ensemble.
""")
poser([9], """
Nombre de personnes résidant dans leur territoire de naissance. Ce sont les
non-migrants au sens de la durée de vie.
""")
poser([15], """
Nombre de personnes résidant dans le territoire au recensement et qui y
résidaient déjà cinq ans auparavant : les non-migrants récents.
""")
poser([22], """
Nombre de personnes résidant dans le territoire au recensement et qui y
résidaient déjà dix ans auparavant.
""")
poser([17], """
Effectif qui résidait dans le territoire cinq ans avant le recensement : les
non-migrants récents, auxquels s'ajoutent les personnes parties depuis. Sert
de dénominateur à l'indice de sorties des cinq dernières années.
""")
poser([24], """
Effectif qui résidait dans le territoire dix ans avant le recensement : les
non-migrants, auxquels s'ajoutent les personnes parties depuis. Sert de
dénominateur à l'indice de sorties des dix dernières années.
""")

poser([26], """
Nombre de personnes résidant dans le territoire au recensement et ayant déjà
résidé à l'étranger. Il ne renseigne pas la nationalité, et ne se limite pas
aux personnes nées à l'étranger : une personne née au Maroc, partie puis
revenue, y figure.
""")

# --------------------------------------------------------------------------
# Trois libellés à corriger, découverts en vérifiant les dénominateurs.
#
# « Résidents installés depuis moins de 5 ans » dit exactement l'inverse de ce
# que la colonne contient. Vérifié sur 178 des 179 territoires :
#       residents_recents_5ans = non-migrants récents + sorties
# c'est-à-dire l'effectif PRÉSENT cinq ans plus tôt, et non les arrivants.
# Le HCP nomme ce concept « Résidents récents », ce que le nettoyage a lu
# comme « récemment installés ». Un libellé faux est pire qu'un libellé
# absent : l'assistant l'énoncerait comme un fait.
# --------------------------------------------------------------------------
#
# Deux précautions de rédaction, mesurées et non supposées :
#   · pas le mot « territoire » dans un libellé. « Que signifie population
#     résidant dans le territoire 5 ans auparavant ? » était aiguillée vers
#     une demande de valeur, et l'assistant réclamait une commune.
#   · le chiffre plutôt que le mot. Avec « cinq » et « dix », la question sur
#     dix ans recevait la définition à cinq ans : la recherche retient les
#     chiffres comme racines, pas les nombres écrits en toutes lettres.
RENOMMER = {
    17: "Population résidente 5 ans auparavant",
    24: "Population résidente 10 ans auparavant",
    23: "Population sédentaire de 10 ans et plus",
}

# --- Emploi ----------------------------------------------------------------
poser([381], """
Population âgée de 15 ans et plus qui occupe un emploi ou en recherche un
activement. Elle réunit les actifs occupés et les chômeurs, et sert de
dénominateur au taux de chômage.
""")
poser([382], """
Population âgée de 15 ans et plus exerçant une activité rémunérée ou une aide
familiale, même à temps partiel ou de façon occasionnelle.
""")
poser([383], """
Population âgée de 15 ans et plus n'occupant pas d'emploi et n'en recherchant
pas : élèves et étudiants, personnes au foyer, retraités, personnes
empêchées. Elle ne doit pas être confondue avec les chômeurs, qui sont comptés
parmi les actifs.
""")
poser([392], """
Part de la population âgée de 15 ans et plus qui est active — occupée ou au
chômage — rapportée à l'ensemble de cette population. Un taux d'activité bas
traduit une forte inactivité, non un fort chômage.
""")
poser([393], """
Part des chômeurs dans la population active de 15 ans et plus. Le dénominateur
est la population active et non la population totale : un territoire où peu de
personnes se déclarent actives peut afficher un taux de chômage modéré tout en
comptant peu d'emplois. À lire avec le taux d'activité.
""")
poser([384, 385, 386, 387, 388, 389, 390, 391], """
Répartition des actifs occupés de 15 ans et plus selon leur statut dans
l'emploi — employeur, indépendant, salarié du secteur public ou privé,
coopérateur, aide familiale, apprenti, autre — en pourcentage des actifs
occupés. Elle ne renseigne pas sur le secteur d'activité ni sur le niveau de
rémunération.
""")

# --------------------------------------------------------------------------
# Ce qui reste sans définition. Plus rien : le document de métadonnées du HCP
# et la vérification arithmétique sur les trois classeurs ont levé les sept
# réserves qui subsistaient.
# --------------------------------------------------------------------------
A_VERIFIER = {}


def moteur():
    # Importé ici et non en tête : l'essai à blanc ne touche pas la base et
    # doit pouvoir tourner sans connexion ni pilote installé.
    from dotenv import load_dotenv
    from sqlalchemy import create_engine
    load_dotenv()
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


def nouvelle_definition(ligne, texte):
    """Le corps est remplacé ; la traçabilité déjà écrite est conservée."""
    ancienne = ligne["definition"] or ""
    tracabilite = ""
    if MARQUE in ancienne:
        tracabilite = " " + ancienne[ancienne.index(MARQUE):]
    return (texte + tracabilite).strip()


def publies(lignes):
    """Les lignes réellement servies par l'application.

    Trois lignes de Démographie sont en base sans être publiées — un doublon
    de la population légale et deux millésimes 2024 déjà portés par un
    indicateur à couverture communale. Elles portent chacune une note qui
    explique pourquoi elles sont masquées : y écrire une définition
    effacerait cette note pour rien.
    """
    return [l for l in lignes
            if l["statut"] in ("actif", "validé")
            and "True" in (l["dispo_province"], l["dispo_commune"])]


def controler(lignes):
    problemes = []
    attendus = {int(l["indicateur_id"]) for l in publies(lignes)
                if l["secteur"] in ("Démographie", "Emploi")}
    traites = set(D) | set(A_VERIFIER)

    oublies = sorted(attendus - traites)
    if oublies:
        problemes.append(f"indicateur(s) publié(s) non traité(s) : {oublies}")

    intrus = sorted(traites - attendus)
    if intrus:
        problemes.append(
            f"indicateur(s) visé(s) hors périmètre publié Démographie/Emploi "
            f"— non publié, autre secteur, ou identifiant inexistant : {intrus}")

    doubles = sorted(set(D) & set(A_VERIFIER))
    if doubles:
        problemes.append(f"à la fois rédigé et signalé à vérifier : {doubles}")

    return problemes


def essai_a_blanc(lignes):
    par_id = {int(l["indicateur_id"]): l for l in lignes}
    print(f"[i] {len(D)} définitions à écrire, "
          f"{len(A_VERIFIER)} laissées de côté "
          f"({len(D) + len(A_VERIFIER)} indicateurs publiés en Démographie "
          f"et Emploi)\n")

    groupes = {}
    for ind, texte in D.items():
        groupes.setdefault(texte, []).append(ind)

    for texte, inds in groupes.items():
        libelles = [par_id[i]["libelle_court"] for i in inds]
        titre = libelles[0] if len(inds) == 1 else \
            f"{libelles[0]}  … et {len(inds) - 1} autre(s)"
        print(f"    [{len(inds):>2}] {titre[:70]}")
        print(f"         {texte[:190]}\n")

    sans_tracabilite = [i for i in D if MARQUE not in (par_id[i]["definition"] or "")]
    print(f"[i] traçabilité existante conservée pour "
          f"{len(D) - len(sans_tracabilite)} lignes ; "
          f"{len(sans_tracabilite)} n'en portaient pas : {sans_tracabilite}")

    print("\n--- libellés corrigés ---")
    for ind, libelle in RENOMMER.items():
        print(f"    {ind:>4}  {par_id[ind]['libelle_court']}")
        print(f"          ->  {libelle}")

    if A_VERIFIER:
        print("\n--- laissées sans définition, faute de source sûre ---")
        for ind, motif in A_VERIFIER.items():
            print(f"    {ind:>4}  {par_id[ind]['libelle_court'][:42]:<42} {motif}")
    else:
        print("\n[i] Aucune ligne laissée sans définition.")
    print("\n[·] Essai à blanc — rien n'a été écrit.")


def ecrire_csv(lignes, colonnes, marque):
    sauvegarde = f"dim_indicateur_avant_definitions_{marque}.csv"
    # Deux exécutions dans la même seconde porteraient le même nom : la
    # seconde écraserait la sauvegarde d'origine, la seule qui vaille.
    suffixe = 1
    while os.path.exists(sauvegarde):
        suffixe += 1
        sauvegarde = f"dim_indicateur_avant_definitions_{marque}_{suffixe}.csv"
    shutil.copy2(CATALOGUE, sauvegarde)
    par_id = {int(l["indicateur_id"]): l for l in lignes}
    for ind, texte in D.items():
        par_id[ind]["definition"] = nouvelle_definition(par_id[ind], texte)
    for ind, libelle in RENOMMER.items():
        par_id[ind]["libelle_court"] = libelle
    with open(CATALOGUE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colonnes)
        w.writeheader()
        w.writerows(lignes)
    print(f"[✔] CSV écrit  (sauvegarde : {sauvegarde})")
    return sauvegarde


def a_changer(lignes):
    """Les lignes dont le texte final diffère de ce qui est déjà écrit.

    Le script doit pouvoir être relancé : si le CSV est déjà à jour et que
    seule la base reste à mettre à jour, la vérification ne doit pas exiger
    78 lignes modifiées mais zéro.
    """
    par_id = {int(l["indicateur_id"]): l for l in lignes}
    return {i for i, t in D.items()
            if par_id[i]["definition"] != nouvelle_definition(par_id[i], t)}


def verifier_csv(sauvegarde, colonnes, attendues):
    avant, _ = lire(sauvegarde)
    apres, _ = lire(CATALOGUE)
    if len(avant) != len(apres):
        print(f"[!] nombre de lignes : {len(avant)} -> {len(apres)}")
        return False
    modifiees, renommees, parasites, tracabilite_perdue = set(), set(), [], []
    for a, b in zip(avant, apres):
        for col in colonnes:
            if a[col] == b[col]:
                continue
            if col == "definition":
                modifiees.add(int(b["indicateur_id"]))
                if MARQUE in a[col] and MARQUE not in b[col]:
                    tracabilite_perdue.append(b["indicateur_id"])
            elif col == "libelle_court":
                renommees.add(int(b["indicateur_id"]))
            else:
                parasites.append((b["indicateur_id"], col))
    print("\n--- vérification du CSV ---")
    print(f"    lignes                  : {len(apres)} (inchangé)")
    print(f"    colonnes modifiées      : "
          f"{'definition et libelle_court' if not parasites else 'AUTRES !'}")
    print(f"    définitions réécrites   : {len(modifiees)}")
    print(f"    libellés corrigés       : {sorted(renommees)}")
    print(f"    traçabilités conservées : "
          f"{'toutes' if not tracabilite_perdue else 'PERDUES : ' + str(tracabilite_perdue)}")
    if parasites or tracabilite_perdue:
        return False
    if not renommees <= set(RENOMMER):
        print(f"[!] libellé modifié hors des trois prévus : "
              f"{sorted(renommees - set(RENOMMER))}")
        return False
    if modifiees != attendues:
        print(f"[!] attendues : {sorted(attendues)}")
        print(f"    obtenues  : {sorted(modifiees)}")
        return False
    print("[✔] Aucune modification non voulue.")
    return True


def ecrire_postgres(lignes):
    from sqlalchemy import text
    par_id = {int(l["indicateur_id"]): l for l in lignes}
    e = moteur()
    with e.begin() as conn:
        for ind in D:
            conn.execute(text(
                "UPDATE referential.dim_indicateur SET definition = :d "
                "WHERE indicateur_id = :i"),
                {"d": par_id[ind]["definition"], "i": ind})
        for ind, libelle in RENOMMER.items():
            conn.execute(text(
                "UPDATE referential.dim_indicateur SET libelle_court = :l "
                "WHERE indicateur_id = :i"), {"l": libelle, "i": ind})
    # On ne compte pas : on relit et on compare caractère par caractère.
    with e.connect() as conn:
        en_base = {i: (d, l) for i, d, l in conn.execute(text(
            "SELECT indicateur_id, definition, libelle_court "
            "FROM referential.dim_indicateur "
            "WHERE indicateur_id = ANY(:ids)"), {"ids": list(D)}).all()}
    ecarts = [i for i in D
              if en_base.get(i, (None, None))[0] != par_id[i]["definition"]]
    mal_nommes = [i for i in RENOMMER if en_base.get(i, (None, None))[1] != RENOMMER[i]]
    print("\n--- vérification de PostgreSQL ---")
    print(f"    lignes relues            : {len(en_base)}/{len(D)}")
    print(f"    écarts de définition     : {len(ecarts)}"
          + (f"  -> {ecarts}" if ecarts else ""))
    print(f"    écarts de libellé        : {len(mal_nommes)}"
          + (f"  -> {mal_nommes}" if mal_nommes else ""))
    if ecarts or mal_nommes or len(en_base) != len(D):
        print("[!] La base et le catalogue ne disent pas la même chose.")
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

    attendues = a_changer(lignes)
    if not attendues:
        print(f"[i] Le catalogue porte déjà ces {len(D)} définitions ; "
              "seule la base reste à mettre à jour.")
    marque = datetime.now().strftime("%Y%m%d_%H%M%S")
    sauvegarde = ecrire_csv(lignes, colonnes, marque)
    if not verifier_csv(sauvegarde, colonnes, attendues):
        print(f"\n[!] Restaurer avec :  copy {sauvegarde} {CATALOGUE}")
        return 1
    lignes, _ = lire(CATALOGUE)
    if not ecrire_postgres(lignes):
        return 1
    print(f"\n[✔] {len(D)} définitions en place "
          f"({len(attendues)} réécrites lors de cette exécution), "
          f"{len(RENOMMER)} libellés corrigés.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal("--appliquer" in sys.argv))
