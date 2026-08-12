"""
Mettre le dépôt au propre avant publication.

CE QUE CE SCRIPT FAIT, ET CE QU'IL NE FAIT PAS
Il retire du dépôt Git ce qui relève du travail intermédiaire — sauvegardes
horodatées, archives, dossiers de travail — et range les scripts d'essai dans
un dossier dédié. Les fichiers restent SUR LE DISQUE : seule leur présence
dans le dépôt change. Rien n'est perdu.

CE QUI EST CONSERVÉ, ET POURQUOI
Les scripts de correction du catalogue restent versionnés. Ils ne sont pas du
brouillon : ils sont la trace vérifiable de ce que décrit le chapitre 3 du
rapport — chaque correction y est faite avec sauvegarde, essai à blanc et
vérification champ par champ. Les supprimer effacerait la preuve de la
méthode.

Les scripts d'essai sont conservés eux aussi, mais rangés : le rapport
indique que les mesures sont « reproductibles par les scripts d'essai
versionnés avec le code ». Les supprimer rendrait cette phrase fausse.

    python nettoyer.py              montre ce qui serait fait
    python nettoyer.py --appliquer
"""

import os
import shutil
import subprocess
import sys

RACINE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# Ce qui sort du dépôt, sans quitter le disque.
# --------------------------------------------------------------------------
HORS_DEPOT = [
    ("data-pipeline/sauvegardes/",
     "sauvegardes de passe du chargement — 30 Mo de copies de travail"),
    ("data-pipeline/faits/_archive_sante/",
     "tables de santé remplacées par les dénombrements officiels"),
    ("rapport/_travail/",
     "dossier de décompression temporaire du rapport"),
    ("data-pipeline/__pycache__/",
     "cache d'exécution Python"),
    ("rapport/__pycache__/",
     "cache d'exécution Python"),
]

# Les sauvegardes horodatées du catalogue, reconnues par leur nom.
MOTIF_SAUVEGARDES = "data-pipeline/dim_indicateur_avant_"

# --------------------------------------------------------------------------
# Ce qui est supprimé pour de bon : du code que plus rien n'appelle.
# --------------------------------------------------------------------------
CODE_MORT = [
    ("data-pipeline/calcul_idt.py",
     "indicateur composite abandonné ; aucune route ne lit ses tables"),
    ("data-pipeline/methodologie_IDT.md",
     "méthodologie de l'indicateur composite abandonné"),
]

# --------------------------------------------------------------------------
# Rangement : les scripts d'essai dans leur dossier.
# --------------------------------------------------------------------------
ESSAIS = "backend/essais"

# --------------------------------------------------------------------------
IGNORER = """
# ===== Travail intermédiaire (ajouté au nettoyage) =====
data-pipeline/sauvegardes/
data-pipeline/dim_indicateur_avant_*.csv
data-pipeline/faits/_archive_sante/
rapport/_travail/
"""


def git(*args, capture=True):
    return subprocess.run(["git"] + list(args), cwd=RACINE,
                          capture_output=capture, text=True)


def suivis():
    return set(git("ls-files").stdout.splitlines())


def plan():
    """Ce qui serait fait, sans rien faire."""
    fichiers = suivis()
    sortants = []
    for chemin, motif in HORS_DEPOT:
        touches = [f for f in fichiers if f.startswith(chemin)]
        if touches:
            sortants.append((chemin, motif, len(touches)))
    horodatees = [f for f in fichiers if f.startswith(MOTIF_SAUVEGARDES)]

    supprimes = [(c, m) for c, m in CODE_MORT
                 if os.path.exists(os.path.join(RACINE, c))]

    a_ranger = [f for f in os.listdir(os.path.join(RACINE, "backend"))
                if f.startswith("essai_") and f.endswith(".py")]
    return sortants, horodatees, supprimes, a_ranger


def principal(appliquer):
    if not os.path.exists(os.path.join(RACINE, ".git")):
        print("[!] Pas de dépôt Git ici.")
        return 1

    sortants, horodatees, supprimes, a_ranger = plan()

    print("--- retirés du dépôt, conservés sur le disque ---")
    for chemin, motif, n in sortants:
        print(f"   {chemin:<44} {n:>4} fichiers   {motif}")
    if horodatees:
        print(f"   {MOTIF_SAUVEGARDES + '*.csv':<44} {len(horodatees):>4} fichiers"
              f"   sauvegardes horodatées du catalogue")

    print("\n--- supprimés : code que plus rien n'appelle ---")
    for chemin, motif in supprimes:
        print(f"   {chemin:<44} {motif}")
    if not supprimes:
        print("   (rien)")

    print(f"\n--- rangés dans {ESSAIS}/ ---")
    for nom in sorted(a_ranger):
        print(f"   backend/{nom}")
    if not a_ranger:
        print("   (déjà rangés)")

    total = sum(n for _, _, n in sortants) + len(horodatees)
    print(f"\n{total} fichiers quittent le dépôt, {len(supprimes)} sont "
          f"supprimés, {len(a_ranger)} sont déplacés.")

    if not appliquer:
        print("\n[·] Essai à blanc — rien n'a été fait.")
        return 0

    # 1. sortir du dépôt sans toucher au disque
    for chemin, _, _ in sortants:
        git("rm", "-r", "--cached", "-q", chemin)
    for f in horodatees:
        git("rm", "--cached", "-q", f)

    # 2. supprimer le code mort
    for chemin, _ in supprimes:
        entier = os.path.join(RACINE, chemin)
        git("rm", "-q", "-f", chemin)
        if os.path.exists(entier):
            os.remove(entier)

    # 3. ranger les scripts d'essai
    dossier = os.path.join(RACINE, ESSAIS)
    os.makedirs(dossier, exist_ok=True)
    for nom in a_ranger:
        source = os.path.join(RACINE, "backend", nom)
        cible = os.path.join(dossier, nom)
        if git("ls-files", "--error-unmatch", f"backend/{nom}").returncode == 0:
            git("mv", f"backend/{nom}", f"{ESSAIS}/{nom}")
        else:
            shutil.move(source, cible)

    # 4. compléter le .gitignore
    chemin_ignore = os.path.join(RACINE, ".gitignore")
    contenu = open(chemin_ignore, encoding="utf-8").read()
    if "Travail intermédiaire" not in contenu:
        open(chemin_ignore, "a", encoding="utf-8").write(IGNORER)
        print("[✔] .gitignore complété")

    print("\n[✔] Dépôt nettoyé. Vérifiez avec :  git status")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal("--appliquer" in sys.argv))
