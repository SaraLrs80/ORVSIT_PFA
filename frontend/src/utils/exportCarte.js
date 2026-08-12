// Export d'une carte en image.
//
// Ce fichier ne capture PAS l'écran. Il redessine la carte.
//
// La première version s'appuyait sur html2canvas, qui rastérise un nœud du DOM.
// Trois défauts s'y sont succédé : des tuiles de réserve débordant du cadre, un
// masque tronqué, puis des étiquettes posées hors des provinces. Tous avaient la
// même origine — Leaflet positionne ses calques par des transformations CSS, et
// html2canvas ne les applique pas identiquement d'un calque à l'autre. Chaque
// correction déplaçait le défaut sans le supprimer.
//
// On dessine donc nous-mêmes, dans l'ordre où Leaflet dessine : tuiles, masque,
// aplats, étiquettes. Chaque point est projeté par Leaflet lui-même, avec
// `latLngToContainerPoint`. Le résultat est exact par construction, et
// l'application se passe d'une dépendance de plus.

const POLICE = "Manrope, -apple-system, Segoe UI, sans-serif";

/**
 * @param {object} o
 *   carteLeaflet — l'instance Leaflet, seule à savoir projeter
 *   geojson      — les territoires affichés
 *   styleDe      — (id) => { fond, opacite, trait, epaisseur } | null
 *   masque       — couleur du pourtour, ou null pour ne pas masquer
 *   etiquetteDe  — (id) => texte à écrire sur le territoire, ou null
 *   titre, sousTitre, palette, bornes, note, source, attribution
 *   nomFichier, echelle (2 par défaut)
 */
export async function exporterCartePNG(o = {}) {
  const image = construireImageCarte(o);
  await telecharger(image, `${o.nomFichier || "carte"}.png`);
  return image;
}

/**
 * La planche finie, en mémoire, sans téléchargement.
 *
 * Exposée pour que l'impression puisse remplacer la carte vivante par cette
 * image : le papier reçoit alors exactement ce que produit le bouton PNG, et
 * les deux sorties ne peuvent pas diverger.
 */
export function construireImageCarte(o = {}) {
  return composer(rasteriser(o), o);
}

/**
 * La même image, déposée dans une page A4.
 *
 * Une image se colle dans une présentation ; un PDF s'imprime et se transmet en
 * gardant ses dimensions physiques. L'orientation suit les proportions de la
 * carte : une région large imprimée en portrait laisserait la page à moitié vide.
 */
export async function exporterCartePDF(o = {}) {
  const image = construireImageCarte(o);
  const { jsPDF } = await import("jspdf");

  const paysage = image.width > image.height;
  const doc = new jsPDF({ orientation: paysage ? "landscape" : "portrait",
                          unit: "mm", format: "a4" });
  const largeurPage = paysage ? 297 : 210;
  const hauteurPage = paysage ? 210 : 297;
  const marge = 10;

  // Même facteur en largeur et en hauteur : une carte étirée ment sur les
  // distances, et c'est l'erreur qu'un géographe repère en premier.
  const facteur = Math.min((largeurPage - 2 * marge) / image.width,
                           (hauteurPage - 2 * marge) / image.height);
  const l = image.width * facteur, h = image.height * facteur;

  doc.addImage(image.toDataURL("image/png"), "PNG",
               (largeurPage - l) / 2, (hauteurPage - h) / 2, l, h, undefined, "FAST");
  doc.save(`${o.nomFichier || "carte"}.pdf`);
}

/* ═════════════════════════════ la carte elle-même ═══════════════════════════ */

function rasteriser(o) {
  const map = o.carteLeaflet;
  const e = o.echelle ?? 2;
  const taille = map.getSize();

  const c = document.createElement("canvas");
  c.width = Math.round(taille.x * e);
  c.height = Math.round(taille.y * e);
  const g = c.getContext("2d");

  g.fillStyle = "#ffffff";
  g.fillRect(0, 0, c.width, c.height);

  dessinerTuiles(g, map, e);
  if (o.masque) dessinerMasque(g, o, e, 0, c.width, c.height);
  dessinerAplats(g, o, e);
  dessinerEtiquettes(g, o, e);
  return c;
}

/** Les tuiles déjà chargées, replacées par la projection de Leaflet. */
function dessinerTuiles(g, map, e) {
  map.eachLayer((couche) => {
    if (!couche._tiles || !couche.getTileSize) return;
    const taille = couche.getTileSize();
    Object.values(couche._tiles).forEach((t) => {
      if (!t.el || !t.loaded || t.el.naturalWidth === 0) return;
      const p = map.layerPointToContainerPoint(couche._getTilePos(t.coords));
      try {
        g.drawImage(t.el, p.x * e, p.y * e, taille.x * e, taille.y * e);
      } catch {
        // Une tuile refusée par la politique d'origine : on la saute plutôt
        // que d'abandonner toute l'image.
      }
    });
  });
}

/** Trace les anneaux d'un territoire dans le chemin courant. */
function tracer(g, map, feature, e, decalageY) {
  const geo = feature.geometry;
  if (!geo) return;
  const anneaux = geo.type === "Polygon" ? geo.coordinates
    : geo.type === "MultiPolygon" ? geo.coordinates.flat() : [];
  anneaux.forEach((anneau) => {
    anneau.forEach(([lng, lat], i) => {
      const p = map.latLngToContainerPoint([lat, lng]);
      const x = p.x * e, y = p.y * e + decalageY;
      if (i === 0) g.moveTo(x, y); else g.lineTo(x, y);
    });
    g.closePath();
  });
}

/**
 * Le masque : un rectangle couvrant toute l'image, percé aux contours des
 * territoires. La règle « evenodd » compte les traversées — un point situé
 * dans un trou en compte deux depuis l'extérieur, il reste donc transparent.
 */
function dessinerMasque(g, o, e, decalageY, largeur, hauteur) {
  g.save();
  g.beginPath();
  g.rect(0, decalageY, largeur, hauteur);
  (o.geojson?.features || []).forEach((f) => tracer(g, o.carteLeaflet, f, e, decalageY));
  g.fillStyle = o.masque;
  g.fill("evenodd");
  g.restore();
}

/** Les aplats de couleur et leurs contours. */
function dessinerAplats(g, o, e) {
  if (!o.styleDe) return;
  const map = o.carteLeaflet;
  // Le territoire ouvert passe en dernier : son contour épais serait sinon
  // recouvert par celui de ses voisins.
  const ordonnees = [...(o.geojson?.features || [])].sort(
    (a, b) => (o.styleDe(a.properties.id)?.epaisseur ?? 1)
            - (o.styleDe(b.properties.id)?.epaisseur ?? 1));

  ordonnees.forEach((f) => {
    const s = o.styleDe(f.properties.id);
    if (!s) return;
    g.beginPath();
    tracer(g, map, f, e, 0);
    g.globalAlpha = s.opacite ?? 1;
    g.fillStyle = s.fond;
    g.fill("evenodd");
    g.globalAlpha = 1;
    g.strokeStyle = s.trait || "#ffffff";
    g.lineWidth = (s.epaisseur || 1) * e;
    g.lineJoin = "round";
    g.stroke();
  });
}

/** Les valeurs écrites sur les territoires, au centre de leur plus grand anneau. */
function dessinerEtiquettes(g, o, e) {
  if (!o.etiquetteDe) return;
  const map = o.carteLeaflet;
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.font = `700 ${Math.round(12 * e)}px ${POLICE}`;

  (o.geojson?.features || []).forEach((f) => {
    const texte = o.etiquetteDe(f.properties.id);
    if (!texte) return;
    const geo = f.geometry;
    const anneaux = geo?.type === "Polygon" ? geo.coordinates
      : geo?.type === "MultiPolygon" ? geo.coordinates.flat() : [];
    if (!anneaux.length) return;

    // Le plus grand anneau : une commune peut avoir des îlots, et son nom
    // écrit sur un îlot minuscule serait illisible.
    const grand = anneaux.reduce((a, b) => (b.length > a.length ? b : a), anneaux[0]);
    let sx = 0, sy = 0;
    grand.forEach(([lng, lat]) => {
      const p = map.latLngToContainerPoint([lat, lng]);
      sx += p.x; sy += p.y;
    });
    const x = (sx / grand.length) * e, y = (sy / grand.length) * e;

    // Liseré clair sous le texte : il reste lisible sur un aplat foncé.
    g.lineWidth = 4 * e;
    g.strokeStyle = "rgba(255,255,255,.9)";
    g.strokeText(texte, x, y);
    g.fillStyle = "#0f2f56";
    g.fillText(texte, x, y);
  });
}

/* ═══════════════════════════ le cadre documentaire ══════════════════════════ */

/**
 * Mise en page cartographique, reprise de celle du site officiel.
 *
 * Les cartouches sont posés SUR la carte plutôt qu'au-dessus d'elle dans des
 * bandes blanches. La différence n'est pas décorative : le territoire occupe
 * toute l'image au lieu d'en abandonner un tiers à des marges, et l'ensemble
 * se lit comme une planche, pas comme une capture légendée.
 *
 * Le pied reprend ce qu'une carte doit déclarer pour être opposable : sources
 * des données, fond de plan, système de projection et date d'édition.
 */
function composer(carte, o) {
  const g = carte.getContext("2d");
  // Les étiquettes ont laissé la ligne de base au milieu ; sans cette remise à
  // zéro, tous les textes du cadre seraient décalés vers le haut.
  g.textBaseline = "alphabetic";
  g.textAlign = "left";
  const e = carte.width / 1600;                 // unité de composition
  const px = (n) => `${Math.round(n * e)}px`;
  const m = Math.round(28 * e);
  const pied = Math.round(46 * e);

  /* ---------------- cartouche de titre ---------------- */
  g.font = `800 ${px(34)} ${POLICE}`;
  const largeurTitre = g.measureText(o.titre || "").width;
  g.font = `500 ${px(15)} ${POLICE}`;
  const largeurSous = g.measureText(o.sousTitre || "").width;
  const lCartouche = Math.max(largeurTitre, largeurSous, 300 * e) + 60 * e;
  const hCartouche = Math.round(112 * e);

  carteBlanche(g, m, m, lCartouche, hCartouche, 6 * e);
  g.fillStyle = "#e8af20";                       // le liseré doré de l'ORVSIT
  g.fillRect(m, m, Math.round(5 * e), hCartouche);

  const tx = m + Math.round(26 * e);
  g.textAlign = "left";
  g.fillStyle = "#b08a1c";
  g.font = `800 ${px(11)} ${POLICE}`;
  g.fillText("ORVSIT · CARTE THÉMATIQUE", tx, m + Math.round(30 * e));
  g.fillStyle = "#0f2a4f";
  g.font = `800 ${px(34)} ${POLICE}`;
  g.fillText(o.titre || "", tx, m + Math.round(68 * e));
  g.fillStyle = "#65728a";
  g.font = `500 ${px(15)} ${POLICE}`;
  g.fillText(o.sousTitre || "", tx, m + Math.round(94 * e));

  fleche(g, carte.width - m - Math.round(26 * e), m + Math.round(30 * e), e);

  /* ---------------- cartouche de légende ---------------- */
  if (o.palette?.length) {
    const l = Math.round(400 * e);
    const h = Math.round(150 * e);
    const x = m;
    const y = carte.height - pied - m - h;
    carteBlanche(g, x, y, l, h, 6 * e);

    const px0 = x + Math.round(26 * e);
    g.fillStyle = "#0f2a4f";
    g.font = `800 ${px(19)} ${POLICE}`;
    g.fillText(o.titreLegende || o.titre || "", px0, y + Math.round(34 * e));

    g.fillStyle = "#7a8499";
    g.font = `800 ${px(11)} ${POLICE}`;
    g.fillText("VALEURS PAR CLASSE", px0, y + Math.round(60 * e));

    const lr = l - Math.round(52 * e);
    const hr = Math.round(13 * e);
    const pas = lr / o.palette.length;
    o.palette.forEach((couleur, i) => {
      g.fillStyle = couleur;
      g.fillRect(px0 + i * pas, y + Math.round(70 * e), Math.ceil(pas), hr);
    });

    g.fillStyle = "#65728a";
    g.font = `600 ${px(12)} ${POLICE}`;
    g.fillText(String(o.bornes?.min ?? ""), px0, y + Math.round(103 * e));
    const max = String(o.bornes?.max ?? "");
    g.fillText(max, px0 + lr - g.measureText(max).width, y + Math.round(103 * e));

    g.fillStyle = "#8e97a8";
    g.font = `500 ${px(11)} ${POLICE}`;
    g.fillText(o.note || "", px0, y + Math.round(124 * e));
    g.fillText(o.sousNote || "", px0, y + Math.round(140 * e));
  }

  echelleGraphique(g, o, e, m + Math.round(430 * e), carte.height - pied - m - Math.round(14 * e));

  /* ---------------- pied de planche ---------------- */
  g.fillStyle = "#0f2a4f";
  g.fillRect(0, carte.height - pied, carte.width, pied);
  g.fillStyle = "#e8af20";
  g.fillRect(0, carte.height - pied, carte.width, Math.round(3 * e));

  const yPied = carte.height - pied + Math.round(29 * e);
  g.font = `700 ${px(12)} ${POLICE}`;
  g.fillStyle = "#ffffff";
  g.fillText("Sources : ", m, yPied);
  const decalage = g.measureText("Sources : ").width;
  g.font = `500 ${px(12)} ${POLICE}`;
  g.fillStyle = "rgba(255,255,255,.82)";
  const date = new Date().toLocaleDateString("fr-FR");
  // Déclarer la projection n'est pas un ornement : sans elle, on ne peut ni
  // superposer cette carte à une autre, ni vérifier une mesure.
  g.fillText(
    [o.source, o.attribution && `fond ${o.attribution.replace(/<[^>]+>/g, "")}`,
     "WGS 84 / Web Mercator (EPSG:3857)", `édition ${date}`]
      .filter(Boolean).join(" · "),
    m + decalage, yPied);

  g.textAlign = "right";
  g.fillStyle = "#e8af20";
  g.font = `800 ${px(12)} ${POLICE}`;
  g.fillText("ORVSIT · Région TTA", carte.width - m, yPied);
  g.textAlign = "left";

  /* ---------------- filet de cadre ---------------- */
  g.strokeStyle = "#0f2a4f";
  g.lineWidth = Math.round(3 * e);
  g.strokeRect(g.lineWidth / 2, g.lineWidth / 2,
               carte.width - g.lineWidth, carte.height - g.lineWidth);

  return carte;
}

/** Un cartouche blanc à coins arrondis, avec une ombre discrète. */
function carteBlanche(g, x, y, l, h, r) {
  g.save();
  g.shadowColor = "rgba(15,42,79,.18)";
  g.shadowBlur = r * 3;
  g.shadowOffsetY = r * 0.6;
  g.fillStyle = "#ffffff";
  g.beginPath();
  g.moveTo(x + r, y);
  g.arcTo(x + l, y, x + l, y + h, r);
  g.arcTo(x + l, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r);
  g.arcTo(x, y, x + l, y, r);
  g.closePath();
  g.fill();
  g.restore();
}

/** Flèche du nord : une carte sans orientation déclarée n'en est pas une. */
function fleche(g, x, y, e) {
  const h = 34 * e;
  g.save();
  g.fillStyle = "#ffffff";
  g.strokeStyle = "rgba(15,42,79,.35)";
  g.lineWidth = 1.5 * e;
  g.beginPath();
  g.moveTo(x, y - h / 2);
  g.lineTo(x + 9 * e, y + h / 2);
  g.lineTo(x, y + h / 4);
  g.lineTo(x - 9 * e, y + h / 2);
  g.closePath();
  g.fill();
  g.stroke();
  g.fillStyle = "#ffffff";
  g.font = `800 ${Math.round(12 * e)}px ${POLICE}`;
  g.textAlign = "center";
  g.fillText("N", x, y - h / 2 - 6 * e);
  g.textAlign = "left";
  g.restore();
}

/**
 * Échelle graphique. On mesure la distance réelle couverte par 100 pixels au
 * centre de la carte, puis on retient la distance ronde immédiatement
 * inférieure — une échelle qui annonce « 137 km » ne se lit pas.
 */
function echelleGraphique(g, o, e, x, y) {
  const map = o.carteLeaflet;
  if (!map) return;
  const taille = map.getSize();
  const a = map.containerPointToLatLng([taille.x / 2 - 50, taille.y / 2]);
  const b = map.containerPointToLatLng([taille.x / 2 + 50, taille.y / 2]);
  const metresPour100px = map.distance(a, b);

  const RONDES = [1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000];
  const km = RONDES.filter((v) => v * 1000 <= metresPour100px * 1.6).pop() || 1;

  // Largeur du trait, en pixels de l'image : mètres à représenter ÷ mètres par
  // pixel d'écran, puis multiplié par le facteur d'agrandissement de l'export.
  const parPixel = metresPour100px / 100;
  const l = (km * 1000 / parPixel) * (o.echelle ?? 2);

  g.save();
  carteBlanche(g, x, y - 22 * e, l + 24 * e, 30 * e, 4 * e);
  g.strokeStyle = "#0f2a4f";
  g.lineWidth = 2 * e;
  g.beginPath();
  g.moveTo(x + 12 * e, y - 4 * e);
  g.lineTo(x + 12 * e, y);
  g.lineTo(x + 12 * e + l, y);
  g.lineTo(x + 12 * e + l, y - 4 * e);
  g.stroke();
  g.fillStyle = "#0f2a4f";
  g.font = `700 ${Math.round(11 * e)}px ${POLICE}`;
  g.fillText(`${km} km`, x + 12 * e, y - 8 * e);
  g.restore();
}
function telecharger(canevas, nom) {
  return new Promise((resoudre, rejeter) => {
    canevas.toBlob((blob) => {
      if (!blob) return rejeter(new Error("Image vide — les tuiles ont peut-être été refusées."));
      const url = URL.createObjectURL(blob);
      const lien = document.createElement("a");
      lien.href = url;
      lien.download = nom;
      document.body.appendChild(lien);
      lien.click();
      document.body.removeChild(lien);
      URL.revokeObjectURL(url);
      resoudre();
    }, "image/png");
  });
}
