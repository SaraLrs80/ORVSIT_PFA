"""
Petite boîte à outils pour modifier le rapport sans le reconstruire.

POURQUOI
Le rapport existe déjà : styles, numérotation des figures, tableaux, images.
Le régénérer à chaque ajout ferait perdre tout ce qui a été mis en forme à la
main. On ouvre donc l'archive, on modifie `word/document.xml`, on referme.

Le document est une suite de <w:p>. Ce module ne connaît que ça : il découpe
le corps en paragraphes, sait retrouver celui qui porte un titre donné, et
sait remplacer une section entière par de nouveaux paragraphes construits au
même format que les existants.

RÈGLE DE PRUDENCE
Aucune fonction n'écrit sur place. On lit, on transforme, on rend une chaîne ;
l'appelant sauvegarde et vérifie. Chaque script d'édition compare ensuite le
nombre de paragraphes et le texte avant/après.
"""

import re

# Le format des paragraphes du rapport, relevé sur l'existant : interligne 1,5
# et justification. Les reproduire à l'identique évite qu'un ajout se voie.
ESPACEMENT = '<w:spacing w:line="360" w:lineRule="auto"/>'
JUSTIFIE = '<w:jc w:val="both"/>'

MOTIF_P = re.compile(r"<w:p(?:\s[^>]*)?(?:/>|>.*?</w:p>)", re.S)
MOTIF_T = re.compile(r"<w:t[^>]*>(.*?)</w:t>", re.S)
MOTIF_STYLE = re.compile(r'<w:pStyle w:val="([^"]+)"')


def echapper(texte):
    return (texte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def paragraphes(xml):
    """Les paragraphes du corps, sous forme de (début, fin, texte, style)."""
    corps = xml.find("<w:body>")
    sortie = []
    for m in MOTIF_P.finditer(xml, corps if corps != -1 else 0):
        bloc = m.group(0)
        texte = "".join(MOTIF_T.findall(bloc))
        style = MOTIF_STYLE.search(bloc)
        sortie.append((m.start(), m.end(), texte.strip(),
                       style.group(1) if style else ""))
    return sortie


def trouver_titre(xml, debut_du_texte):
    """L'indice du paragraphe dont le texte commence par ce libellé.

    On compare sur le texte reconstitué, jamais sur le XML brut : Word coupe
    un titre en plusieurs runs, et « 3.8.8 » peut n'exister nulle part comme
    chaîne contiguë dans le fichier.
    """
    ps = paragraphes(xml)
    for i, (_, _, texte, style) in enumerate(ps):
        if texte.startswith(debut_du_texte) and style.startswith(("Heading", "Titre")):
            return i, ps
    raise LookupError(f"titre introuvable : {debut_du_texte!r}")


def fin_de_section(ps, i):
    """Le premier paragraphe qui n'appartient plus à la section i.

    Une section s'arrête au prochain titre de niveau égal ou supérieur ;
    un sous-titre plus profond en fait encore partie.
    """
    niveau = niveau_de(ps[i][3])
    for j in range(i + 1, len(ps)):
        n = niveau_de(ps[j][3])
        if n and n <= niveau:
            return j
    return len(ps)


def niveau_de(style):
    m = re.fullmatch(r"(?:Heading|Titre)(\d)", style or "")
    return int(m.group(1)) if m else 0


# --------------------------------------------------------------------------
# Fabrication de paragraphes
# --------------------------------------------------------------------------

def para(texte, style=None, gras=False, italique=False, centre=False):
    prop = ""
    if style:
        prop += f'<w:pStyle w:val="{style}"/>'
    prop += ESPACEMENT
    prop += '<w:jc w:val="center"/>' if centre else JUSTIFIE
    rpr = ""
    if gras:
        rpr += "<w:b/><w:bCs/>"
    if italique:
        rpr += "<w:i/><w:iCs/>"
    run_rpr = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
    return (f"<w:p><w:pPr>{prop}</w:pPr>"
            f"<w:r>{run_rpr}<w:t xml:space=\"preserve\">{echapper(texte)}</w:t></w:r></w:p>")


def puce(texte, num_id):
    """Un élément de liste à puces, rattaché à une numérotation existante.

    On ne crée pas de nouvelle numérotation : on réutilise celle de la liste
    que l'on remplace, relevée dans le document. Une puce écrite en dur — le
    caractère « • » dans le texte — ne se comporterait pas comme une liste au
    moment de la mise en page.
    """
    return (f'<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/>'
            f'<w:numId w:val="{num_id}"/></w:numPr>{ESPACEMENT}{JUSTIFIE}</w:pPr>'
            f'<w:r><w:t xml:space="preserve">{echapper(texte)}</w:t></w:r></w:p>')


def numerotation_de(xml, debut_du_texte):
    """L'identifiant de numérotation utilisé par la liste d'une section."""
    i, ps = trouver_titre(xml, debut_du_texte)
    j = fin_de_section(ps, i)
    for k in range(i, j):
        m = re.search(r'<w:numId w:val="(\d+)"/>', xml[ps[k][0]:ps[k][1]])
        if m:
            return m.group(1)
    return None


def titre(texte, niveau=3):
    return para(texte, style=f"Heading{niveau}")


def legende(texte):
    """Une légende de figure, dans le style du document.

    Le rapport numérote ses figures par un champ SEQ : on reproduit le champ
    plutôt qu'un numéro écrit à la main, sinon toute insertion décalerait
    toutes les légendes suivantes.
    """
    return ('<w:p><w:pPr><w:pStyle w:val="Caption"/>'
            f'{ESPACEMENT}<w:jc w:val="center"/></w:pPr>'
            '<w:r><w:t xml:space="preserve">Figure </w:t></w:r>'
            '<w:fldSimple w:instr=" SEQ Figure \\* ARABIC ">'
            '<w:r><w:t>0</w:t></w:r></w:fldSimple>'
            f'<w:r><w:t xml:space="preserve">. {echapper(texte)}</w:t></w:r></w:p>')


# --------------------------------------------------------------------------
# Images
# --------------------------------------------------------------------------

LARGEUR_TEXTE = 5486400   # 6 pouces en EMU, la largeur utile des figures


def ajouter_image(dossier, chemin_png):
    """Copie l'image dans l'archive et rend l'identifiant de relation.

    Trois fichiers doivent rester d'accord : le média lui-même, la relation
    qui lui donne un rId, et la déclaration du type de contenu. Le troisième
    est déjà là — le rapport contient des PNG — mais on le vérifie plutôt que
    de le supposer.
    """
    import os
    import shutil

    media = os.path.join(dossier, "word", "media")
    os.makedirs(media, exist_ok=True)
    nom = os.path.basename(chemin_png)
    shutil.copy2(chemin_png, os.path.join(media, nom))

    chemin_rels = os.path.join(dossier, "word", "_rels", "document.xml.rels")
    rels = open(chemin_rels, encoding="utf-8").read()

    deja = re.search(rf'Id="(rId\d+)"[^>]*Target="media/{re.escape(nom)}"', rels)
    if deja:
        return deja.group(1)

    numeros = [int(n) for n in re.findall(r'Id="rId(\d+)"', rels)]
    rid = f"rId{max(numeros) + 1}"
    rels = rels.replace("</Relationships>",
        f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
        f'officeDocument/2006/relationships/image" Target="media/{nom}"/>'
        "</Relationships>")
    open(chemin_rels, "w", encoding="utf-8").write(rels)

    types = os.path.join(dossier, "[Content_Types].xml")
    contenu = open(types, encoding="utf-8").read()
    ext = nom.rsplit(".", 1)[-1].lower()
    if f'Extension="{ext}"' not in contenu:
        raise RuntimeError(f"type de contenu absent pour .{ext}")
    return rid


def figure(rid, largeur_px, hauteur_px, identifiant):
    """Un paragraphe centré contenant l'image, mise à la largeur du texte."""
    cx = LARGEUR_TEXTE
    cy = int(LARGEUR_TEXTE * hauteur_px / largeur_px)
    return (
        f'<w:p><w:pPr>{ESPACEMENT}<w:jc w:val="center"/></w:pPr>'
        '<w:r><w:rPr><w:noProof/></w:rPr><w:drawing>'
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:docPr id="{identifiant}" name="Image {identifiant}"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:nvPicPr><pic:cNvPr id="{identifiant}" name="Image {identifiant}"/>'
        '<pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rid}" cstate="print"/>'
        '<a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')


def taille(chemin_png):
    """Largeur et hauteur d'un PNG, lues dans son en-tête IHDR."""
    import struct
    with open(chemin_png, "rb") as f:
        entete = f.read(26)
    if entete[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{chemin_png} n'est pas un PNG")
    return struct.unpack(">II", entete[16:24])


def remplacer_section(xml, debut_du_texte, nouveaux):
    """Remplace la section entière (titre compris) par ces paragraphes."""
    i, ps = trouver_titre(xml, debut_du_texte)
    j = fin_de_section(ps, i)
    return xml[:ps[i][0]] + "".join(nouveaux) + xml[ps[j - 1][1]:]


def inserer_apres_section(xml, debut_du_texte, nouveaux):
    """Insère ces paragraphes juste après la fin de la section nommée."""
    i, ps = trouver_titre(xml, debut_du_texte)
    j = fin_de_section(ps, i)
    coupe = ps[j - 1][1]
    return xml[:coupe] + "".join(nouveaux) + xml[coupe:]


def inserer_avant_titre(xml, debut_du_texte, nouveaux):
    i, ps = trouver_titre(xml, debut_du_texte)
    return xml[:ps[i][0]] + "".join(nouveaux) + xml[ps[i][0]:]


def renommer_titre(xml, ancien_debut, nouveau_texte):
    """Change le texte d'un titre sans toucher à son style."""
    i, ps = trouver_titre(xml, ancien_debut)
    deb, fin, _, style = ps[i]
    return xml[:deb] + para(nouveau_texte, style=style) + xml[fin:]


def figures_de(xml, debut_du_texte):
    """Les paragraphes d'une section qui contiennent une image, tels quels.

    Réécrire une section ferait disparaître ses illustrations : elles sont
    incorporées dans le document, pas rechargées depuis un fichier. On les
    extrait donc avant de remplacer, pour les replacer ensuite à l'identique.
    """
    i, ps = trouver_titre(xml, debut_du_texte)
    j = fin_de_section(ps, i)
    return [xml[ps[k][0]:ps[k][1]] for k in range(i, j)
            if "<w:drawing>" in xml[ps[k][0]:ps[k][1]]]


def trouver_paragraphe(xml, debut_du_texte):
    """L'indice du paragraphe de corps dont le texte commence par ce libellé."""
    ps = paragraphes(xml)
    for i, (_, _, texte, style) in enumerate(ps):
        if texte.startswith(debut_du_texte) and not niveau_de(style):
            return i, ps
    raise LookupError(f"paragraphe introuvable : {debut_du_texte!r}")


def remplacer_paragraphe(xml, debut_du_texte, nouveaux):
    """Remplace un paragraphe de corps par un ou plusieurs autres."""
    i, ps = trouver_paragraphe(xml, debut_du_texte)
    if isinstance(nouveaux, str):
        nouveaux = [nouveaux]
    return xml[:ps[i][0]] + "".join(nouveaux) + xml[ps[i][1]:]


def supprimer_paragraphe(xml, debut_du_texte):
    return remplacer_paragraphe(xml, debut_du_texte, [])


# --------------------------------------------------------------------------
# Tableaux
# --------------------------------------------------------------------------

LARGEURS_TABLEAU = None   # relevées sur la première ligne du tableau visé


def _tableau_contenant(xml, repere):
    for m in re.finditer(r"<w:tbl>.*?</w:tbl>", xml, re.S):
        if repere in m.group(0):
            return m
    raise LookupError(f"tableau introuvable, repère : {repere!r}")


def cellule(texte, largeur):
    return (f'<w:tc><w:tcPr><w:tcW w:w="{largeur}" w:type="dxa"/></w:tcPr>'
            '<w:p><w:pPr><w:spacing w:line="240" w:lineRule="auto"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{echapper(texte)}</w:t></w:r></w:p></w:tc>')


def largeurs_de(xml, repere):
    """Les largeurs de colonne du tableau, relevées sur sa dernière ligne."""
    tbl = _tableau_contenant(xml, repere).group(0)
    derniere = re.findall(r"<w:tr[ >].*?</w:tr>", tbl, re.S)[-1]
    return [int(l) for l in re.findall(r'<w:tcW w:w="(\d+)"', derniere)]


def remplacer_lignes(xml, repere, lignes, depuis_la_ligne):
    """Remplace les lignes d'un tableau à partir d'un indice donné.

    L'en-tête et les lignes précédentes sont conservés tels quels : leur mise
    en forme — trame de fond, gras — n'est pas reproduite ici, et la refaire à
    la main serait le meilleur moyen de la perdre.
    """
    m = _tableau_contenant(xml, repere)
    tbl = m.group(0)
    trs = list(re.finditer(r"<w:tr[ >].*?</w:tr>", tbl, re.S))
    largeurs = [int(l) for l in re.findall(r'<w:tcW w:w="(\d+)"', trs[-1].group(0))]
    neuves = "".join(
        "<w:tr>" + "".join(cellule(c, largeurs[i]) for i, c in enumerate(ligne))
        + "</w:tr>" for ligne in lignes)
    nouveau = tbl[:trs[depuis_la_ligne].start()] + neuves + tbl[trs[-1].end():]
    return xml[:m.start()] + nouveau + xml[m.end():]


# Le style de tableau du rapport, relevé sur l'existant. On le réutilise
# plutôt que d'en définir un nouveau : un tableau ajouté doit être
# indiscernable de ceux déjà présents.
STYLE_TABLEAU = "PlainTable1"
LARGEUR_TABLEAU = 8674
ENTETE_FOND = "00498D"


def _cellule(texte, largeur, entete=False):
    fond = (f'<w:shd w:val="clear" w:color="auto" w:fill="{ENTETE_FOND}"/>'
            if entete else "")
    rpr = ('<w:rPr><w:b/><w:bCs/><w:color w:val="FFFFFF"/></w:rPr>'
           if entete else "")
    return (f'<w:tc><w:tcPr><w:tcW w:w="{largeur}" w:type="dxa"/>{fond}</w:tcPr>'
            '<w:p><w:pPr><w:spacing w:line="240" w:lineRule="auto"/></w:pPr>'
            f'<w:r>{rpr}<w:t xml:space="preserve">{echapper(texte)}</w:t></w:r>'
            '</w:p></w:tc>')


def tableau(entetes, lignes, proportions=None):
    """Un tableau complet, dans le style des tableaux existants.

    `proportions` répartit la largeur entre les colonnes ; par défaut elles
    sont égales. Les largeurs sont posées à la fois sur la grille et sur
    chaque cellule : sans les deux, le rendu diverge d'un lecteur à l'autre.
    """
    n = len(entetes)
    parts = proportions or [1] * n
    total = sum(parts)
    largeurs = [int(LARGEUR_TABLEAU * p / total) for p in parts]
    largeurs[-1] += LARGEUR_TABLEAU - sum(largeurs)   # l'arrondi va au dernier

    grille = "".join(f'<w:gridCol w:w="{l}"/>' for l in largeurs)
    tr_entete = ("<w:tr><w:trPr><w:tblHeader/></w:trPr>"
                 + "".join(_cellule(t, largeurs[i], entete=True)
                           for i, t in enumerate(entetes)) + "</w:tr>")
    corps = "".join(
        "<w:tr>" + "".join(_cellule(str(c), largeurs[i])
                           for i, c in enumerate(ligne)) + "</w:tr>"
        for ligne in lignes)

    return (f'<w:tbl><w:tblPr><w:tblStyle w:val="{STYLE_TABLEAU}"/>'
            f'<w:tblW w:w="{LARGEUR_TABLEAU}" w:type="dxa"/>'
            '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" '
            'w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
            f'</w:tblPr><w:tblGrid>{grille}</w:tblGrid>{tr_entete}{corps}</w:tbl>'
            f'<w:p><w:pPr>{ESPACEMENT}</w:pPr></w:p>')


def legende_tableau(texte):
    """Une légende de tableau, numérotée par le même champ SEQ que l'existant."""
    return ('<w:p><w:pPr><w:pStyle w:val="Caption"/>'
            f'{ESPACEMENT}<w:jc w:val="center"/></w:pPr>'
            '<w:r><w:t xml:space="preserve">Tableau </w:t></w:r>'
            '<w:fldSimple w:instr=" SEQ Tableau \\* ARABIC ">'
            '<w:r><w:t>0</w:t></w:r></w:fldSimple>'
            f'<w:r><w:t xml:space="preserve">. {echapper(texte)}</w:t></w:r></w:p>')


# --------------------------------------------------------------------------
# Numérotation des figures et des tableaux
# --------------------------------------------------------------------------
# Word calcule la valeur d'un champ SEQ à l'affichage, mais il conserve dans
# le fichier la dernière valeur calculée. Un champ neuf porte donc « 0 »
# jusqu'à ce que l'utilisateur mette les champs à jour — ce qu'on ne peut pas
# demander à un lecteur. On écrit donc la bonne valeur dans le cache, en
# parcourant le document dans l'ordre.
#
# Deux formes de champ coexistent dans le rapport, selon la version de Word
# qui a écrit le paragraphe : la forme simple <w:fldSimple> et la forme
# complexe, découpée en begin / instrText / separate / valeur / end. Les deux
# doivent être renumérotées, sans quoi les légendes anciennes et nouvelles ne
# suivraient pas la même série.

_SEQ_SIMPLE = re.compile(
    r'(<w:fldSimple[^>]*w:instr="[^"]*SEQ\s+(Figure|Tableau)[^"]*"[^>]*>)'
    r'(.*?)(</w:fldSimple>)', re.S)

_SEQ_COMPLEXE = re.compile(
    r'(<w:instrText[^>]*>\s*SEQ\s+(Figure|Tableau).*?'
    r'<w:fldChar w:fldCharType="separate"/>\s*</w:r>\s*<w:r[^>]*>)'
    r'(<w:t[^>]*>)(\d*)(</w:t>)', re.S)


def renumeroter(xml):
    """Écrit dans chaque champ SEQ le numéro que Word afficherait.

    Rend le XML modifié et le décompte par série, pour contrôle.
    """
    compteurs = {"Figure": 0, "Tableau": 0}
    positions = []

    for m in _SEQ_SIMPLE.finditer(xml):
        positions.append((m.start(), m.end(), m.group(2), "simple", m))
    for m in _SEQ_COMPLEXE.finditer(xml):
        positions.append((m.start(), m.end(), m.group(2), "complexe", m))
    positions.sort()

    morceaux, curseur = [], 0
    for debut, fin, serie, forme, m in positions:
        compteurs[serie] += 1
        n = compteurs[serie]
        morceaux.append(xml[curseur:debut])
        if forme == "simple":
            morceaux.append(f'{m.group(1)}<w:r><w:t>{n}</w:t></w:r>{m.group(4)}')
        else:
            morceaux.append(f"{m.group(1)}{m.group(3)}{n}{m.group(5)}")
        curseur = fin
    morceaux.append(xml[curseur:])
    return "".join(morceaux), compteurs


def saut_de_page():
    return ('<w:p><w:pPr><w:spacing w:after="0"/></w:pPr>'
            '<w:r><w:br w:type="page"/></w:r></w:p>')


def champ(instruction, texte_cache="Mettre à jour les champs (Ctrl+A puis F9)"):
    """Un champ Word qui se recalcule à l'ouverture du document.

    L'attribut `dirty` demande à Word de recalculer le champ dès l'ouverture :
    sans lui, la table des matières resterait vide jusqu'à ce que le lecteur
    pense à la mettre à jour lui-même.
    """
    return (f'<w:p><w:pPr>{ESPACEMENT}</w:pPr>'
            '<w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
            f'<w:r><w:instrText xml:space="preserve"> {instruction} </w:instrText></w:r>'
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            f'<w:r><w:t xml:space="preserve">{echapper(texte_cache)}</w:t></w:r>'
            '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')
