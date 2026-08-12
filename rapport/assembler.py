"""
Assembler le rapport livrable : page de garde + corps du rapport.

POURQUOI DEUX FICHIERS
La page de garde porte les logos et la mise en page de l'établissement ; elle
est fournie telle quelle et n'a pas à être reconstruite. Le corps du rapport
est produit par ajouts_v6.py. Le livrable est la réunion des deux, en PDF.

POURQUOI PASSER PAR WORD POUR LE PDF
Le sommaire, la liste des figures et la liste des tableaux sont des CHAMPS.
Seul Word sait les calculer : une conversion automatique les laisserait
vides. L'export doit donc être fait depuis Word, après mise à jour des
champs. Ce script ne fait que la dernière étape, la réunion.

MODE D'EMPLOI
  1. python ajouts_v6.py --appliquer
  2. ouvrir rapport_stage1_v6.docx dans Word
  3. Ctrl+A puis F9  — les trois tables se remplissent
  4. Fichier > Enregistrer sous > PDF, sous le nom rapport_stage1_v6.pdf
  5. python assembler.py

Le résultat porte le nom Rapport_PFA_Laaroussi_Sara.pdf, à côté du rapport.
"""

import os
import sys

RACINE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.abspath(os.path.join(RACINE, "..", ".."))

CORPS = os.path.join(STAGE, "rapport_stage1_v6.pdf")
LIVRABLE = os.path.join(STAGE, "Rapport_PFA_Laaroussi_Sara.pdf")

# La page de garde, cherchée sous plusieurs noms possibles : le fichier a
# changé de nom au fil des versions, et faire échouer le script pour cela
# serait une perte de temps.
NOMS_GARDE = [
    "page de garde1 (1).pdf",
    "page de garde1.pdf",
    "page de garde.pdf",
    "Page_de_garde.pdf",
]


def trouver_page_de_garde():
    for nom in NOMS_GARDE:
        chemin = os.path.join(STAGE, nom)
        if os.path.exists(chemin):
            return chemin
    # Dernier recours : n'importe quel PDF dont le nom évoque une page de garde.
    for nom in sorted(os.listdir(STAGE)):
        if nom.lower().endswith(".pdf") and "garde" in nom.lower():
            return os.path.join(STAGE, nom)
    return None


def principal():
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("[!] Le module pypdf est nécessaire pour réunir les deux PDF.\n"
              "    Installez-le :  pip install pypdf")
        return 1

    garde = trouver_page_de_garde()
    if garde is None:
        print(f"[!] Page de garde introuvable dans {STAGE}.\n"
              f"    Attendu l'un de : {', '.join(NOMS_GARDE)}")
        return 1
    if not os.path.exists(CORPS):
        print(f"[!] {os.path.basename(CORPS)} introuvable.\n"
              "    Exportez d'abord le rapport en PDF depuis Word, après avoir "
              "mis les champs à jour (Ctrl+A puis F9).")
        return 1

    lecteur_garde = PdfReader(garde)
    lecteur_corps = PdfReader(CORPS)

    ecrivain = PdfWriter()
    for page in lecteur_garde.pages:
        ecrivain.add_page(page)
    for page in lecteur_corps.pages:
        ecrivain.add_page(page)

    ecrivain.add_metadata({
        "/Title": "Conception et mise en place d'une plateforme d'intelligence "
                  "territoriale : entrepôt de données, tableau de bord et "
                  "assistant conversationnel",
        "/Author": "Laaroussi Sara",
        "/Subject": "Rapport de stage — Projet de Fin d'Année, filière Génie "
                    "Informatique, ENSA Tanger, 2025-2026",
        "/Keywords": "intelligence territoriale, entrepôt de données, "
                     "disparités territoriales, assistant conversationnel, "
                     "ORVSIT, CRTTA",
    })

    with open(LIVRABLE, "wb") as f:
        ecrivain.write(f)

    print(f"[✔] {os.path.basename(LIVRABLE)}")
    print(f"    page de garde : {os.path.basename(garde)} "
          f"({len(lecteur_garde.pages)} page)")
    print(f"    corps         : {os.path.basename(CORPS)} "
          f"({len(lecteur_corps.pages)} pages)")
    print(f"    total         : {len(ecrivain.pages)} pages")

    # Un contrôle qui vaut la peine : le sommaire est-il rempli ?
    # Un champ non calculé laisse le texte de remplacement, et le rapport
    # partirait avec trois pages vides.
    try:
        debut = "".join((lecteur_corps.pages[i].extract_text() or "")
                        for i in range(min(8, len(lecteur_corps.pages))))
        if "Mettre à jour les champs" in debut:
            print("\n[!] Le sommaire et les listes sont restés vides.\n"
                  "    Ouvrez le .docx dans Word, faites Ctrl+A puis F9, "
                  "réexportez en PDF et relancez.")
            return 1
        print("    sommaire et listes : remplis")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
