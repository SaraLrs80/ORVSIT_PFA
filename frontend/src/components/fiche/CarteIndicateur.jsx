// Carte choroplèthe d'UN indicateur, sur fond de plan Leaflet.
//
// Pourquoi un fond de plan ici alors que la page Comparer s'en passe : la fiche
// sert à situer un territoire, et un aplat de couleur flottant sans repère ne
// situe rien. Le fond de plan donne le littoral, les villes, les reliefs.
//
// Un seul indicateur à la fois, volontairement. Superposer deux aplats n'apporte
// rien : celui du dessus masque l'autre, et jouer sur l'opacité mêle les teintes
// en une troisième qui ne correspond à aucune valeur.

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { classer, classeDe, teintes, encreSur, nb, dec, court } from "./outils";

// Cadre du masque : le bassin occidental de la Méditerranée et le Maghreb.
// Volontairement fini plutôt que planétaire — un rectangle de -180 à 180
// produit, une fois projeté à fort grossissement, un tracé de plusieurs
// dizaines de millions de pixels que les navigateurs rendent mal. Ce cadre
// couvre largement ce qui reste visible au zoom minimal fixé plus bas.
const CADRE = [[-25, 15], [15, 15], [15, 48], [-25, 48], [-25, 15]];
const ZOOM_MIN = 6;   // en deçà, on sortirait du cadre du masque

/**
 * Masque troué : un polygone qui recouvre le monde, percé à la forme exacte
 * des territoires affichés.
 *
 * Pourquoi ce détour plutôt qu'un fond de plan sans frontières : aucun fond de
 * tuiles ne propose « le Maroc sans ses voisins ». Les frontières, l'Espagne et
 * la mer font partie de l'image livrée. La seule façon de ne montrer que la
 * région est donc de recouvrir tout le reste.
 *
 * On perce autant de trous qu'il y a d'anneaux de territoire. Les provinces se
 * touchent sans se chevaucher : la règle de remplissage « evenodd » compte les
 * traversées, un point situé dans un trou en compte deux depuis l'extérieur et
 * reste donc transparent. L'union des trous dessine exactement la région, sans
 * qu'on ait eu à la calculer.
 */
function masqueDe(geojson) {
  const trous = [];
  (geojson?.features || []).forEach((f) => {
    const g = f.geometry;
    if (!g) return;
    if (g.type === "Polygon") trous.push(...g.coordinates);
    else if (g.type === "MultiPolygon") g.coordinates.forEach((p) => trous.push(...p));
  });
  if (!trous.length) return null;
  return {
    type: "Feature",
    properties: {},
    geometry: { type: "Polygon", coordinates: [CADRE, ...trous] },
  };
}

const FONDS = {
  Clair: ["https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", "© OpenStreetMap, © CARTO"],
  Sombre: ["https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", "© OpenStreetMap, © CARTO"],
  Satellite: [
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "Imagerie © Esri, Maxar",
  ],
};

// Seuls les fonds vectoriels dessinent les limites administratives : ce sont
// eux, et eux seuls, qui posent la question du tracé de la frontière sud.
// L'imagerie satellite ne trace rien — elle photographie. La masquer lui ferait
// perdre le détroit, la mer et le relief sans rien résoudre.
const FONDS_AVEC_FRONTIERES = new Set(["Clair", "Sombre"]);

export default function CarteIndicateur({
  geojson,            // FeatureCollection déjà restreinte aux pairs
  serie,              // { territoire_id : valeur }
  secteur,            // pilote la rampe de couleurs
  unite,
  territoireOuvert,
  // Comparaison : { territoire_id : couleur }. Quand cette table est fournie,
  // la carte ne représente plus un indicateur mais une SÉLECTION — chaque
  // territoire retenu porte sa propre couleur, les autres restent en fond
  // neutre. Deux lectures différentes, un seul composant.
  selection = null,
  nomDe,              // (id) => nom lisible
  onSelect,
  methode = "Quantiles",
  classes = 5,
  opacite = 0.88,
  fond = "Clair",
  etiquettes = false,
  // Ne montrer que les territoires affichés, en recouvrant tout le reste.
  // Demande de l'encadrante : une carte thématique ne doit pas laisser voir
  // les frontières des pays voisins, qui n'ont rien à y faire.
  masquer = true,
  // Appelée une fois avec l'instance Leaflet, pour que l'export puisse projeter.
  surPret = null,
}) {
  const conteneur = useRef(null);
  const carte = useRef(null);
  const couche = useRef(null);
  const masque = useRef(null);
  const fondRef = useRef(null);
  const marqueurs = useRef([]);
  // Les gestionnaires de clic sont recréés à chaque rendu ; on les lit depuis
  // une référence pour que la couche Leaflet, elle, ne soit pas reconstruite.
  const rappel = useRef(onSelect);
  rappel.current = onSelect;

  /* ---------- création de la carte, une seule fois ---------- */
  useEffect(() => {
    if (carte.current || !conteneur.current) return;
    carte.current = L.map(conteneur.current, {
      zoomControl: false,
      attributionControl: true,
      minZoom: ZOOM_MIN,
    }).setView([35.2, -5.4], 7.4);

    L.control.zoom({ position: "bottomright" }).addTo(carte.current);
    L.control.scale({ imperial: false, position: "bottomleft" }).addTo(carte.current);

    // La carte occupe désormais la hauteur que lui laisse sa colonne, laquelle
    // n'est connue qu'une fois la grille posée. Sans cette surveillance,
    // Leaflet garde la taille mesurée au montage et n'affiche qu'une partie
    // des tuiles — le fameux damier gris.
    const observateur = new ResizeObserver(() => carte.current?.invalidateSize());
    observateur.observe(conteneur.current);

    return () => {
      observateur.disconnect();
      carte.current?.remove();
      carte.current = null;
    };
  }, []);

  // La carte est remise à qui la demande — l'export projette lui-même ses
  // coordonnées plutôt que de rastériser le DOM.
  //
  // À chaque rendu, et non une seule fois à la création : React monte puis
  // remonte les composants en développement, et la carte du premier montage est
  // détruite. Une transmission unique laissait alors le destinataire avec une
  // référence morte, ou vide — et l'export répondait « la carte doit être
  // affichée » alors qu'elle l'était.
  useEffect(() => {
    if (carte.current) surPret?.(carte.current);
  });

  /* ---------- fond de plan ---------- */
  useEffect(() => {
    if (!carte.current) return;
    if (fondRef.current) carte.current.removeLayer(fondRef.current);
    const [url, attribution] = FONDS[fond] || FONDS.Clair;
    // crossOrigin : sans lui, les tuiles — servies par CARTO et Esri, donc par
    // un autre domaine — « teintent » le canevas, et toute tentative de le
    // convertir en image échoue. L'export PNG rendrait une carte blanche, sans
    // la moindre erreur pour l'expliquer. Les deux fournisseurs envoient les
    // en-têtes CORS nécessaires, ce mot suffit donc à débloquer l'export.
    fondRef.current = L.tileLayer(url, {
      maxZoom: 18,
      attribution,
      crossOrigin: "anonymous",
    }).addTo(carte.current);
  }, [fond]);

  /* ---------- tracés et couleurs ---------- */
  const vs = Object.values(serie || {});
  const bornes = classer(vs, classes, methode);
  const palette = teintes(bornes.length + 1, secteur);
  const d = dec(vs);

  useEffect(() => {
    if (!carte.current || !geojson) return;

    if (couche.current) carte.current.removeLayer(couche.current);
    if (masque.current) carte.current.removeLayer(masque.current);
    marqueurs.current.forEach((m) => carte.current.removeLayer(m));
    marqueurs.current = [];

    // Le masque est posé AVANT les territoires : dans un même volet, Leaflet
    // empile dans l'ordre d'ajout. Posé après, il recouvrirait les aplats
    // qu'il est censé mettre en valeur.
    if (masquer && FONDS_AVEC_FRONTIERES.has(fond)) {
      const m = masqueDe(geojson);
      if (m) {
        // Le masque prend la teinte du fond choisi : un pourtour clair autour
        // d'une région posée sur un fond sombre trancherait bêtement.
        const teinte = fond === "Sombre" ? "#12192b" : "#f4f6fa";
        masque.current = L.geoJSON(m, {
          interactive: false,
          style: {
            fillColor: teinte,
            fillOpacity: 1,
            fillRule: "evenodd",
            weight: 0,
            color: teinte,
          },
        }).addTo(carte.current);
      }
    }

    const aSerie = vs.length > 0;

    couche.current = L.geoJSON(geojson, {
      style: (x) => {
        const id = x.properties.id;
        if (selection) {
          const c = selection[id];
          return {
            fillColor: c || "#e3e8f0",
            fillOpacity: c ? 0.85 : 0.45,
            color: "#fff",
            weight: c ? 3 : 1,
          };
        }
        const v = serie?.[id];
        return {
          fillColor: !aSerie ? "#eef2f7"
            : v == null ? "#dde3ec"            // absence de donnée : gris, jamais zéro
            : palette[classeDe(v, bornes)],
          fillOpacity: aSerie ? opacite : 0.55,
          color: String(id) === String(territoireOuvert) ? "#f0a92c" : "#fff",
          weight: String(id) === String(territoireOuvert) ? 3 : 1,
        };
      },
      onEachFeature: (x, l) => {
        const id = x.properties.id;
        const v = serie?.[id];
        const invite = selection
          ? (selection[id] ? "cliquez pour retirer de la comparaison"
                           : "cliquez pour ajouter à la comparaison")
          : "cliquez pour ouvrir cette fiche";
        l.bindTooltip(
          `<b>${court(nomDe(id) || id)}</b><br>${
            !aSerie ? "" : v == null ? "donnée non disponible" : `${nb(v, d)} ${unite || ""}`
          }<br><span style="opacity:.7">${invite}</span>`,
          { sticky: true }
        );
        l.on("click", () => rappel.current?.(id));
      },
    }).addTo(carte.current);

    // Étiquettes de valeur. Elles valent aussi au niveau communal : la carte
    // n'affiche que les communes de la province ouverte, soit 5 à 36 — et non
    // les 146 de la région. On réduit seulement leur taille quand elles sont
    // nombreuses. En mode sélection, il n'y a pas d'indicateur à étiqueter.
    if (etiquettes && aSerie && !selection) {
      // Un territoire peut être livré en plusieurs morceaux par une source
      // future ; on ne garde que le plus grand, sinon le nombre s'écrirait
      // plusieurs fois au même endroit.
      const retenu = {};
      couche.current.eachLayer((l) => {
        const id = l.feature.properties.id;
        if (serie?.[id] == null) return;
        const b = l.getBounds();
        const aire = Math.abs(b.getEast() - b.getWest()) * Math.abs(b.getNorth() - b.getSouth());
        if (!retenu[id] || aire > retenu[id].aire) retenu[id] = { l, aire };
      });
      Object.keys(retenu).forEach((id) => {
        const v = serie[id];
        const fondCase = palette[classeDe(v, bornes)];
        const encre = encreSur(fondCase);
        const ombre = encre === "#ffffff" ? "rgba(0,0,0,.8)" : "rgba(255,255,255,.9)";
        marqueurs.current.push(
          L.marker(retenu[id].l.getBounds().getCenter(), {
            interactive: false,
            icon: L.divIcon({
              className: "",
              html: `<div style="font:600 ${
                geojson.features.length > 20 ? "9.5px" : "11px"
              } Inter,sans-serif;color:${encre};text-shadow:0 1px 3px ${ombre};white-space:nowrap;
                transform:translate(-50%,-50%)">${nb(v, d)}</div>`,
            }),
          }).addTo(carte.current)
        );
      });
    }

    if (couche.current.getLayers().length)
      carte.current.fitBounds(couche.current.getBounds(), { padding: [16, 16] });
  }, [geojson, serie, secteur, territoireOuvert, selection,
      methode, classes, opacite, etiquettes, unite, masquer, fond]);

  // La carte occupe toute la hauteur que son parent lui laisse. C'est ce qui
  // permet de l'aligner exactement sur le catalogue et sur les réglages : une
  // hauteur fixe laissait sous elle une bande blanche dans la carte-conteneur.
  //
  // Elle ne porte plus de légende flottante : la légende vit dans la colonne
  // de réglages, où elle ne mange pas le territoire et où elle n'est écrite
  // qu'une fois.
  return <div ref={conteneur} className="h-full w-full rounded-[18px] overflow-hidden z-0" />;
}

export { FONDS };
