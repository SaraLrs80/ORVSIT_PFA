// Explorer un indicateur — page entièrement pilotée par le catalogue.
//
// Aucun nom de table, aucun libellé d'indicateur, aucune source n'est écrit
// dans ce fichier : tout vient de GET /explorer/{theme}/catalogue. Le jour où
// un thème est ajouté côté backend, cette page l'affiche sans être modifiée.
//
// Deux modes de lecture, distingués par `variante.mode` :
//   - "long"  : un indicateur déjà calculé, une valeur par territoire.
//               Exemple : habitants par médecin. Pas de filtre, une carte.
//   - "brut…" : une table d'objets réels (établissements, effectifs). On reçoit
//               les lignes brutes et on filtre dans le navigateur : la plus
//               grosse table fait 958 lignes, un aller-retour réseau par case
//               cochée serait absurde.

import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Loader2, AlertTriangle, ListFilter, BarChart3, Info, MapPin, Layers,
} from "lucide-react";
import DashboardLayout from "../../components/DashboardLayout";
import SelecteurTerritoire from "../../components/SelecteurTerritoire";
import CarteChoropleth from "../../components/CarteChoropleth";
import BoutonExport from "../../components/BoutonExport";
import { getCatalogue, getIndicateur, getJeu } from "../../api/explorer";

// Palette de performance : du meilleur au moins bon. Elle ne change jamais de
// sens — c'est la valeur qui est projetée dessus, pas l'inverse.
const ECHELLE = ["#0d8577", "#12a594", "#f5a623", "#f2865b", "#d9534a"];
const NEUTRE = "#dfe4ec";

const PALMARES = 12;      // longueur du classement avant dépliage
const SEUIL_ETIQUETTES = 20; // au-delà, plus aucun nom écrit sur la carte

// --------------------------------------------------------------------- outils

const nb = (v, dec = 0) =>
  v === null || v === undefined
    ? "—"
    : Number(v).toLocaleString("fr-FR", { minimumFractionDigits: dec, maximumFractionDigits: dec });

/**
 * Nombre de décimales à afficher, déduit de l'AMPLITUDE réelle des valeurs.
 *
 * Sans cela, un taux de privation qui va de 0,00 % à 0,94 % s'arrondit à « 0 »
 * partout : la carte est colorée, le classement est ordonné, et pourtant chaque
 * chiffre affiché vaut zéro. C'était le cas de « privation — mortalité
 * infantile », dont l'étendue tient sous 1 point.
 */
function decimales(valeurs, unite) {
  const vs = Object.values(valeurs).filter((v) => v !== null && v !== undefined && !Number.isNaN(v));
  if (!vs.length) return 0;
  const etendue = Math.max(...vs) - Math.min(...vs);
  const max = Math.max(...vs.map(Math.abs));
  if (max < 1 || etendue < 1) return 2;
  if (max < 20 || etendue < 10) return 1;
  // Un taux publié avec une décimale ne doit pas la perdre à l'affichage : le
  // HCP écrit « 21,8 % », pas « 22 % », et l'écart de 0,8 point compte quand on
  // classe 146 communes.
  return unite === "%" ? 1 : 0;
}

/** « Commune d'Oued Laou » → « Oued Laou ». Les cartes n'ont pas la place. */
function court(nom) {
  return (nom || "")
    .replace(/^(Commune|Municipalité|Préfecture|Province)\s+(d'|de\s|du\s|des\s)?/i, "")
    .replace(/\s*\(Mun\.\)$/i, "")
    .trim();
}

/**
 * Découpe les valeurs en classes de couleur.
 *
 * Pourquoi pas une échelle linéaire : les comptages territoriaux sont très
 * dissymétriques. Tanger porte 28 établissements, la plupart des communes en
 * portent 1. Réparti linéairement, tout ce qui vaut 1 à 5 tombe dans la même
 * tranche basse et la carte devient uniformément rouge — elle ne distingue plus
 * rien, alors que l'écart entre 1 et 5 intéresse le décideur.
 *
 * On coupe donc aux quantiles, ce qui remplit chaque classe à peu près
 * également. Deux garanties tiennent malgré ce changement :
 *   - une coupure est toujours ramenée sur une valeur réellement observée, donc
 *     deux territoires à ÉGALITÉ ne peuvent jamais être de couleurs différentes ;
 *   - les bornes chiffrées de chaque classe sont écrites dans la légende, donc
 *     le lecteur sait ce que chaque couleur veut dire.
 */
function classer(valeurs, k = 5) {
  const vs = Object.values(valeurs)
    .filter((v) => v !== null && v !== undefined && !Number.isNaN(v))
    .sort((a, b) => a - b);
  if (!vs.length) return [];

  const distinctes = [...new Set(vs)];
  if (distinctes.length <= k) return distinctes.map((v) => [v, v]);

  // Coupures aux quantiles des observations.
  const candidats = new Set([distinctes[0]]);
  for (let i = 1; i < k; i++) candidats.add(vs[Math.floor((i * vs.length) / k)]);

  // Distribution très concentrée : sur les 80 communes qui portent au moins un
  // établissement RAMED, 70 n'en portent qu'un seul. Les quatre coupures de
  // quantile tombent alors toutes sur la valeur 1 et il ne reste qu'une classe,
  // c'est-à-dire une carte d'une seule couleur. Dans ce cas on découpe les
  // valeurs DISTINCTES plutôt que les observations : les paliers redeviennent
  // lisibles, et deux ex aequo restent par construction dans la même classe.
  if (candidats.size < k) {
    for (let i = 1; i < k; i++) candidats.add(distinctes[Math.floor((i * distinctes.length) / k)]);
  }

  let debuts = [...candidats].sort((a, b) => a - b);
  if (debuts.length > k) {
    debuts = [...new Set(Array.from({ length: k }, (_, i) =>
      debuts[Math.round((i * (debuts.length - 1)) / (k - 1))]))];
  }

  return debuts.map((d, i) => {
    const suivant = debuts[i + 1];
    const max = suivant === undefined
      ? distinctes[distinctes.length - 1]
      : distinctes[distinctes.indexOf(suivant) - 1];
    return [d, max];
  });
}

/** Les couleurs des classes, dans l'ordre croissant des valeurs. */
function palette(nombreDeClasses, sensInverse) {
  const n = Math.max(nombreDeClasses, 1);
  const base = n >= ECHELLE.length
    ? ECHELLE
    : Array.from({ length: n }, (_, i) =>
        ECHELLE[Math.round((i * (ECHELLE.length - 1)) / Math.max(n - 1, 1))]);
  // sensInverse : petit = bon, donc la première classe reçoit la couleur la
  // plus favorable. Pour un comptage c'est l'inverse.
  return sensInverse ? base : base.slice().reverse();
}

function couleurDeClasse(v, bornes, couleurs) {
  if (v === null || v === undefined || Number.isNaN(v)) return NEUTRE;
  for (let i = 0; i < bornes.length; i++) {
    if (v >= bornes[i][0] && v <= bornes[i][1]) return couleurs[i];
  }
  return v < bornes[0][0] ? couleurs[0] : couleurs[couleurs.length - 1];
}

/** Une ligne passe-t-elle les filtres ? `exclure` sert aux facettes : une
 *  colonne ne se filtre jamais elle-même, sinon cocher une valeur ferait
 *  disparaître toutes les autres options de la même liste. */
function passe(ligne, filtres, exclure) {
  for (const [col, valeurs] of Object.entries(filtres)) {
    if (col === exclure || !valeurs.size) continue;
    if (!valeurs.has(String(ligne[col]))) return false;
  }
  return true;
}

/** Comptes par modalité d'une colonne, triés du plus fréquent au moins. */
function agreger(lignes, colonne, mesure) {
  const m = new Map();
  lignes.forEach((l) => {
    const v = l[colonne];
    if (v === null || v === undefined || v === "") return;
    const poids = mesure ? Number(l[mesure]) || 0 : 1;
    m.set(String(v), (m.get(String(v)) || 0) + poids);
  });
  return [...m.entries()].sort((a, b) => b[1] - a[1]);
}

// Colonnes géographiques : elles restent filtrables, mais ne servent pas à
// résumer le jeu dans les indicateurs de tête (« quel type est le plus
// fréquent ? » n'a pas de sens si la réponse est « Tanger-Assilah »).
const COLONNES_GEO = new Set(["Province", "Territoire", "CS", "C. sanitaire", "Circ. sanitaire"]);

// ============================================================================

export default function ExplorerPage() {
  // Le thème est porté par l'URL : /dashboard/explorer/health. Ainsi chaque
  // thème a son adresse, partageable et mise en favori, et le bouton Retour du
  // navigateur fait ce que l'utilisateur attend.
  const { theme: themeUrl } = useParams();
  const THEME = themeUrl || "health";

  const [catalogue, setCatalogue] = useState(null);
  const [erreur, setErreur] = useState(null);

  const [cleAngle, setCleAngle] = useState(null);
  const [cleVariante, setCleVariante] = useState(null);
  const [ventilation, setVentilation] = useState({});

  const [donnees, setDonnees] = useState(null);
  const [chargement, setChargement] = useState(false);

  const [filtres, setFiltres] = useState({});
  const [recherches, setRecherches] = useState({});
  const [onglet, setOnglet] = useState("filtres");
  const [toutLeClassement, setToutLeClassement] = useState(false);

  const [geoProvinces, setGeoProvinces] = useState(null);
  const [geoCommunes, setGeoCommunes] = useState(null);

  // --- chargements initiaux -------------------------------------------------
  useEffect(() => {
    setCatalogue(null);
    setDonnees(null);
    setFiltres({});
    setRecherches({});
    getCatalogue(THEME)
      .then((d) => {
        setCatalogue(d);
        const premier = d.angles[0];
        setCleAngle(premier?.cle ?? null);
        setCleVariante(premier?.variantes[0]?.cle ?? null);
      })
      .catch((e) => setErreur(e?.response?.data?.detail || e.message));
    fetch("/geo/provinces.geojson").then((r) => r.json()).then(setGeoProvinces).catch(() => {});
    fetch("/geo/communes.geojson").then((r) => r.json()).then(setGeoCommunes).catch(() => {});
  }, [THEME]);

  const angle = catalogue?.angles.find((a) => a.cle === cleAngle) || null;
  const variante = angle?.variantes.find((v) => v.cle === cleVariante) || null;

  // --- chargement de la variante active -------------------------------------
  useEffect(() => {
    if (!variante) return;
    let annule = false;
    setChargement(true);
    setErreur(null);

    const promesse = variante.mode === "long"
      ? getIndicateur(THEME, variante.cle, ventilation)
      : getJeu(THEME, variante.table);

    promesse
      .then((d) => { if (!annule) { setDonnees(d); setChargement(false); } })
      .catch((e) => {
        if (annule) return;
        setErreur(e?.response?.data?.detail || e.message);
        setDonnees(null);
        setChargement(false);
      });

    return () => { annule = true; };
  }, [variante?.cle, variante?.mode, variante?.table, JSON.stringify(ventilation)]);

  // Changer d'angle remet tout à zéro : les filtres d'un jeu n'ont aucun sens
  // dans un autre, et les garder produirait une page vide inexplicable.
  function choisirAngle(cle) {
    const a = catalogue.angles.find((x) => x.cle === cle);
    setCleAngle(cle);
    setCleVariante(a?.variantes[0]?.cle ?? null);
    setFiltres({});
    setRecherches({});
    setVentilation({});
    setToutLeClassement(false);
    setDonnees(null);
  }

  function choisirVariante(cle) {
    setCleVariante(cle);
    setFiltres({});
    setRecherches({});
    setVentilation({});
    setToutLeClassement(false);
    setDonnees(null);
  }

  function basculer(col, val) {
    setFiltres((prec) => {
      const suivant = { ...prec };
      const ens = new Set(suivant[col] || []);
      ens.has(val) ? ens.delete(val) : ens.add(val);
      if (ens.size) suivant[col] = ens; else delete suivant[col];
      return suivant;
    });
  }

  const nbFiltres = Object.values(filtres).reduce((s, v) => s + v.size, 0);

  // --- préparation des données affichées ------------------------------------
  const vue = useMemo(() => {
    if (!donnees || !variante) return null;
    const estIndicateur = variante.mode === "long";

    if (estIndicateur) {
      // Les valeurs sont converties en LIGNES, avec leur province et leur nom de
      // territoire comme colonnes. Tout le mécanisme déjà écrit pour les jeux
      // bruts — facettes, recherche, tableau de détail, export — fonctionne
      // alors sans une ligne de plus. Filtrer 146 communes à la main dans un
      // classement était le seul vrai manque de ce mode.
      const toutes = (donnees.valeurs || []).map((v) => ({
        territoire_id: v.territoire_id,
        Territoire: v.nom,
        Province: v.province || "—",
        Valeur: v.valeur,
      }));
      const retenues = toutes.filter((l) => passe(l, filtres));

      const noms = {};
      const valeurs = {};
      toutes.forEach((l) => { noms[l.territoire_id] = l.Territoire; });
      retenues.forEach((l) => { if (l.Valeur !== null) valeurs[l.territoire_id] = l.Valeur; });

      // « Territoire » ne devient filtrable qu'au niveau commune : au niveau
      // province il répéterait exactement la colonne « Province ».
      const dims = donnees.niveau === "commune" ? ["Province", "Territoire"] : ["Province"];

      return {
        estIndicateur: true,
        niveau: donnees.niveau,
        noms,
        valeurs,
        unite: donnees.unite || variante.unite,
        sensInverse: donnees.sens === "bas_mieux",
        lignes: retenues,
        toutes,
        dimensions: dims,
        colonnes: ["Territoire", "Province", "Valeur"],
        mesure: null,          // les facettes comptent des territoires, pas des taux
        total: null,
      };
    }

    const toutes = donnees.lignes || [];
    const retenues = toutes.filter((l) => passe(l, filtres));
    const mesure = donnees.mesure;

    const noms = {};
    const valeurs = {};
    toutes.forEach((l) => { if (l.territoire_id != null) noms[l.territoire_id] = l.Territoire; });
    retenues.forEach((l) => {
      const id = l.territoire_id;
      if (id == null) return;
      valeurs[id] = (valeurs[id] || 0) + (mesure ? Number(l[mesure]) || 0 : 1);
    });
    // Absence VÉRIFIÉE : on écrit zéro, pas « non renseigné ». Un territoire dont
    // on sait qu'il ne possède rien n'est pas un territoire dont on ignore tout.
    (donnees.absences_confirmees || []).forEach((a) => {
      noms[a.territoire_id] = a.nom;
      if (valeurs[a.territoire_id] === undefined) valeurs[a.territoire_id] = 0;
    });

    const total = mesure
      ? retenues.reduce((s, l) => s + (Number(l[mesure]) || 0), 0)
      : retenues.length;

    return {
      estIndicateur: false,
      niveau: donnees.niveau,
      noms,
      valeurs,
      unite: variante.unite,
      sensInverse: false,          // compter des équipements : plus = mieux
      lignes: retenues,
      toutes,
      dimensions: donnees.dimensions || [],
      colonnes: donnees.colonnes || [],
      mesure,
      total,
    };
  }, [donnees, variante, filtres]);

  const ordre = useMemo(() => {
    if (!vue) return [];
    return Object.entries(vue.valeurs)
      .map(([id, v]) => ({ id: Number(id), v }))
      .sort((a, b) => (vue.sensInverse ? a.v - b.v : b.v - a.v));
  }, [vue]);

  const classes = useMemo(() => {
    if (!vue) return { bornes: [], couleurs: [], couleur: () => NEUTRE };
    const bornes = classer(vue.valeurs);
    const couleurs = palette(bornes.length, vue.sensInverse);
    return { bornes, couleurs, couleur: (v) => couleurDeClasse(v, bornes, couleurs) };
  }, [vue]);
  const couleur = classes.couleur;

  // Un seul formateur pour la carte, la légende, le classement et les indicateurs
  // de tête : trois précisions différentes sur le même écran donneraient
  // l'impression que ce ne sont pas les mêmes chiffres.
  const dec = useMemo(() => (vue ? decimales(vue.valeurs, vue.unite) : 0), [vue]);
  const fmt = useMemo(
    () => (v) => (v === null || v === undefined ? "—" : `${nb(v, dec)}${vue?.unite === "%" ? " %" : ""}`),
    [dec, vue?.unite]
  );

  const geojson = vue?.niveau === "commune" ? geoCommunes : geoProvinces;
  // Au-delà d'une vingtaine de zones, les étiquettes se chevauchent quel que
  // soit le placement : la couleur porte la valeur, le survol donne le détail,
  // et le classement à droite garde les noms lisibles.
  const nombreux = (geojson?.features?.length || 0) > SEUIL_ETIQUETTES;

  // Symboles proportionnels réservés aux QUANTITÉS ABSOLUES lisibles d'un coup
  // d'œil : huit provinces, un nombre d'établissements ou d'agents. Un ratio
  // « habitants par médecin » reste en aplats — un disque deux fois plus gros y
  // signifierait « deux fois plus de rapport », ce qui n'a aucun sens. Et à 146
  // communes, les disques se recouvriraient plus encore que les étiquettes.
  const enBulles = !!vue && !vue.estIndicateur && !nombreux;

  const motifs = useMemo(() => {
    const m = {};
    (donnees?.absences_confirmees || []).forEach((a) => { m[a.territoire_id] = a.motif; });
    return m;
  }, [donnees]);

  // --- export ---------------------------------------------------------------
  function donneesExport() {
    if (!vue) return null;
    const entete = [
      `ORVSIT — Explorer : ${angle?.nom}`,
      `${variante?.nom}${vue.unite ? ` (${vue.unite})` : ""}`,
      nbFiltres ? `Filtres actifs : ${Object.entries(filtres)
        .map(([c, v]) => `${c} = ${[...v].join(" ou ")}`).join(" ; ")}` : "Aucun filtre",
      donnees?.source ? `Source : ${donnees.source}${donnees.annee ? ` (${donnees.annee})` : ""}` : "",
    ].filter(Boolean);

    // L'export suit exactement ce qui est affiché, filtres compris : c'est la
    // raison d'être du bouton, et la première chose qu'un utilisateur vérifie.
    const colonnes = vue.estIndicateur
      ? vue.colonnes.map((c) => (c === "Valeur" ? variante.nom : c))
      : vue.colonnes;
    return {
      entete,
      colonnes,
      lignes: vue.lignes.map((l) => vue.colonnes.map((c) => l[c])),
    };
  }

  // --- rendu ----------------------------------------------------------------
  if (erreur && !catalogue) return (
    <DashboardLayout title="Explorer un indicateur" active="explorer">
      <Message type="erreur" titre="Le catalogue n'a pas pu être chargé" texte={erreur} />
    </DashboardLayout>
  );

  if (!catalogue) return (
    <DashboardLayout title="Explorer un indicateur" active="explorer">
      <div className="flex items-center gap-2 text-t2 text-sm">
        <Loader2 size={16} className="animate-spin" /> Chargement du catalogue…
      </div>
    </DashboardLayout>
  );

  return (
    <DashboardLayout title="Explorer un indicateur" active="explorer">
      {/* ---------------- barre d'angles ----------------
          Une seule ligne qui défile horizontalement plutôt qu'un repli sur
          deux rangs : le repli déplaçait les onglets d'une ligne à l'autre au
          moindre changement de largeur, et laissait le bouton Exporter orphelin
          sur sa propre ligne. Ici la barre garde toujours la même forme. */}
      <div className="bg-surface border border-line rounded-2xl p-1.5 mb-3 overflow-x-auto">
        <div className="flex gap-1 min-w-max">
          {catalogue.angles.map((a) => (
            <button key={a.cle} onClick={() => choisirAngle(a.cle)}
              className={`px-3.5 py-2 rounded-xl text-[12.5px] font-semibold whitespace-nowrap
                          transition-colors ${
                a.cle === cleAngle ? "bg-navy text-white" : "text-t2 hover:text-navy hover:bg-bg"}`}>
              {a.nom}
            </button>
          ))}
        </div>
      </div>

      {/* ---------------- en-tête de l'angle ----------------
          La question de décision est écrite en toutes lettres : le titre seul
          (« Plateau technique ») ne dit pas à un élu ce qu'il va trouver ici. */}
      {angle && (
        <div className="bg-surface border border-line rounded-2xl px-5 py-4 mb-4
                        flex flex-wrap items-start gap-4">
          <div className="flex-1 min-w-[260px]">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h2 className="font-bold text-navy text-[15px]">{angle.nom}</h2>
              <span className="text-[10px] font-bold uppercase tracking-wide text-t2
                               bg-bg px-2 py-0.5 rounded-md">
                niveau {angle.grain === "commune" ? "commune" : "province"}
              </span>
              {variante?.unite && (
                <span className="text-[11px] text-t3">en {variante.unite}</span>
              )}
            </div>
            {angle.question && (
              <p className="text-[12.5px] text-t2 mt-1.5 leading-relaxed max-w-[62ch]">
                {angle.question}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {angle.variantes.length > 1 && (
              <div className="w-[330px]">
                <SelecteurTerritoire
                  valeur={cleVariante || ""}
                  onChange={choisirVariante}
                  options={angle.variantes.map((v) => ({
                    id: v.cle, nom: v.nom, detail: v.unite || undefined,
                  }))}
                  Icone={Layers}
                  placeholder="Choisir un indicateur…"
                  libelleRecherche="Rechercher un indicateur…"
                  libelleVide="Aucun indicateur ne correspond."
                  largeurMenu="min-w-[420px]"
                />
              </div>
            )}
            <BoutonExport nom={`explorer_${angle?.cle || THEME}`} donnees={donneesExport} />
          </div>
        </div>
      )}

      {/* ---------------- ventilation ---------------- */}
      {donnees?.ventilations && Object.keys(donnees.ventilations).length > 0 && (
        <div className="flex flex-wrap items-center gap-3 bg-blue-soft border border-blue/20
                        rounded-2xl px-4 py-3 mb-4">
          <Info size={15} className="text-blue shrink-0" />
          <span className="text-[12px] text-navy font-semibold">
            Cet indicateur est détaillé — choisissez le découpage :
          </span>
          {Object.entries(donnees.ventilations).map(([col, valeurs]) => (
            <label key={col} className="flex items-center gap-1.5 text-[11.5px] text-t2">
              {col}
              <select
                value={donnees.ventilation_appliquee?.[col] || ""}
                onChange={(e) => setVentilation((p) => ({ ...p, [col]: e.target.value }))}
                className="text-[12px] font-semibold text-navy bg-surface border border-line
                           rounded-lg px-2 py-1 outline-none">
                {valeurs.map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
            </label>
          ))}
        </div>
      )}

      {erreur && <div className="mb-4"><Message type="erreur" titre="Lecture impossible" texte={erreur} /></div>}

      {chargement && !vue && (
        <div className="flex items-center gap-2 text-t2 text-sm py-10">
          <Loader2 size={16} className="animate-spin" /> Lecture des données…
        </div>
      )}

      {vue && (
        <>
          <Indicateurs vue={vue} ordre={ordre} variante={variante} nbFiltres={nbFiltres} fmt={fmt} />

          {/* Hauteur fixée sur grand écran : sans elle, la rangée s'étire à la
              hauteur du panneau de droite — un classement de 146 lignes ou une
              pile de facettes laissait un vide énorme sous la carte. Chaque
              panneau défile désormais à l'intérieur de sa propre carte. */}
          <div className="grid grid-cols-1 lg:grid-cols-[1.85fr_1fr] gap-4 items-stretch lg:h-[600px]">
            {/* ---------------- carte ---------------- */}
            <section className="bg-surface border border-line rounded-2xl p-5 flex flex-col min-h-0">
              <h2 className="font-bold text-navy text-[14px]">
                Répartition par {vue.niveau === "commune" ? "commune" : "province"}
              </h2>
              <p className="text-[11.5px] text-t2 mt-0.5 mb-3">
                {nombreux
                  ? "Survolez une zone pour son nom et sa valeur ; le classement à droite les donne toutes."
                  : enBulles
                    ? "La taille du disque suit le nombre, écrit à l'intérieur. Survolez pour le nom."
                    : "La couleur et le chiffre traduisent la valeur. Molette ou boutons pour zoomer."}
              </p>

              {geojson ? (
                <CarteChoropleth
                  geojson={geojson}
                  valeurs={vue.valeurs}
                  couleurDe={(v) => couleur(v)}
                  hauteur={455}
                  libelleDe={(id) => {
                    const nom = vue.noms[id] || "Territoire";
                    const v = vue.valeurs[id];
                    if (v === undefined) return `${nom} — non renseigné`;
                    const base = `${nom} — ${fmt(v)}${vue.unite && vue.unite !== "%" ? ` ${vue.unite}` : ""}`;
                    return motifs[id] ? `${base} · ${motifs[id]}` : base;
                  }}
                  // Aucune étiquette quand les zones sont nombreuses (146
                  // communes se chevauchent quoi qu'on fasse) ni en mode bulles,
                  // où le chiffre est déjà écrit dans le disque.
                  etiquetteDe={(nombreux || enBulles) ? null : (id) =>
                    vue.valeurs[id] === undefined
                      ? null
                      : `${court(vue.noms[id])} ${nb(vue.valeurs[id], dec)}`}
                  bulles={enBulles ? {
                    couleur: (v) => couleur(v),
                    texteDe: (v) => nb(v, dec),
                  } : null}
                />
              ) : (
                <div className="flex-1 flex items-center justify-center text-t3 text-sm">
                  <Loader2 size={15} className="animate-spin mr-2" /> Chargement du fond de carte…
                </div>
              )}

              <Legende vue={vue} classes={classes} enBulles={enBulles} ordre={ordre} fmt={fmt} />
            </section>

            {/* ---------------- panneau droit ---------------- */}
            <section className="bg-surface border border-line rounded-2xl p-5 flex flex-col min-h-0 overflow-hidden">
              {vue.dimensions.length > 0 && (
                <div className="inline-flex self-start bg-bg rounded-xl p-1 gap-1 mb-3">
                  {[["filtres", "Filtrer", ListFilter], ["classement", "Classement", BarChart3]]
                    .map(([cle, label, Icon]) => (
                      <button key={cle} onClick={() => setOnglet(cle)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11.5px]
                                    font-semibold transition-colors ${
                          onglet === cle ? "bg-surface text-navy shadow-sm" : "text-t2 hover:text-navy"}`}>
                        <Icon size={13} /> {label}
                      </button>
                    ))}
                  {nbFiltres > 0 && (
                    <button onClick={() => setFiltres({})}
                      className="ml-1 px-2 text-[11px] font-bold text-blue hover:underline">
                      effacer ({nbFiltres})
                    </button>
                  )}
                </div>
              )}

              {(onglet === "classement" || !vue.dimensions.length) ? (
                <Classement
                  ordre={ordre} noms={vue.noms} couleur={couleur} unite={vue.unite} fmt={fmt}
                  tout={toutLeClassement} setTout={setToutLeClassement}
                  sensInverse={vue.sensInverse} motifs={motifs}
                />
              ) : (
                <Facettes
                  vue={vue} filtres={filtres} recherches={recherches}
                  setRecherches={setRecherches} basculer={basculer}
                />
              )}
            </section>
          </div>

          {/* ---------------- tableau de détail ---------------- */}
          {/* Le tableau n'est affiché que s'il apporte quelque chose que la carte
              et le classement ne disent pas déjà :
                - mode jeu       → chaque ligne est un objet réel (un établissement,
                                   un effectif), pas un territoire : toujours utile ;
                - indicateur au niveau commune → 146 lignes alors que le classement
                                   n'en montre que 12, plus la colonne Province ;
                - indicateur au niveau province → 8 lignes strictement identiques
                                   au classement, avec Territoire = Province.
                                   Répéter n'informe pas : on le retire. */}
          {vue.dimensions.length > 0 && (!vue.estIndicateur || vue.niveau === "commune") && (
            <TableauDetail vue={vue} filtres={filtres} basculer={basculer} fmt={fmt} />
          )}

          {donnees?.source && (
            <p className="mt-4 text-[11px] text-t3 leading-relaxed">
              <MapPin size={11} className="inline mr-1 -mt-0.5" />
              {donnees.source}{donnees.annee ? ` — ${donnees.annee}` : ""}
              {donnees.definition ? ` · ${donnees.definition.split(". Colonnes")[0]}.` : ""}
            </p>
          )}
        </>
      )}
    </DashboardLayout>
  );
}

// =========================================================== sous-composants

function Message({ type, titre, texte }) {
  return (
    <div className="flex items-start gap-3 bg-surface border border-line rounded-2xl p-5">
      <AlertTriangle size={18} className={type === "erreur" ? "text-coral shrink-0 mt-0.5" : "text-gold shrink-0 mt-0.5"} />
      <div>
        <div className="font-semibold text-navy text-sm">{titre}</div>
        <div className="text-t2 text-[13px] mt-1">{texte}</div>
      </div>
    </div>
  );
}

function Carte({ libelle, valeur, detail }) {
  return (
    <div className="bg-surface border border-line rounded-2xl px-4 py-3.5">
      <div className="text-[11px] text-t2">{libelle}</div>
      <div className="text-[25px] font-extrabold text-navy leading-tight mt-0.5">{valeur}</div>
      <div className="text-[10.5px] text-t3 mt-0.5">{detail}</div>
    </div>
  );
}

/** Quatre chiffres de tête, différents selon le mode de lecture. */
function Indicateurs({ vue, ordre, variante, nbFiltres, fmt }) {
  const cartes = [];

  if (vue.estIndicateur) {
    const meilleur = ordre[0];
    const pire = ordre[ordre.length - 1];
    // Un rapport n'a de sens que si le dénominateur n'est pas nul. Quarante-neuf
    // communes affichent zéro sur « privation — mortalité infantile » : le
    // rapport y serait infini. On bascule alors sur l'écart absolu, qui reste
    // parfaitement lisible.
    const rapport = meilleur && pire && meilleur.v > 0 ? pire.v / meilleur.v : null;
    cartes.push(
      ["Situation la plus favorable", meilleur ? fmt(meilleur.v) : "—",
        meilleur ? court(vue.noms[meilleur.id]) : ""],
      ["Situation la plus tendue", pire ? fmt(pire.v) : "—",
        pire ? court(vue.noms[pire.id]) : ""],
      rapport
        ? ["Rapport entre les deux", `${rapport.toFixed(1)} ×`,
           `${fmt(Math.abs(pire.v - meilleur.v))} d'écart`]
        : ["Écart entre les deux", meilleur && pire ? fmt(Math.abs(pire.v - meilleur.v)) : "—",
           "rapport indéfini : la valeur la plus basse est nulle"],
      ["Territoires affichés", nb(ordre.length),
        nbFiltres ? `${nbFiltres} filtre${nbFiltres > 1 ? "s" : ""} actif${nbFiltres > 1 ? "s" : ""}` : "aucun filtre"]
    );
  } else {
    const dimsAnalyse = vue.dimensions.filter((d) => !COLONNES_GEO.has(d));
    const premiere = dimsAnalyse[0];
    const repartition = premiere ? agreger(vue.lignes, premiere, vue.mesure) : [];
    const tete = ordre[0];
    cartes.push(
      [`Total ${vue.unite || "unités"}`, nb(vue.total),
        nbFiltres ? `${nbFiltres} filtre${nbFiltres > 1 ? "s" : ""} actif${nbFiltres > 1 ? "s" : ""}` : "région entière"],
      [vue.niveau === "commune" ? "Communes desservies" : "Provinces desservies",
        nb(ordre.filter((o) => o.v > 0).length),
        vue.niveau === "commune" ? "sur 146 communes" : "sur 8 provinces"],
      [premiere || "Répartition", nb(repartition.length),
        repartition[0] ? `plus fréquent : ${repartition[0][0]}` : ""],
      ["Concentration", tete && vue.total ? `${Math.round((tete.v / vue.total) * 100)} %` : "—",
        tete ? `dans ${court(vue.noms[tete.id])}` : ""]
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      {cartes.map(([l, v, d]) => <Carte key={l} libelle={l} valeur={v} detail={d} />)}
    </div>
  );
}

/** Légende à classes : chaque couleur porte ses bornes chiffrées, sinon le
 *  lecteur ne peut pas savoir ce que « orange » signifie. */
function Legende({ vue, classes, enBulles, ordre, fmt }) {
  const { bornes, couleurs } = classes;
  if (!bornes.length) return null;

  // Les bornes passent par le MÊME formateur que le reste de l'écran : arrondir
  // ici à l'entier afficherait « 0 – 0 » sur un indicateur qui va de 0 à 0,94.
  const format = ([min, max]) => (min === max ? fmt(min) : `${fmt(min)} – ${fmt(max)}`);

  // En symboles proportionnels, c'est la TAILLE qui porte l'information : la
  // légende doit donc montrer des disques de référence, pas des aplats.
  if (enBulles && ordre.length) {
    const max = ordre[0].v;
    const paliers = [...new Set([max, Math.round(max / 3), 1].filter((v) => v >= 1))];
    const diametre = (v) => 8 + 26 * Math.sqrt(v / max);
    return (
      <div className="flex items-center gap-4 flex-wrap mt-3 text-[10.5px] text-t2">
        <span className="font-semibold">Taille = nombre</span>
        {paliers.map((v) => (
          <span key={v} className="inline-flex items-center gap-1.5">
            <i className="block rounded-full border-2 border-white"
               style={{ width: diametre(v), height: diametre(v), background: classes.couleur(v) }} />
            {nb(v)}
          </span>
        ))}
        <span className="ml-auto">
          {nb(ordre.reduce((s, o) => s + o.v, 0))} {vue.unite || "unités"} au total
          {" · "}gris = non renseigné
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 flex-wrap mt-3 text-[10.5px] text-t2">
      {bornes.length === 1 ? (
        <>
          <span className="inline-block w-9 h-2.5 rounded" style={{ background: couleurs[0] }} />
          <span>toutes à égalité : {format(bornes[0])}</span>
        </>
      ) : (
        <div className="flex items-center gap-2.5 flex-wrap">
          {bornes.map((b, i) => (
            <span key={i} className="inline-flex items-center gap-1.5">
              <i className="block w-5 h-2.5 rounded-sm" style={{ background: couleurs[i] }} />
              {format(b)}
            </span>
          ))}
        </div>
      )}
      <span className="ml-auto">
        {vue.sensInverse ? "accès facile → accès tendu" : "peu doté → bien doté"}
        {" · "}gris = non renseigné
      </span>
    </div>
  );
}

/** Classement en barres horizontales. L'œil compare des longueurs alignées sur
 *  une même base : c'est la forme la plus fiable pour lire un rang. */
function Classement({ ordre, noms, couleur, unite, tout, setTout, sensInverse, motifs, fmt }) {
  if (!ordre.length) return <p className="text-[12px] text-t3">Aucune valeur à classer.</p>;
  const mx = Math.max(...ordre.map((o) => o.v), 1);
  const vus = tout ? ordre : ordre.slice(0, PALMARES);

  return (
    <>
      <p className="text-[11.5px] text-t2 mb-3">
        {sensInverse ? "Du plus favorable au moins favorable." : "Du mieux doté au moins doté."}
      </p>
      <div className="flex flex-col gap-2.5 overflow-y-auto flex-1 min-h-0 pr-1">
        {vus.map((o, i) => (
          <div key={o.id} className="flex flex-col gap-1">
            <div className="flex items-baseline gap-2">
              <span className="text-[10px] font-extrabold text-t3 w-4 shrink-0">{i + 1}</span>
              <span className="flex-1 text-[12px] font-semibold text-t1 truncate"
                    title={motifs[o.id] || noms[o.id]}>
                {court(noms[o.id]) || o.id}
              </span>
              <span className="text-[12.5px] font-extrabold tabular-nums"
                    style={{ color: couleur(o.v) }}>
                {fmt(o.v)}
              </span>
            </div>
            <span className="block h-2 rounded-full bg-bg overflow-hidden">
              <i className="block h-full rounded-full transition-all duration-300"
                 style={{ width: `${Math.max((o.v / mx) * 100, 2)}%`, background: couleur(o.v) }} />
            </span>
          </div>
        ))}
      </div>
      {ordre.length > PALMARES && (
        <button onClick={() => setTout(!tout)}
          className="mt-3 shrink-0 border border-dashed border-line rounded-xl py-2
                     text-[11px] font-bold text-blue hover:bg-blue-soft transition-colors">
          {tout ? "Réduire au palmarès" : `Afficher les ${ordre.length} au complet`}
        </button>
      )}
    </>
  );
}

/** Filtres à facettes : OU à l'intérieur d'une colonne, ET entre colonnes. */
function Facettes({ vue, filtres, recherches, setRecherches, basculer }) {
  return (
    <>
      <p className="text-[11.5px] text-t2 mb-3">
        Cochez une ou plusieurs valeurs. Les colonnes se combinent.
      </p>
      <div className="flex flex-col overflow-y-auto flex-1 min-h-0 -mx-1 px-1">
        {vue.dimensions.map((col) => {
          // Une facette ne se filtre jamais elle-même : sinon, cocher « Rural »
          // ferait disparaître « Urbain » de la liste et le choix deviendrait
          // irréversible sans passer par le bouton « effacer ».
          const liste = agreger(vue.toutes.filter((l) => passe(l, filtres, col)), col, vue.mesure);
          const choisis = filtres[col] || new Set();
          const q = (recherches[col] || "").toLowerCase();
          const visibles = q ? liste.filter(([v]) => v.toLowerCase().includes(q)) : liste;
          const triees = [...visibles].sort(
            (a, b) => (choisis.has(b[0]) ? 1 : 0) - (choisis.has(a[0]) ? 1 : 0) || b[1] - a[1]
          );
          const mx = liste[0]?.[1] || 1;

          return (
            <div key={col} className="py-3 border-b border-line last:border-0">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10.5px] font-bold uppercase tracking-wide text-t2">{col}</span>
                <span className="text-[10px] text-t3">{liste.length} valeurs</span>
                {choisis.size > 0 && (
                  <button onClick={() => [...choisis].forEach((v) => basculer(col, v))}
                    className="ml-auto text-[11px] font-bold text-blue hover:underline">
                    effacer ({choisis.size})
                  </button>
                )}
              </div>

              {liste.length > 8 && (
                <input value={recherches[col] || ""} placeholder="Rechercher…"
                  onChange={(e) => setRecherches((p) => ({ ...p, [col]: e.target.value }))}
                  className="w-full text-[11.5px] bg-bg border border-line rounded-lg
                             px-2.5 py-1.5 mb-2 outline-none focus:border-blue focus:bg-surface" />
              )}

              <div className="flex flex-col gap-px max-h-52 overflow-y-auto pr-1">
                {triees.length ? triees.map(([v, n]) => {
                  const actif = choisis.has(v);
                  return (
                    <button key={v} onClick={() => basculer(col, v)}
                      className="flex items-center gap-2.5 px-1.5 py-1.5 rounded-lg
                                 hover:bg-bg text-left w-full">
                      <span className={`w-[15px] h-[15px] rounded shrink-0 border flex items-center
                                        justify-center transition-colors ${
                        actif ? "bg-blue border-blue" : "bg-surface border-[#cfd6e0]"}`}>
                        {actif && (
                          <svg width="9" height="9" viewBox="0 0 12 12">
                            <path d="M1 6l3.5 3.5L11 2" stroke="#fff" strokeWidth="2.2"
                                  fill="none" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        )}
                      </span>
                      <span className={`flex-1 text-[11.5px] truncate ${
                        actif ? "font-bold text-navy" : "text-t1"}`} title={v}>{v}</span>
                      <span className="w-[52px] h-1.5 rounded bg-bg overflow-hidden shrink-0">
                        <i className="block h-full rounded bg-blue"
                           style={{ width: `${(n / mx) * 100}%`, opacity: actif ? 1 : 0.55 }} />
                      </span>
                      <span className={`w-11 text-right text-[11px] tabular-nums ${
                        actif ? "font-bold text-navy" : "font-semibold text-t2"}`}>{nb(n)}</span>
                    </button>
                  );
                }) : <p className="text-[11px] text-t3 px-1.5 py-2">Aucune valeur ne correspond.</p>}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}

function TableauDetail({ vue, filtres, basculer, fmt }) {
  const actifs = Object.entries(filtres).flatMap(([c, vs]) => [...vs].map((v) => [c, v]));

  return (
    <section className="bg-surface border border-line rounded-2xl p-5 mt-4">
      <div className="flex items-center gap-3 mb-1">
        <h2 className="font-bold text-navy text-[14px] flex-1">Détail</h2>
        <span className="text-[11.5px] text-t2">
          {nb(vue.lignes.length)} ligne{vue.lignes.length > 1 ? "s" : ""}
        </span>
      </div>
      <p className="text-[11.5px] text-t2 mb-3">Les lignes correspondant exactement aux filtres actifs.</p>

      {actifs.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap bg-blue-soft rounded-xl px-3 py-2.5 mb-3">
          {actifs.map(([c, v]) => (
            <span key={`${c}-${v}`}
              className="inline-flex items-center gap-2 bg-surface text-blue text-[11px]
                         font-bold px-2.5 py-1 rounded-lg border border-blue/25">
              <em className="not-italic font-medium text-t2">{c}</em> {v}
              <b onClick={() => basculer(c, v)}
                 className="cursor-pointer opacity-50 hover:opacity-100 text-[13px] leading-none">×</b>
            </span>
          ))}
        </div>
      )}

      <div className="max-h-[380px] overflow-auto">
        <table className="w-full border-collapse text-[12px]">
          <thead>
            <tr>
              {vue.colonnes.map((c) => (
                <th key={c} className="text-left text-[10px] uppercase tracking-wide text-t2
                                       font-bold px-2 py-2 border-b-2 border-line sticky top-0 bg-surface">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {vue.lignes.slice(0, 400).map((l, i) => (
              <tr key={i} className="hover:bg-bg">
                {vue.colonnes.map((c) => (
                  <td key={c} className="px-2 py-1.5 border-b border-line">
                    {c === "Valeur" ? fmt(l[c])
                      : l[c] === null || l[c] === undefined ? "—" : String(l[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {vue.lignes.length > 400 && (
        <p className="text-[11px] text-t3 mt-2">
          400 premières lignes affichées sur {nb(vue.lignes.length)}. L'export contient tout.
        </p>
      )}
    </section>
  );
}
