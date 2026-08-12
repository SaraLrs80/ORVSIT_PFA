// Impression d'un écran.
//
// Le point délicat est la carte. Une carte Leaflet s'imprime mal : ses tuiles
// sont posées par transformations CSS, le navigateur les repositionne pour la
// feuille, et le résultat est au mieux décalé, au pire vide.
//
// Plutôt que de lutter, on lui donne l'image que le moteur d'export sait déjà
// produire — titre, légende, échelle, sources compris. La carte affichée est
// masquée le temps de l'impression et remplacée par cette image. Le papier
// reçoit donc exactement ce que produit le bouton PNG, ce qui garantit aussi
// que les deux sorties ne divergeront jamais.

import { construireImageCarte } from "./exportCarte";

/**
 * @param {object} o
 *   carte    — () => options du moteur d'export, ou null s'il n'y a pas de carte
 *   ancre    — l'élément où insérer l'image (sinon : le corps du document)
 *   titre    — remplace le titre du document, donc l'en-tête de page du navigateur
 */
export async function imprimer(o = {}) {
  const infos = o.carte?.();
  const titreInitial = document.title;
  let hote = null;

  try {
    if (infos?.carteLeaflet) {
      const canevas = construireImageCarte(infos);
      hote = document.createElement("div");
      hote.className = "impression-seule";
      hote.style.margin = "0 0 14px";
      const img = document.createElement("img");
      img.src = canevas.toDataURL("image/png");
      img.style.width = "100%";
      img.style.border = "1px solid #d8dde6";
      img.style.borderRadius = "10px";
      hote.appendChild(img);
      (o.ancre || document.body).prepend(hote);
      // Laisse au navigateur le temps de décoder l'image : imprimer avant
      // qu'elle ne soit prête laisserait un cadre vide.
      await img.decode().catch(() => {});
    }

    // Le titre du document devient l'en-tête de page imprimée. « ORVSIT —
    // Observatoire TTA » en haut de chaque feuille n'apprend rien ; le nom du
    // territoire, si.
    if (o.titre) document.title = o.titre;

    window.print();
  } finally {
    document.title = titreInitial;
    hote?.remove();
  }
}
