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
  const texte = String(valeur);
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
