// Carte choroplèthe rendue en SVG à partir d'un fichier GeoJSON.
//
// Pourquoi du SVG plutôt qu'une librairie de cartographie : on n'affiche ici
// que des zones administratives coloriées (pas de fond de plan, pas de zoom).
// Le SVG suffit, évite une dépendance et un chargement de tuiles externes,
// et reste net à toutes les tailles.
//
// Props :
//   - geojson         : objet GeoJSON (FeatureCollection) déjà chargé
//   - valeurs         : { territoire_id : valeur } — sert à colorier
//   - couleurDe       : (valeur, territoire_id) => couleur de remplissage
//   - selection       : un territoire_id, ou un tableau d'identifiants, mis en
//                       évidence par un contour épais
//   - couleurBordure  : (territoire_id) => couleur du contour d'un territoire
//                       sélectionné ; permet de donner à chacun sa couleur
//   - onSelect        : (territoire_id) => void, au clic sur une zone
//   - libelleDe       : (territoire_id) => texte affiché au survol
//   - etiquetteDe     : (territoire_id) => texte écrit SUR la zone, ou null.
//                       Sert à nommer les territoires importants directement
//                       sur la carte, sans obliger à survoler.
//   - bulles          : { couleur, texteDe } pour passer en symboles
//                       proportionnels : les zones deviennent un fond neutre et
//                       chaque territoire reçoit un disque dont l'AIRE suit la
//                       valeur, avec le chiffre écrit dedans.
//                       À réserver aux quantités ABSOLUES (nombre de lits, de
//                       médecins). Une quantité relative — un taux, un ratio
//                       habitants/médecin — doit rester en aplats de couleur :
//                       un gros disque y signifierait « beaucoup de rapport »,
//                       ce qui ne veut rien dire.
//   - hauteur         : hauteur du cadre en pixels

import { useEffect, useMemo, useRef, useState } from "react";
import { Plus, Minus, Maximize2 } from "lucide-react";

const ZOOM_MAX = 14;          // agrandissement maximal
const PAS_BOUTON = 1.6;       // facteur appliqué par les boutons + et −

// Récupère l'identifiant de territoire, quel que soit le nom de la propriété.
function idDe(feature) {
  const p = feature.properties || {};
  const brut = p.territoire_id ?? p.TERRITOIRE_ID ?? null;
  return brut === null ? null : Number(brut);
}

// Transforme une géométrie (Polygon ou MultiPolygon) en liste d'anneaux.
function anneaux(geometry) {
  if (!geometry) return [];
  if (geometry.type === "Polygon") return geometry.coordinates;
  if (geometry.type === "MultiPolygon") return geometry.coordinates.flat();
  return [];
}

export default function CarteChoropleth({
  geojson,
  valeurs = {},
  couleurDe = () => "#d7dde6",
  selection = null,
  couleurBordure = null,
  onSelect = null,
  libelleDe = null,
  etiquetteDe = null,
  bulles = null,
  hauteur = 320,
}) {
  const [survol, setSurvol] = useState(null);

  // --- zoom et déplacement ---
  // On ne redessine pas les tracés : on déplace seulement la « fenêtre » de
  // lecture du SVG (son viewBox). C'est instantané, et le rendu reste net à
  // n'importe quel grossissement puisque tout est vectoriel.
  const svgRef = useRef(null);
  const [fenetre, setFenetre] = useState(null);
  const deplacement = useRef(null);
  // Mémorise si la carte a été FAIT GLISSER pendant le geste en cours. Ce drapeau
  // survit au relâchement du pointeur, car l'événement « click » n'est émis
  // qu'APRÈS « pointerup » : sans lui, on ne pourrait plus distinguer un
  // déplacement de carte d'un clic de sélection.
  const aGlisse = useRef(false);

  // On accepte indifféremment un identifiant seul ou une liste, pour que la
  // fiche (un territoire) et la comparaison (deux ou trois) partagent ce composant.
  const selections = selection == null
    ? []
    : (Array.isArray(selection) ? selection : [selection]).map(Number);

  // On calcule les tracés une seule fois par GeoJSON (opération coûteuse).
  const { traces, largeur, hauteurVue } = useMemo(() => {
    if (!geojson?.features?.length) return { traces: [], largeur: 100, hauteurVue: 100 };

    // 1) Emprise géographique (min/max des longitudes et latitudes).
    let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;
    geojson.features.forEach((f) =>
      anneaux(f.geometry).forEach((anneau) =>
        anneau.forEach(([lon, lat]) => {
          if (lon < minLon) minLon = lon;
          if (lon > maxLon) maxLon = lon;
          if (lat < minLat) minLat = lat;
          if (lat > maxLat) maxLat = lat;
        })
      )
    );

    // 2) Projection équirectangulaire. À cette latitude (~35°), on corrige le
    //    resserrement des méridiens par cos(latitude) pour éviter une carte
    //    horizontalement étirée.
    const latMoyenne = ((minLat + maxLat) / 2) * (Math.PI / 180);
    const corrX = Math.cos(latMoyenne);
    const largeurGeo = (maxLon - minLon) * corrX;
    const hauteurGeo = maxLat - minLat;

    const ECHELLE = 1000;                       // unités du repère SVG interne
    const largeurVue = ECHELLE;
    const hauteurVue = (hauteurGeo / largeurGeo) * ECHELLE;

    const projeter = ([lon, lat]) => [
      ((lon - minLon) * corrX / largeurGeo) * largeurVue,
      hauteurVue - ((lat - minLat) / hauteurGeo) * hauteurVue,   // y inversé en SVG
    ];

    const traces = geojson.features.map((f, i) => {
      const listeAnneaux = anneaux(f.geometry);

      // Point d'ancrage d'une étiquette : le centre du plus grand anneau.
      // On prend le plus grand parce qu'une commune peut avoir des îlots ;
      // écrire son nom sur un îlot minuscule serait illisible.
      let plusGrand = [], maxPoints = 0;
      listeAnneaux.forEach((a) => {
        if (a.length > maxPoints) { maxPoints = a.length; plusGrand = a; }
      });
      let centre = null;
      if (plusGrand.length) {
        const pts = plusGrand.map(projeter);
        const somme = pts.reduce((acc, [x, y]) => [acc[0] + x, acc[1] + y], [0, 0]);
        centre = [somme[0] / pts.length, somme[1] / pts.length];
      }

      return {
        cle: `${idDe(f) ?? "x"}-${i}`,
        territoireId: idDe(f),
        centre,
        taille: maxPoints,
        d: listeAnneaux
          .map((anneau) => {
            const points = anneau.map(projeter);
            if (!points.length) return "";
            return (
              "M" + points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join("L") + "Z"
            );
          })
          .join(" "),
      };
    });

    return { traces, largeur: largeurVue, hauteurVue };
  }, [geojson]);

  // Vue d'origine : le cadre complet. Recalculée si l'on change de fond de carte
  // (passage des provinces aux communes, par exemple).
  const fenetreInitiale = useMemo(
    () => ({ x: 0, y: 0, w: largeur, h: hauteurVue }),
    [largeur, hauteurVue]);

  useEffect(() => { setFenetre(fenetreInitiale); }, [fenetreInitiale]);

  const vue = fenetre || fenetreInitiale;

  // Empêche de sortir du cadre : on ne peut ni dézoomer au-delà de la carte
  // entière, ni faire glisser le territoire hors de vue.
  function borner(f) {
    const w = Math.min(Math.max(f.w, largeur / ZOOM_MAX), largeur);
    const h = w * (hauteurVue / largeur);
    return {
      w, h,
      x: Math.min(Math.max(f.x, 0), largeur - w),
      y: Math.min(Math.max(f.y, 0), hauteurVue - h),
    };
  }

  // Zoom centré sur un point : ce point reste sous le curseur après l'opération.
  function zoomer(facteur, ancrage) {
    const fx = ancrage ? ancrage.fx : 0.5;
    const fy = ancrage ? ancrage.fy : 0.5;
    const px = vue.x + fx * vue.w;
    const py = vue.y + fy * vue.h;
    const w = vue.w * facteur;
    const h = vue.h * facteur;
    setFenetre(borner({ x: px - fx * w, y: py - fy * h, w, h }));
  }

  function ancrageDepuis(e) {
    const r = svgRef.current?.getBoundingClientRect();
    if (!r) return null;
    return { fx: (e.clientX - r.left) / r.width, fy: (e.clientY - r.top) / r.height };
  }

  // La molette doit zoomer sans faire défiler la page : cela impose un écouteur
  // non passif, que React n'installe pas via onWheel.
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    function surMolette(e) {
      e.preventDefault();
      zoomer(e.deltaY > 0 ? 1.15 : 1 / 1.15, ancrageDepuis(e));
    }
    el.addEventListener("wheel", surMolette, { passive: false });
    return () => el.removeEventListener("wheel", surMolette);
  });

  function debutDeplacement(e) {
    aGlisse.current = false;
    deplacement.current = { clientX: e.clientX, clientY: e.clientY, x: vue.x, y: vue.y };
  }
  function pendantDeplacement(e) {
    const d = deplacement.current;
    if (!d) return;
    const r = svgRef.current.getBoundingClientRect();
    const dxEcran = e.clientX - d.clientX;
    const dyEcran = e.clientY - d.clientY;
    // Seuil de 3 pixels : un clic n'est jamais parfaitement immobile, et une
    // micro-secousse de souris ne doit pas passer pour un déplacement.
    if (Math.abs(dxEcran) > 3 || Math.abs(dyEcran) > 3) aGlisse.current = true;
    if (!aGlisse.current) return;
    setFenetre(borner({
      ...vue,
      x: d.x - dxEcran * (vue.w / r.width),
      y: d.y - dyEcran * (vue.h / r.height),
    }));
  }
  function finDeplacement() { deplacement.current = null; }

  const zoomActif = vue.w < largeur - 0.5;

  // Tout ce qui est dessiné en SVG grossit avec le zoom. Pour que les contours
  // et les noms gardent la même épaisseur à l'écran, on les divise par le
  // facteur d'agrandissement courant.
  const echelle = vue.w / largeur;

  if (!geojson) {
    return (
      <div className="flex items-center justify-center text-t3 text-sm bg-bg rounded-2xl"
           style={{ height: hauteur }}>
        Chargement de la carte…
      </div>
    );
  }

  const libelleSurvol = survol !== null && libelleDe ? libelleDe(survol) : null;

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        viewBox={`${vue.x} ${vue.y} ${vue.w} ${vue.h}`}
        style={{
          height: hauteur, width: "100%",
          cursor: deplacement.current ? "grabbing" : zoomActif ? "grab" : "default",
          touchAction: "none",
        }}
        className="rounded-2xl bg-bg select-none"
        role="img"
        aria-label="Carte des territoires"
        /* Pas de setPointerCapture : la capture redirige tous les événements
           vers le <svg>, si bien que le « click » n'atteignait plus les zones
           et que la sélection ne fonctionnait pas. */
        onPointerDown={debutDeplacement}
        onPointerMove={pendantDeplacement}
        onPointerUp={finDeplacement}
        onPointerLeave={finDeplacement}
        onDoubleClick={(e) => zoomer(1 / 2, ancrageDepuis(e))}
      >
        {/* Les territoires sélectionnés sont dessinés en dernier : en SVG le
            dernier tracé passe au-dessus, sinon un voisin recouvrirait leur
            contour épais et la mise en évidence deviendrait invisible. */}
        {[...traces]
          .sort((a, b) => (selections.includes(a.territoireId) ? 1 : 0)
                        - (selections.includes(b.territoireId) ? 1 : 0))
          .map((t) => {
          const estSelection = selections.includes(t.territoireId);
          const estSurvol = survol === t.territoireId;
          const bordure = estSelection
            ? (couleurBordure ? couleurBordure(t.territoireId) : "#0a2540")
            : "#ffffff";
          return (
            <path
              key={t.cle}
              d={t.d}
              fill={bulles ? "#e8edf4" : couleurDe(valeurs[t.territoireId], t.territoireId)}
              stroke={bordure}
              strokeWidth={(estSelection ? 7 : estSurvol ? 4 : 1.5) * echelle}
              strokeLinejoin="round"
              opacity={estSurvol && !estSelection ? 0.85 : 1}
              style={{ cursor: onSelect ? "pointer" : "default", transition: "opacity .15s" }}
              onMouseEnter={() => setSurvol(t.territoireId)}
              onMouseLeave={() => setSurvol(null)}
              onClick={() => {
                // Un glissement de carte ne doit pas être pris pour un clic
                // de sélection : on ignore le clic si la vue a bougé.
                if (aGlisse.current) return;
                if (onSelect && t.territoireId != null) onSelect(t.territoireId);
              }}
            />
          );
        })}

        {/* Symboles proportionnels. L'AIRE du disque suit la valeur, donc son
            rayon suit la RACINE de la valeur : l'œil compare des surfaces, et
            un rayon proportionnel exagérerait les écarts au carré.
            Les plus gros sont dessinés d'abord pour que les petits, posés
            par-dessus, restent visibles. */}
        {bulles && (() => {
          const parTerritoire = {};
          traces.forEach((t) => {
            if (!t.centre || t.territoireId == null) return;
            const v = valeurs[t.territoireId];
            if (v === null || v === undefined || !v) return;
            const p = parTerritoire[t.territoireId];
            if (!p || t.taille > p.taille) parTerritoire[t.territoireId] = t;
          });
          const liste = Object.values(parTerritoire);
          const max = Math.max(...liste.map((t) => valeurs[t.territoireId]), 1);
          const rayon = (v) => (largeur / 60) * (1 + 2.4 * Math.sqrt(v / max));
          return liste
            .sort((a, b) => valeurs[b.territoireId] - valeurs[a.territoireId])
            .map((t) => {
              const v = valeurs[t.territoireId];
              const r = rayon(v);
              const texte = bulles.texteDe ? bulles.texteDe(v, t.territoireId) : String(v);
              return (
                <g key={`b-${t.territoireId}`}
                   onMouseEnter={() => setSurvol(t.territoireId)}
                   onMouseLeave={() => setSurvol(null)}
                   onClick={() => {
                     if (aGlisse.current) return;
                     if (onSelect && t.territoireId != null) onSelect(t.territoireId);
                   }}
                   style={{ cursor: onSelect ? "pointer" : "default" }}>
                  <circle cx={t.centre[0]} cy={t.centre[1]} r={r}
                          fill={bulles.couleur ? bulles.couleur(v, t.territoireId) : "#f5a623"}
                          fillOpacity={survol === t.territoireId ? 1 : 0.9}
                          stroke="#ffffff" strokeWidth={2.5 * echelle} />
                  <text x={t.centre[0]} y={t.centre[1]}
                        textAnchor="middle" dominantBaseline="central"
                        style={{
                          fontSize: Math.min(r * 0.62, 26), fontWeight: 800, fill: "#0a2540",
                          pointerEvents: "none",
                        }}>
                    {texte}
                  </text>
                </g>
              );
            });
        })()}

        {/* Étiquettes en dernier, pour qu'aucun tracé ne les recouvre.
            Le liseré blanc (paint-order) garde le texte lisible quelle que
            soit la couleur de la zone en dessous. */}
        {/* Un même territoire peut être découpé en plusieurs tracés : la commune
            de Tanger apparaît sous la forme de ses quatre arrondissements, qui
            portent tous territoire_id 34. Sans ce regroupement, son étiquette
            serait écrite quatre fois, les unes par-dessus les autres. On garde
            le plus grand tracé, celui où le texte a la place de tenir. */}
        {etiquetteDe && Object.values(
          traces
            .filter((t) => t.centre && etiquetteDe(t.territoireId))
            .reduce((parTerritoire, t) => {
              const precedent = parTerritoire[t.territoireId];
              if (!precedent || t.taille > precedent.taille) parTerritoire[t.territoireId] = t;
              return parTerritoire;
            }, {})
        )
          .map((t) => (
            <text key={`et-${t.cle}`}
                  x={t.centre[0]} y={t.centre[1]}
                  textAnchor="middle" dominantBaseline="middle"
                  style={{
                    fontSize: 22 * echelle, fontWeight: 700, fill: "#0a2540",
                    stroke: "#ffffff", strokeWidth: 5 * echelle, paintOrder: "stroke",
                    pointerEvents: "none",
                  }}>
              {etiquetteDe(t.territoireId)}
            </text>
          ))}
      </svg>

      {libelleSurvol && (
        <div className="absolute top-2 left-2 bg-navy text-white text-xs font-semibold
                        px-3 py-1.5 rounded-lg pointer-events-none shadow-lg">
          {libelleSurvol}
        </div>
      )}

      {/* Commandes de zoom */}
      <div className="absolute top-2 right-2 flex flex-col gap-1">
        {[
          { Icone: Plus, titre: "Agrandir", action: () => zoomer(1 / PAS_BOUTON), actif: true },
          { Icone: Minus, titre: "Réduire", action: () => zoomer(PAS_BOUTON), actif: zoomActif },
          { Icone: Maximize2, titre: "Vue d'ensemble",
            action: () => setFenetre(fenetreInitiale), actif: zoomActif },
        ].map(({ Icone, titre, action, actif }) => (
          <button key={titre} onClick={action} title={titre} aria-label={titre}
            disabled={!actif}
            className={`w-8 h-8 rounded-lg bg-surface border border-line flex items-center
                        justify-center shadow-sm transition-colors ${
              actif ? "text-navy hover:bg-bg" : "text-t3 opacity-40 cursor-not-allowed"}`}>
            <Icone size={15} />
          </button>
        ))}
      </div>

      {zoomActif && (
        <div className="absolute bottom-2 left-2 text-[10px] text-t2 bg-surface/90
                        px-2 py-1 rounded-md pointer-events-none">
          Glissez pour déplacer · double-clic pour reculer
        </div>
      )}
    </div>
  );
}
