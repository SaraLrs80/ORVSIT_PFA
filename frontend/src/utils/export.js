// Export de données vers un fichier, fabriqué dans le navigateur.
//
// Pourquoi côté navigateur plutôt que côté serveur : les pages disposent déjà
// de toutes leurs données. Le fichier produit correspond donc exactement à ce
// que l'utilisateur a sous les yeux, filtres appliqués compris — ce qu'un
// export serveur ne garantirait pas sans repasser tous les filtres en paramètre.

// Excel francophone attend le point-virgule : la virgule y est le séparateur
// décimal, un fichier séparé par des virgules s'ouvrirait en une seule colonne.
const SEPARATEUR = ";";

/**
 * Prépare une valeur pour le format CSV.
 * Une valeur contenant le séparateur, un guillemet ou un retour à la ligne doit
 * être entourée de guillemets, les guillemets internes étant doublés.
 */
function echapper(valeur) {
  if (valeur === null || valeur === undefined) return "";
  // Un nombre est mis en forme ici, au moment de l'écriture, et non par la page
  // qui produit les lignes. C'est ce qui permet à la même ligne d'alimenter le
  // CSV — où le nombre doit devenir « 12,3 » — et le classeur Excel, où il doit
  // rester un nombre. Une page qui pré-formatait ses valeurs interdisait l'un
  // des deux.
  const texte = typeof valeur === "number"
    ? (Number.isFinite(valeur) ? String(valeur).replace(".", ",") : "")
    : String(valeur);
  if (texte.includes(SEPARATEUR) || texte.includes('"') || /[\r\n]/.test(texte)) {
    return `"${texte.replace(/"/g, '""')}"`;
  }
  return texte;
}

/**
 * Écrit un nombre à la française : virgule décimale, sans séparateur de milliers
 * (celui-ci empêcherait Excel de reconnaître la valeur comme un nombre).
 */
export function nombrePourExcel(valeur) {
  if (valeur === null || valeur === undefined || valeur === "") return "";
  const n = Number(valeur);
  return Number.isFinite(n) ? String(n).replace(".", ",") : String(valeur);
}

/**
 * Télécharge un fichier CSV.
 *
 * @param {string}   nomFichier  sans extension
 * @param {string[]} colonnes    en-têtes
 * @param {Array[]}  lignes      tableau de tableaux, dans l'ordre des colonnes
 * @param {string[]} entete      lignes de contexte placées avant le tableau
 *                               (territoire, date, sources…)
 */
export function telechargerCSV(nomFichier, colonnes, lignes, entete = []) {
  const corps = [
    ...entete.map((l) => echapper(l)),
    ...(entete.length ? [""] : []),
    colonnes.map(echapper).join(SEPARATEUR),
    ...lignes.map((ligne) => ligne.map(echapper).join(SEPARATEUR)),
  ].join("\r\n");

  // Le BOM UTF-8 : sans ces trois octets en tête, Excel affiche « TÃ©touan »
  // au lieu de « Tétouan ». Invisible, mais indispensable.
  const contenu = "﻿" + corps;

  const blob = new Blob([contenu], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const lien = document.createElement("a");
  lien.href = url;
  lien.download = `${nomFichier}_${horodatage()}.csv`;
  document.body.appendChild(lien);
  lien.click();
  document.body.removeChild(lien);
  URL.revokeObjectURL(url);      // libère la mémoire retenue par le Blob
}

/**
 * Télécharge un vrai classeur Excel (.xlsx).
 *
 * Pourquoi un vrai classeur : un tableau HTML renommé « .xls » — la solution
 * courte — s'ouvre en affichant un avertissement de format, et surtout ses
 * nombres arrivent en texte. Impossible d'y faire une somme ou un tri
 * numérique sans reconvertir colonne par colonne.
 *
 * Ce que le format apporte en plus du CSV :
 *   - les nombres restent des nombres, quelle que soit la langue d'Excel ;
 *   - une feuille par secteur, au lieu d'un bloc unique de deux cents lignes ;
 *   - des largeurs de colonnes et un filtre automatique.
 *
 * La bibliothèque est chargée à la demande : elle pèse quelques centaines de
 * kilo-octets qui n'ont pas à ralentir l'ouverture de chaque page pour un
 * bouton dont on ne se sert qu'occasionnellement.
 *
 * @param {string} nomFichier  sans extension
 * @param {Array}  feuilles    [{ nom, colonnes, lignes }] — une par onglet
 * @param {string[]} entete    lignes de contexte, placées en tête de la 1re feuille
 */
export async function telechargerXLSX(nomFichier, feuilles, entete = []) {
  const XLSX = await import("xlsx");
  const classeur = XLSX.utils.book_new();

  feuilles.forEach((f, i) => {
    const contexte = i === 0 && entete.length ? [...entete.map((l) => [l]), []] : [];
    const grille = [...contexte, f.colonnes, ...f.lignes];
    const feuille = XLSX.utils.aoa_to_sheet(grille);

    // Largeurs : on regarde le contenu réel, borné pour qu'une source de cent
    // caractères ne produise pas une colonne illisible.
    feuille["!cols"] = f.colonnes.map((titre, c) => {
      const longueurs = [String(titre).length,
        ...f.lignes.map((l) => String(l[c] ?? "").length)];
      return { wch: Math.min(52, Math.max(10, Math.max(...longueurs) + 2)) };
    });

    // Filtre automatique sur la ligne d'en-tête : c'est ce qu'un utilisateur
    // d'Excel fait de toute façon en premier.
    const debut = contexte.length;
    feuille["!autofilter"] = {
      ref: XLSX.utils.encode_range(
        { r: debut, c: 0 },
        { r: debut + f.lignes.length, c: f.colonnes.length - 1 }),
    };

    // Excel refuse les noms d'onglet de plus de 31 caractères et les
    // caractères : \ / ? * [ ]
    const nom = String(f.nom || `Feuille ${i + 1}`).replace(/[:\\/?*[\]]/g, "-").slice(0, 31);
    XLSX.utils.book_append_sheet(classeur, feuille, nom);
  });

  XLSX.writeFile(classeur, `${nomFichier}_${horodatage()}.xlsx`);
}

/** Date du jour au format 2026-07-27, pour trier les fichiers par nom. */
function horodatage() {
  const d = new Date();
  const deuxChiffres = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${deuxChiffres(d.getMonth() + 1)}-${deuxChiffres(d.getDate())}`;
}

/** Nettoie un libellé pour en faire un nom de fichier sûr. */
export function nomDeFichier(texte) {
  return (texte || "export")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "_")
    .replace(/^_|_$/g, "")
    .toLowerCase();
}
