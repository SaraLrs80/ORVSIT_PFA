"""
Passage du rapport en version 6.

Le script part toujours de la version 5 et refabrique la version 6 : il est
donc rejouable, et une capture remplacée n'oblige qu'à le relancer.

CE QU'IL FAIT
  · 2.7.2  liste des écrans mise en accord avec la solution livrée
  · 3.6.1  vérification du sens des indicateurs de migration (section neuve)
  · 3.8.8  la vue d'ensemble, décrite telle qu'elle est livrée
  · 4.1    la première règle de fond, et la règle d'aiguillage du territoire
  · 4.4    diagramme de séquence
  · 4.5    les mécanismes de la recherche
  · 4.6    la rédaction contrôlée
  · 4.8    l'interface de l'assistant (section neuve), 4.9 et 4.10 renumérotées

RÈGLE D'ÉCRITURE TENUE PARTOUT
Le rapport décrit la solution livrée et justifie ses choix ; il ne raconte pas
les états antérieurs du travail. Les corrections et améliorations se
rapportent en 3.9, qui leur est consacrée. Les textes réécrits sont dans
redaction.py.

L'interface de l'assistant est placée au chapitre 4 et non au chapitre 3 : le
chapitre 3 décrit les écrans du tableau de bord, où l'assistant n'est pas
encore introduit. Le lecteur y rencontrerait les copies d'écran avant le
principe.

    python ajouts_v6.py              essai à blanc
    python ajouts_v6.py --appliquer
"""

import os
import shutil
import sys
import zipfile

import chapitre5 as C5
import edition as E
import liminaires as L
import redaction as R

RACINE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.abspath(os.path.join(RACINE, "..", ".."))
SOURCE = os.path.join(STAGE, "rapport_stage1_v5.docx")
SORTIE = os.path.join(STAGE, "rapport_stage1_v6.docx")
CAPTURES = os.path.join(STAGE, "captures")
TRAVAIL = os.path.join(RACINE, "_travail")


def transformer(dossier, xml):
    etapes = []

    def etape(nom, avant):
        etapes.append((nom, len(xml) - len(avant)))

    a = xml
    xml = E.remplacer_section(xml, "2.7.2",
                              R.section_ecrans(E.figures_de(xml, "2.7.2"),
                                               E.numerotation_de(xml, "2.7.2")))
    etape("2.7.2 écrans conçus", a)

    a = xml
    xml = E.inserer_apres_section(xml, "3.6 Vérification", R.section_migration())
    etape("3.6.1 sens des indicateurs", a)

    a = xml
    xml = E.remplacer_section(xml, "3.8.8", R.section_vue_ensemble(
        dossier, os.path.join(CAPTURES, "ui_vue_ensemble.png")))
    etape("3.8.8 vue d'ensemble", a)

    a = xml
    xml = E.remplacer_paragraphe(xml, "L'API compte", E.para(R.PHRASE_MODULES))
    xml = E.remplacer_lignes(xml, "fiche-nouvelle", R.MODULES, depuis_la_ligne=1)
    etape("3.7.1 modules de l'API", a)

    a = xml
    xml = xml.replace("394 indicateurs", R.VOLUME_CATALOGUE)
    etape("2.6.1 volume du catalogue", a)

    a = xml
    for ancien, nouveau in R.COMMUNES:
        xml = xml.replace(ancien, nouveau)
    xml = xml.replace(">147<", ">146<")
    etape("1.1 nombre de communes", a)

    a = xml
    xml = E.remplacer_section(xml, "3.9.2", [])
    xml = E.remplacer_section(xml, "3.9.1", R.section_regles_de_travail())
    etape("3.9.1 sans redite du tableau", a)

    # --- chapitre 4 : les passages narratifs ------------------------------
    a = xml
    xml = E.remplacer_paragraphe(xml, "La première est que l'assistant",
                                 E.para(R.REGLE_UNE))
    xml = E.remplacer_paragraphe(xml, "La troisième est que la comparaison",
                                 [E.para("La troisième est que la comparaison ne "
                                         "se fait qu'entre territoires de même "
                                         "niveau. Comparer une commune à une "
                                         "province mesurerait une différence de "
                                         "taille et non une disparité."),
                                  E.para(R.REGLE_TERRITOIRE)])
    etape("4.1 règles de fond", a)

    a = xml
    xml = E.supprimer_paragraphe(xml, "Une première version exigeait un territoire")
    etape("4.1 passage narratif retiré", a)

    a = xml
    xml = E.remplacer_paragraphe(xml, "La deuxième ligne du tableau",
        E.para("La deuxième ligne du tableau est la mesure la plus importante "
               "du projet. " + R.MESURE_CATALOGUE))
    xml = E.remplacer_paragraphe(xml, "Cette mesure a orienté", E.para(R.ORIENTATION))
    etape("4.3 décomptes du catalogue", a)

    a = xml
    xml = E.remplacer_paragraphe(xml, "Elle opère sur les FAMILLES", E.para(R.FAMILLES))
    xml = E.remplacer_lignes(xml, "Qualité des définitions",
                             [R.LIMITE_DEFINITIONS], depuis_la_ligne=4)
    etape("4.5 et 4.9 chiffres du catalogue", a)

    a = xml
    xml = E.inserer_apres_section(xml, "4.4 Architecture", R.diagramme(
        dossier, os.path.join(CAPTURES, "sequence_assistant.png")))
    etape("4.4 diagramme de séquence", a)

    a = xml
    xml = E.remplacer_paragraphe(xml, "Trois mécanismes ont été ajoutés",
                                 E.para(R.MECANISMES))
    xml = E.remplacer_paragraphe(xml, "Ce principe a été appliqué quatre fois",
                                 E.para(R.PRINCIPE))
    etape("4.5 recherche", a)

    a = xml
    xml = E.remplacer_paragraphe(xml, "La dernière étape confie au modèle",
                                 E.para(R.RISQUE))
    xml = E.remplacer_paragraphe(xml, "Une première version transmettait",
                                 E.para(R.MESURE_UNE))
    xml = E.remplacer_paragraphe(xml, "Une seconde version, plus contrainte",
                                 E.para(R.MESURE_DEUX))
    xml = E.remplacer_paragraphe(xml, "La conception retenue renverse",
                                 E.para(R.CONCEPTION))
    etape("4.6 rédaction contrôlée", a)

    # La renumérotation précède l'insertion : sinon deux titres
    # commenceraient par « 4.8 » et la recherche deviendrait ambiguë.
    a = xml
    xml = E.renommer_titre(xml, "4.9 Ce que", "4.10 Ce que l'assistant garantit")
    xml = E.renommer_titre(xml, "4.8 Limites", "4.9 Limites connues")
    etape("4.9 et 4.10 renumérotées", a)

    a = xml
    xml = E.inserer_avant_titre(xml, "4.9 Limites",
                                R.section_interface(dossier, CAPTURES))
    etape("4.8 interface de l'assistant", a)

    # Le chapitre 5 se place après le chapitre 4, donc en fin de corps.
    a = xml
    xml = E.inserer_apres_section(
        xml, "4.10 Ce que", C5.chapitre(dossier, CAPTURES,
                                        E.numerotation_de(xml, "2.7.2")))
    etape("chapitre 5 — Tests et validation", a)

    # Les pages liminaires en tête, la conclusion et la bibliographie en fin.
    a = xml
    num = E.numerotation_de(xml, "2.7.2")
    debut = xml.index("<w:body>") + len("<w:body>")
    xml = xml[:debut] + "".join(L.avant(num)) + xml[debut:]
    etape("pages liminaires", a)

    a = xml
    fin = xml.rindex("<w:sectPr")
    fin = xml.rindex("</w:p>", 0, fin) + len("</w:p>")
    xml = xml[:fin] + "".join(L.apres(num)) + xml[fin:]
    etape("conclusion et bibliographie", a)

    # En dernier : Word garde en mémoire la dernière valeur calculée d'un
    # champ SEQ. Sans cette passe, toute légende ajoutée afficherait « 0 »
    # jusqu'à ce que le lecteur mette les champs à jour lui-même.
    a = xml
    xml, series = E.renumeroter(xml)
    etapes.append((f"renumérotation ({series['Figure']} figures, "
                   f"{series['Tableau']} tableaux)", len(xml) - len(a)))

    return xml, etapes


NARRATION = [
    "première version", "version initiale", "au départ", "a été abandonné",
    "abandonnée", "au moment de la rédaction", "en cours de reconstruction",
    "Une seconde version", "à mesure que les essais", "initialement",
]


def controler_narration(xml):
    """Aucun passage narratif ne doit subsister hors de la section 3.9.

    La section 3.9 est consacrée aux difficultés et aux corrections : c'est
    le seul endroit du rapport où un état antérieur a sa place.
    """
    ps = E.paragraphes(xml)
    i, _ = E.trouver_titre(xml, "3.9 Difficultés")
    j = E.fin_de_section(ps, i)
    restes = []
    for k, (_, _, texte, _) in enumerate(ps):
        if i <= k < j:
            continue
        for mot in NARRATION:
            if mot.lower() in texte.lower():
                restes.append((k, mot, texte[:110]))
    return restes


def ouvrir(source, dossier):
    """Décompresse le document dans un dossier de travail.

    On emploie le module zipfile plutôt que les commandes unzip et zip :
    celles-ci n'existent pas sous Windows, où le script doit tourner.
    """
    if os.path.exists(dossier):
        shutil.rmtree(dossier)
    os.makedirs(dossier)
    with zipfile.ZipFile(source) as archive:
        archive.extractall(dossier)


def refermer(dossier, sortie):
    """Reconstitue le .docx à partir du dossier de travail.

    L'ordre des entrées compte : [Content_Types].xml doit venir en premier,
    faute de quoi certains lecteurs refusent le document.
    """
    fichiers = []
    for racine, _, noms in os.walk(dossier):
        for nom in noms:
            chemin = os.path.join(racine, nom)
            fichiers.append((chemin,
                             os.path.relpath(chemin, dossier).replace("\\", "/")))
    fichiers.sort(key=lambda f: (f[1] != "[Content_Types].xml", f[1]))

    with zipfile.ZipFile(sortie, "w", zipfile.ZIP_DEFLATED) as archive:
        for chemin, interne in fichiers:
            archive.write(chemin, interne)


def principal(appliquer):
    ouvrir(SOURCE, TRAVAIL)

    chemin = os.path.join(TRAVAIL, "word", "document.xml")
    xml = open(chemin, encoding="utf-8").read()
    avant = E.paragraphes(xml)

    xml, etapes = transformer(TRAVAIL, xml)
    apres = E.paragraphes(xml)

    print(f"paragraphes : {len(avant)} -> {len(apres)}\n")
    for nom, delta in etapes:
        print(f"   {nom:<32} {delta:+7d} caractères")

    manquantes = [n for n, _ in R.FIGURES_ASSISTANT
                  if not os.path.exists(os.path.join(CAPTURES, n))]
    manquantes += [n for n in ("ui_vue_ensemble.png", "sequence_assistant.png")
                   if not os.path.exists(os.path.join(CAPTURES, n))]
    if manquantes:
        print(f"\n[!] captures absentes, figures non insérées : {manquantes}")

    restes = controler_narration(xml)
    print(f"\n--- contrôle : narration hors de la section 3.9 ---")
    if restes:
        for k, mot, texte in restes:
            print(f"   [{k}] « {mot} » : {texte}…")
    else:
        print("   aucun passage narratif.")

    if not appliquer:
        print("\n[·] Essai à blanc — aucun fichier écrit.")
        return 1 if restes else 0

    open(chemin, "w", encoding="utf-8").write(xml)
    if os.path.exists(SORTIE):
        try:
            os.remove(SORTIE)
        except PermissionError:
            print(f"\n[!] {os.path.basename(SORTIE)} est ouvert dans Word. "
                  f"Fermez-le et relancez.")
            return 1
    refermer(TRAVAIL, SORTIE)
    print(f"\n[✔] Écrit : {SORTIE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal("--appliquer" in sys.argv))
