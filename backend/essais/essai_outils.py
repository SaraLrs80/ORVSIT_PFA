"""
Essais des outils de l'assistant.

À lancer depuis le dossier `backend/`, environnement activé :

    python essai_outils.py

Pourquoi un fichier plutôt qu'une ligne de commande : les guillemets imbriqués
sont traités différemment par PowerShell, par cmd et par un terminal Unix, et
une commande qui marche sur l'un se coupe silencieusement sur l'autre. Un
fichier se comporte partout pareil — et il se relit, se complète et se rejoue.

Ce fichier grandira : chaque outil y ajoutera ses cas, et il deviendra le
premier étage du jeu d'évaluation prévu à l'étape 3.
"""

from app.assistant.outils import (
    cle, niveau_demande, resoudre_territoire, lister_indicateurs, decrire,
    lire_valeur, classer, comparer,
)
from app.database import SessionDWH

# (ce que l'utilisateur écrit, nom réduit attendu, niveau désigné attendu)
CAS = [
    ("Tétouan",                   "tetouan",         None),
    ("TETOUAN",                   "tetouan",         None),
    ("  Ouezzane  ",              "ouezzane",        None),
    ("Tanger-Assilah",            "tanger assilah",  None),

    # Le préfixe dit le niveau : c'est lui qui lève l'ambiguïté des homonymes
    ("la commune de Tanger",      "tanger",          "commune"),
    ("Commune d'Al Hoceima",      "al hoceima",      "commune"),
    ("Préfecture de Tanger",      "tanger",          "prefecture_province"),
    ("province de Chefchaouen",   "chefchaouen",     "prefecture_province"),
    ("Province Larache",          "larache",         "prefecture_province"),

    # L'apostrophe disparaît, et c'est sans conséquence : les noms de la base
    # passent par la même fonction, donc les deux côtés se correspondent.
    ("M’diq",                     "m diq",           None),
    ("M'diq-Fnideq",              "m diq fnideq",    None),
    ("Commune de M’diq",          "m diq",           "commune"),

    # Cas limites
    ("",                          "",                None),
    ("   ",                       "",                None),
]


# (saisie, action attendue, identifiants attendus dans l'ordre — ou None si on
#  ne veut vérifier que l'action)
CAS_TERRITOIRE = [
    # Sûr et unique : l'assistant peut répondre sans demander
    ("Tanger-Assilah",           "utiliser",  [2]),
    ("la commune de Tanger",     "utiliser",  [34]),
    ("Préfecture de Tanger",     "utiliser",  [2]),      # « probable », mais seul
    ("commune de Chefchaouen",   "utiliser",  [135]),
    ("province de Chefchaouen",  "utiliser",  [8]),
    ("Ksar el Kébir",            "utiliser",  None),

    # Ambigu : l'utilisateur n'a pas dit le niveau, il faut demander
    ("Tétouan",                  "demander",  [4, 51]),
    ("Al Hoceïma",               "demander",  None),
    ("Larache",                  "demander",  None),

    # Mal orthographié : proposé, jamais choisi seul
    ("Chefchawen",               "demander",  None),
    ("Tetuan",                   "demander",  None),

    # Introuvable : l'outil refuse, il ne rabat pas sur un voisin
    ("Marrakech",                "aucun",     []),
    ("",                         "aucun",     []),
]


def essais_cle():
    echecs = 0
    print(f"{'saisie':<28} {'nom réduit':<18} {'niveau':<20} verdict")
    print("-" * 82)
    for saisie, attendu_cle, attendu_niveau in CAS:
        obtenu_cle, obtenu_niveau = cle(saisie), niveau_demande(saisie)
        bon = obtenu_cle == attendu_cle and obtenu_niveau == attendu_niveau
        echecs += not bon
        print(f"{saisie!r:<28} {obtenu_cle!r:<18} {str(obtenu_niveau):<20} "
              f"{'ok' if bon else 'ÉCHEC'}")
        if not bon:
            print(f"{'':<28} attendu : {attendu_cle!r} / {attendu_niveau}")
    return echecs


def essais_territoire():
    echecs = 0
    dwh = SessionDWH()
    try:
        print(f"\n{'saisie':<28} {'action':<10} {'certitude':<10} candidats")
        print("-" * 96)
        for saisie, attendue, ids in CAS_TERRITOIRE:
            r = resoudre_territoire(dwh, saisie)
            obtenus = [c["territoire_id"] for c in r["candidats"]]
            bon = r["action"] == attendue and (ids is None or obtenus == ids)
            echecs += not bon
            noms = " · ".join(f"{c['territoire_id']} {c['nom']}" for c in r["candidats"])
            print(f"{saisie!r:<28} {r['action']:<10} {r['certitude']:<10} {noms or '—'}")
            if not bon:
                print(f"{'':<28} ATTENDU action={attendue} identifiants={ids}")
            # Le message part au modèle : on le lit pour vérifier qu'il dit
            # quoi faire, et pas seulement ce qui a été trouvé.
            print(f"{'':<28} {r['message']}")
    finally:
        dwh.close()
    return echecs


def essais_couverture():
    """Ce qui existe, et à quel niveau.

    Ce bloc est autant une vérification qu'une observation : c'est la première
    fois qu'on regarde la profondeur territoriale secteur par secteur, et c'est
    elle qui justifie — ou non — la sixième famille de questions.
    """
    echecs = 0
    dwh = SessionDWH()
    try:
        print("\nCouverture par niveau")
        print("-" * 96)
        for niveau in ("prefecture_province", "commune"):
            r = lister_indicateurs(dwh, niveau=niveau)
            print(f"  {niveau:<20} {r['nombre']:>3} indicateurs")
            for secteur, n in sorted(r.get("par_secteur", {}).items(),
                                     key=lambda x: -x[1]):
                print(f"      {secteur:<22} {n:>3}")

        print("\n  Écart entre les deux niveaux, par secteur :")
        prov = lister_indicateurs(dwh, niveau="prefecture_province").get("par_secteur", {})
        comm = lister_indicateurs(dwh, niveau="commune").get("par_secteur", {})
        for secteur in prov:
            p, c = prov.get(secteur, 0), comm.get(secteur, 0)
            perdu = p - c
            part = f"{100 * c / p:.0f} %" if p else "—"
            print(f"      {secteur:<22} {p:>3} -> {c:>3}   "
                  f"({perdu} de moins, {part} conservés)")

        print("\n  Listes détaillées et refus")
        print("-" * 96)
        cas = [
            ("santé au niveau commune",
             lambda: lister_indicateurs(dwh, secteur="santé", niveau="commune")),
            ("SANTE, graphie libre",
             lambda: lister_indicateurs(dwh, secteur="SANTE", niveau="commune")),
            ("motif « pauvre », province",
             lambda: lister_indicateurs(dwh, motif="pauvre")),
            ("secteur inconnu",
             lambda: lister_indicateurs(dwh, secteur="tourisme")),
            ("niveau inconnu",
             lambda: lister_indicateurs(dwh, niveau="douar")),
        ]
        for libelle, appel in cas:
            r = appel()
            apercu = ", ".join(i["libelle_court"] for i in r["indicateurs"][:3])
            print(f"  {libelle:<28} {r['nombre']:>3}  {apercu[:60]}")
            print(f"  {'':<28} {r['message']}")

        # Les deux graphies doivent donner le même résultat : c'est le modèle
        # qui écrit le nom du secteur, et il n'a pas la graphie exacte.
        a = lister_indicateurs(dwh, secteur="santé", niveau="commune")["nombre"]
        b = lister_indicateurs(dwh, secteur="SANTE", niveau="commune")["nombre"]
        if a != b:
            print(f"  ÉCHEC — « santé » rend {a} et « SANTE » rend {b}")
            echecs += 1
        # Un secteur ou un niveau inconnu doit refuser, jamais rendre au hasard.
        for mauvais in (lister_indicateurs(dwh, secteur="tourisme"),
                        lister_indicateurs(dwh, niveau="douar")):
            if mauvais["nombre"] != 0 or "inconnu" not in mauvais["message"]:
                print(f"  ÉCHEC — refus attendu, obtenu : {mauvais['message']}")
                echecs += 1
    finally:
        dwh.close()
    return echecs


# (identifiant, doit être trouvé, sens attendu ou None si on ne vérifie pas)
CAS_DECRIRE = [
    (496, True,  "bas_mieux"),   # MPI 2024, désormais aux deux niveaux
    (526, True,  "bas_mieux"),   # MPI 2014, le nouveau millésime
    (530, True,  "neutre"),      # contribution : ni bonne ni mauvaise
    (311, True,  "neutre"),      # Autoroutes : un effectif n'a pas de sens
    (113, True,  "bas_mieux"),   # Analphabétisme
     # Refus attendus
    (72,   False, None),         # masqué : existe en base, non publié
    (99999, False, None),        # inexistant
    ("abc", False, None),        # pas un identifiant
]


def essais_decrire():
    echecs = 0
    dwh = SessionDWH()
    try:
        print("\nDescription d'un indicateur")
        print("-" * 96)
        for identifiant, attendu, sens in CAS_DECRIRE:
            r = decrire(dwh, identifiant)
            bon = r["trouve"] == attendu
            if bon and attendu and sens:
                bon = r["sens"]["code"] == sens
            echecs += not bon
            if r["trouve"]:
                print(f"  [{identifiant}] {r['libelle'][:46]:<46} {r['unite'] or '—':<10} "
                      f"{r['millesime']}  {'ok' if bon else 'ÉCHEC'}")
                print(f"        couverture : {r['couverture']['phrase']}")
                print(f"        sens       : {r['sens']['lecture']}")
                print(f"        définition : {(r['definition'] or '')[:78]}")
                print(f"        traçabilité: {(r['tracabilite'] or '—')[:78]}")
            else:
                print(f"  [{identifiant}] refusé  {'ok' if bon else 'ÉCHEC'}")
                print(f"        {r['message']}")
    finally:
        dwh.close()
    return echecs


# (indicateur, territoire, absence attendue — None si la valeur doit être trouvée)
CAS_VALEUR = [
    # Trouvées
    (497, 8,   None),   # taux de pauvreté, province de Chefchaouen
    (497, 135, None),   # le même, commune de Chefchaouen
    (526, 8,   None),   # MPI millésime 2014, la donnée d'aujourd'hui
    (530, 8,   None),   # contribution au MPI — mortalité infantile
    (35,  8,   None),   # descendance finale : porte une ventilation par sexe

    # Un VRAI zéro : aucun établissement qualifiant privé à Chefchaouen.
    # L'outil doit le dire comme une valeur, jamais comme une absence.
    (521, 8,   None),

    # Première absence : l'indicateur n'existe pas à cette échelle
    (311, 135, "hors_niveau"),   # Autoroutes, demandé à une commune
    (410, 99,  "hors_niveau"),   # Habitants par ESSP, demandé à une commune

    # Refus
    (99999, 8,     "indicateur"),
    (497,   99999, "territoire"),
    ("abc", 8,     "identifiant"),
]


def essais_valeur():
    echecs = 0
    dwh = SessionDWH()
    try:
        print("\nLecture d'une valeur")
        print("-" * 96)
        for ind, terr, absence in CAS_VALEUR:
            r = lire_valeur(dwh, ind, terr)
            bon = r.get("absence") == absence and r["trouve"] == (absence is None)
            echecs += not bon
            tete = f"  [{ind} / {terr}]"
            if r["trouve"]:
                v = r["ventilation"]
                print(f"{tete:<16} {r['libelle'][:40]:<40} = {r['valeur']} "
                      f"{r['unite'] or ''}  {'ok' if bon else 'ÉCHEC'}")
                print(f"{'':<16} {r['territoire']} · millésime {r['millesime']}"
                      + (f" · ventilations {v['disponibles']}" if len(v['disponibles']) > 1
                         else ""))
            else:
                print(f"{tete:<16} absence = {r.get('absence')}  {'ok' if bon else 'ÉCHEC'}")
            print(f"{'':<16} {r['message']}")
    finally:
        dwh.close()
    return echecs


# (libellé, arguments, doit aboutir, premier attendu ou None)
CAS_CLASSER = [
    ("pauvreté, les 8 provinces",
     dict(indicateur_id=497), True, "Tanger-Assilah"),
    ("chômage, les 8 provinces",
     dict(indicateur_id=393), True, None),
    ("autoroutes — indicateur neutre",
     dict(indicateur_id=311), True, None),
    ("pauvreté, communes de Chefchaouen",
     dict(indicateur_id=497, niveau="commune", province_id=8), True, None),
    ("santé communale — des exclus attendus",
     dict(indicateur_id=523, niveau="commune", province_id=8), True, None),
    ("les 3 premières seulement",
     dict(indicateur_id=497, limite=3), True, "Tanger-Assilah"),

    # Refus
    ("commune sans province",
     dict(indicateur_id=497, niveau="commune"), False, None),
    ("autoroutes au niveau commune",
     dict(indicateur_id=311, niveau="commune", province_id=8), False, None),
    ("indicateur inexistant",
     dict(indicateur_id=99999), False, None),
    ("niveau inconnu",
     dict(indicateur_id=497, niveau="douar"), False, None),
]


def essais_classer():
    echecs = 0
    dwh = SessionDWH()
    try:
        print("\nClassement des territoires")
        print("-" * 96)
        for libelle, args, aboutit, premier in CAS_CLASSER:
            r = classer(dwh, **args)
            bon = r["trouve"] == aboutit
            if bon and aboutit and premier:
                bon = r["classement"][0]["nom"] == premier
            echecs += not bon
            print(f"  {libelle:<40} {'ok' if bon else 'ÉCHEC'}")
            if r["trouve"]:
                for e in r["classement"][:4]:
                    print(f"      {e['rang']}. {e['nom']:<28} {e['valeur_lisible']}")
                if len(r["classement"]) > 4:
                    print(f"      … {len(r['classement']) - 4} autres")
                if r["non_renseignes"]:
                    apercu = ", ".join(r["non_renseignes"][:3])
                    print(f"      écartés ({len(r['non_renseignes'])}) : {apercu}…")
            print(f"      {r['message']}")
    finally:
        dwh.close()
    return echecs


# (libellé, arguments, doit aboutir)
CAS_COMPARER = [
    ("Chefchaouen et Ouezzane sur la pauvreté",
     dict(indicateur_ids=[497, 496], territoire_ids=[8, 9]), True),
    ("quatre provinces, trois indicateurs",
     dict(indicateur_ids=[497, 393, 113], territoire_ids=[2, 4, 8, 9]), True),
    ("un indicateur neutre — aucun gagnant à désigner",
     dict(indicateur_ids=[311], territoire_ids=[2, 8]), True),
    ("deux communes d'une même province",
     dict(indicateur_ids=[497], territoire_ids=[135, 136]), True),
    ("indicateur non publié à ce niveau",
     dict(indicateur_ids=[311], territoire_ids=[135, 136]), True),

    # Refus
    ("une province et une commune",
     dict(indicateur_ids=[497], territoire_ids=[8, 135]), False),
    ("un seul territoire",
     dict(indicateur_ids=[497], territoire_ids=[8]), False),
    ("cinq territoires",
     dict(indicateur_ids=[497], territoire_ids=[2, 3, 4, 5, 6]), False),
    ("territoire inexistant",
     dict(indicateur_ids=[497], territoire_ids=[8, 99999]), False),
]


def essais_comparer():
    echecs = 0
    dwh = SessionDWH()
    try:
        print("\nComparaison de territoires")
        print("-" * 96)
        for libelle, args, aboutit in CAS_COMPARER:
            r = comparer(dwh, **args)
            bon = r["trouve"] == aboutit
            echecs += not bon
            print(f"  {libelle:<44} {'ok' if bon else 'ÉCHEC'}")
            if r["trouve"]:
                noms = " · ".join(t["nom"] for t in r["territoires"])
                print(f"      {noms}")
                for l in r["indicateurs"]:
                    cases = "  ".join(f"{c['valeur_lisible'] or '—':>16}" for c in l["cases"])
                    print(f"      {(l['libelle'] or '?')[:34]:<34} {cases}")
                    print(f"         {l['message']}")
            else:
                print(f"      {r['message']}")
    finally:
        dwh.close()
    return echecs


def principal():
    echecs = (essais_cle() + essais_territoire() + essais_couverture()
              + essais_decrire() + essais_valeur() + essais_classer()
              + essais_comparer())
    print("-" * 96)
    total = (len(CAS) + len(CAS_TERRITOIRE) + len(CAS_DECRIRE) + len(CAS_VALEUR)
             + len(CAS_CLASSER) + len(CAS_COMPARER))
    print(f"{echecs} cas sur {total} ne passent pas." if echecs
          else f"Les {total} cas passent.")
    return echecs


if __name__ == "__main__":
    raise SystemExit(1 if principal() else 0)
