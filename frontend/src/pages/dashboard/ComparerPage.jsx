// Comparer les territoires — met en regard 2 ou 3 territoires de même niveau.
//
// La page répond à une question de décision : « lequel servir en premier, et
// sur quoi ? ». Elle s'organise donc ainsi :
//   1. Sélection des territoires (provinces entre elles, ou communes entre elles).
//   2. LE VERDICT, écrit en toutes lettres : qui décroche, sur quoi, de combien.
//      Un décideur ne doit pas avoir à déduire la conclusion d'un graphique.
//   3. Position dans la région : TOUS les territoires sont coloriés selon
//      l'indicateur choisi, les comparés sont entourés et nommés. C'est ce qui
//      permet de lire « zone la plus faible » et non « moins bien que l'autre ».
//   4. Écarts les plus marquants, calculés côté serveur.
//   5. Le détail par thème, avec un verdict par thème puis les valeurs.
//   6. Tableau complet, avec le rang de chaque territoire.
//
// Aucune valeur n'est calculée ici : l'API renvoie les valeurs officielles, les
// écarts (soustractions) et les rangs. Le frontend ne fait que mettre en forme.

import { Fragment, useEffect, useMemo, useState } from "react";
import {
  ArrowLeftRight, MapPin, TriangleAlert, ChartNoAxesColumn, Table2,
  ArrowDown, ArrowUp,
} from "lucide-react";
import DashboardLayout from "../../components/DashboardLayout";
import CarteChoropleth from "../../components/CarteChoropleth";
import SelecteurTerritoire from "../../components/SelecteurTerritoire";
import BoutonExport from "../../components/BoutonExport";
import { getArborescence } from "../../api/fiche";
import { getComparaison } from "../../api/comparer";
import { nombrePourExcel } from "../../utils/export";

/* ---------------------------------------------------------------- couleurs */
const NAVY = "#0a2540", TEAL = "#12a594";

// UNE SEULE ÉCHELLE DE COULEUR DANS TOUTE LA PAGE : la performance, du plus
// favorable au plus défavorable. Carte, barres, matrice, pastilles de rang :
// partout la même signification. Les territoires, eux, se distinguent par leur
// nom, toujours écrit à côté — pas besoin de leur attribuer une couleur, ce qui
// créerait un second langage concurrent.
const ECHELLE = ["#0d7d6c", "#5cb8a2", "#f5a623", "#ef7d54", "#d63d3d"];
const NEUTRE = "#dfe4ec";                          // territoire non mesuré

// Couleur correspondant à une position : rang 1 = le plus favorable.
function couleurRang(rang, total) {
  if (!rang || !total) return NEUTRE;
  const q = (rang - 1) / Math.max(total - 1, 1);
  return ECHELLE[Math.min(Math.floor(q * ECHELLE.length), ECHELLE.length - 1)];
}

/* ----------------------------------------------------------------- formats */
const nb = (v) => (v == null ? "—" : Number(v).toLocaleString("fr-FR"));
const dec = (v, d = 1) => (v == null ? "—" : Number(v).toFixed(d).replace(".", ","));
const val = (v, unite) => (v == null ? "—" : unite === "%" ? `${dec(v)} %` : nb(v));
const court = (nom) => (nom || "")
  .replace(/^Commune (de |d')/, "").replace(/^(Préfecture|Province) (de |d')/, "")
  .split("-")[0];

/* ============================================================== briques UI */

function Carte({ titre, Icon, couleurIcone, but, children, className = "" }) {
  return (
    <div className={`bg-surface border border-line rounded-2xl p-4 flex flex-col h-full ${className}`}>
      {titre && (
        <h3 className="text-[13.5px] font-bold text-navy flex items-center gap-2">
          {Icon && <Icon size={16} style={{ color: couleurIcone || NAVY }} />}
          {titre}
        </h3>
      )}
      {but && <p className="text-[11.5px] text-t2 mt-1 leading-relaxed">{but}</p>}
      <div className="flex-1 flex flex-col mt-3">{children}</div>
    </div>
  );
}

function TitreSection({ Icon, titre, note }) {
  return (
    <div className="flex items-center gap-2.5 mt-7 mb-3.5">
      <Icon size={19} className="text-navy" />
      <h2 className="text-base font-extrabold text-navy">{titre}</h2>
      {note && <span className="text-[11.5px] text-t2 ml-auto">{note}</span>}
    </div>
  );
}

/* Puce de rang : « 8ᵉ/8 » coloré selon la position. */
function Rang({ rang, total }) {
  if (!rang) return null;
  const couleur = couleurRang(rang, total);
  return (
    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded"
          style={{ background: `${couleur}22`, color: couleur }}>
      {rang}<sup>{rang === 1 ? "er" : "e"}</sup>/{total}
    </span>
  );
}

/* ================================================================= la page */

export default function ComparerPage() {
  const [arbre, setArbre] = useState([]);
  const [niveau, setNiveau] = useState("prov");
  const [ids, setIds] = useState([2, 9, 8]);
  const [data, setData] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const [geoProv, setGeoProv] = useState(null);
  const [geoComm, setGeoComm] = useState(null);
  const [indCarte, setIndCarte] = useState(null);
  const [theme, setTheme] = useState(null);

  useEffect(() => {
    getArborescence().then(setArbre).catch(() => {});
    fetch("/geo/provinces.geojson").then((r) => r.json()).then(setGeoProv).catch(() => {});
    fetch("/geo/communes.geojson").then((r) => r.json()).then(setGeoComm).catch(() => {});
  }, []);

  useEffect(() => {
    const retenus = ids.filter(Boolean);
    if (retenus.length < 2) return;
    setChargement(true);
    setErreur("");
    getComparaison(retenus)
      .then((d) => { setData(d); setIndCarte(null); setTheme(null); })
      .catch((e) => setErreur(e?.response?.data?.detail || "Comparaison impossible."))
      .finally(() => setChargement(false));
  }, [ids]);

  /* --- listes de choix --- */
  const options = useMemo(() => {
    if (niveau === "prov") {
      return arbre.map((p) => ({ id: p.territoire_id, nom: p.nom }));
    }
    return arbre.flatMap((p) =>
      (p.communes || []).map((c) => ({ id: c.territoire_id, nom: court(c.nom), groupe: p.nom })));
  }, [arbre, niveau]);

  function changerNiveau(n) {
    setNiveau(n);
    setData(null);
    if (n === "prov") setIds([2, 9, 8]);
    else {
      const communes = arbre.flatMap((p) => p.communes || []).map((c) => c.territoire_id);
      setIds(communes.slice(0, 3));
    }
  }

  function changerSlot(i, valeur) {
    const copie = [...ids];
    copie[i] = valeur ? Number(valeur) : null;
    setIds(copie);
  }

  /* --- indicateur affiché sur la carte --- */
  const defs = data?.indicateurs || [];
  const defCarte = useMemo(
    () => defs.find((d) => d.cle === indCarte) || defs[0] || null,
    [defs, indCarte]);

  const valeursCarte = data?.valeurs?.[defCarte?.cle] || {};

  // Classement de TOUS les territoires de référence pour l'indicateur affiché :
  // c'est lui qui donne sa couleur à chaque zone.
  const classement = useMemo(() => {
    if (!defCarte || !data) return [];
    return Object.entries(valeursCarte)
      .map(([id, v]) => ({ id: Number(id), valeur: v }))
      .sort((a, b) => (defCarte.sens === 1 ? b.valeur - a.valeur : a.valeur - b.valeur));
  }, [defCarte, valeursCarte, data]);

  function couleurZone(_, id) {
    const rang = classement.findIndex((c) => c.id === Number(id));
    if (rang < 0) return NEUTRE;                       // territoire non mesuré
    const q = rang / Math.max(classement.length - 1, 1);
    return ECHELLE[Math.min(Math.floor(q * ECHELLE.length), ECHELLE.length - 1)];
  }

  // Tous les territoires comparés sont entourés du même trait sombre : c'est
  // leur NOM écrit sur la carte qui les identifie, pas une couleur.
  const couleurDe = () => NAVY;
  const nomDe = (tid) =>
    (data?.territoires || []).find((t) => t.territoire_id === Number(tid))?.nom
    || data?.reference?.[String(tid)] || tid;

  /* --- thèmes du profil --- */
  const themes = useMemo(() => [...new Set(defs.map((d) => d.theme))], [defs]);
  const themeActif = theme || themes[0];
  const indicateursTheme = defs.filter((d) => d.theme === themeActif);

  /* ------------------------------------------------------------------ verdicts
   * Un décideur ne doit pas avoir à déduire la conclusion d'un graphique :
   * on la calcule et on l'écrit. Tout vient de « ecarts » et « rangs », déjà
   * produits par le serveur à partir des valeurs officielles.
   */

  // Territoire le plus souvent en dernière position parmi ceux comparés.
  const verdictGlobal = useMemo(() => {
    if (!data?.ecarts?.length) return null;
    const compte = {};
    data.ecarts.forEach((e) => {
      compte[e.pire.territoire_id] = (compte[e.pire.territoire_id] || 0) + 1;
    });
    const classe = Object.entries(compte).sort((a, b) => b[1] - a[1]);
    if (!classe.length) return null;
    const [tid, combien] = classe[0];

    // Sur combien d'indicateurs ce territoire est-il DERNIER de toute la région ?
    // C'est ce qui distingue « en retard sur ses voisins » de « zone critique ».
    const derniersRegion = defs.filter((d) => {
      const r = data.rangs?.[tid]?.[d.cle];
      return r && r.rang === r.total;
    }).length;

    return {
      tid, combien, total: data.ecarts.length, derniersRegion,
      principal: data.ecarts.find((e) => e.pire.territoire_id === tid),
    };
  }, [data, defs]);

  // Même logique, restreinte au thème affiché.
  const verdictTheme = useMemo(() => {
    if (!data?.ecarts?.length || !indicateursTheme.length) return null;
    const cles = new Set(indicateursTheme.map((d) => d.cle));
    const concernes = data.ecarts.filter((e) => cles.has(e.cle));
    if (!concernes.length) return null;
    const compte = {};
    concernes.forEach((e) => {
      compte[e.pire.territoire_id] = (compte[e.pire.territoire_id] || 0) + 1;
    });
    const [tid, combien] = Object.entries(compte).sort((a, b) => b[1] - a[1])[0];
    return { tid, combien, total: concernes.length, principal: concernes[0] };
  }, [data, indicateursTheme]);

  // Contenu de l'export : le tableau comparatif tel qu'affiché, augmenté des
  // rangs — un fichier doit se suffire à lui-même, sans la page pour le lire.
  function donneesExport() {
    if (!data) return null;
    const noms = data.territoires.map((t) => court(t.nom));
    const colonnes = ["Thème", "Indicateur", "Unité", ...noms,
                      ...noms.map((n) => `Rang ${n}`), "Écart"];
    const lignes = [];
    themes.forEach((th) => {
      defs.filter((d) => d.theme === th).forEach((d) => {
        const e = (data.ecarts || []).find((x) => x.cle === d.cle);
        lignes.push([
          th, d.label, d.unite || "habitants",
          ...data.territoires.map((t) =>
            nombrePourExcel(data.valeurs?.[d.cle]?.[String(t.territoire_id)])),
          ...data.territoires.map((t) => {
            const r = data.rangs?.[String(t.territoire_id)]?.[d.cle];
            return r ? `${r.rang}/${r.total}` : "";
          }),
          e ? nombrePourExcel(e.ecart) : "",
        ]);
      });
    });
    const sources = [...new Map(
      Object.values(data.sources || {}).flat().map((x) => [x.source, x])).values()];
    return {
      colonnes, lignes,
      entete: [
        "ORVSIT — Comparaison de territoires",
        `Territoires : ${data.territoires.map((t) => t.nom).join(" / ")}`,
        `Niveau : ${data.niveau === "commune" ? "communes" : "préfectures et provinces"}`,
        `Ensemble de référence : ${Object.keys(data.reference).length} territoires`,
        `Exporté le ${new Date().toLocaleDateString("fr-FR")}`,
        ...sources.map((x) => `Source : ${x.source}${x.annee ? ` (${x.annee})` : ""}`),
      ],
    };
  }

  return (
    <DashboardLayout title="Comparer les territoires" active="comparer">
      {/* ================= EN-TÊTE ================= */}
      {/* Pas d'overflow-hidden ici : il rognait les menus déroulants des
          sélecteurs. Le halo décoratif est donc rogné par son propre conteneur. */}
      <div className="relative rounded-3xl px-7 py-6 text-white
                      bg-gradient-to-br from-navy via-navy-2 to-navy shadow-xl">
        <div className="absolute inset-0 rounded-3xl overflow-hidden pointer-events-none">
          <div className="absolute -top-24 -right-10 w-72 h-72 rounded-full"
               style={{ background: "radial-gradient(circle, rgba(245,166,35,.28), transparent 70%)" }} />
          <div className="absolute -bottom-20 left-1/4 w-64 h-64 rounded-full"
               style={{ background: "radial-gradient(circle, rgba(245,166,35,.12), transparent 70%)" }} />
        </div>
        <div className="relative">
          <h1 className="text-[23px] font-extrabold flex items-center gap-2.5">
            <span className="w-9 h-9 rounded-xl bg-gold/20 text-gold flex items-center justify-center">
              <ArrowLeftRight size={19} />
            </span>
            Comparer les territoires
          </h1>
          <p className="text-[12.5px] text-white/65 mt-1.5">
            Deux ou trois territoires de même niveau, replacés dans l'ensemble de la région.
          </p>

          <div className="inline-flex bg-white/10 rounded-xl p-1 mt-4">
            {[["prov", "Provinces"], ["comm", "Communes"]].map(([cle, label]) => (
              <button key={cle} onClick={() => changerNiveau(cle)}
                className={`text-[12.5px] font-semibold px-4 py-2 rounded-lg transition-colors ${
                  niveau === cle ? "bg-gold text-navy shadow-sm" : "text-white/70 hover:text-white"}`}>
                {label}
              </button>
            ))}
          </div>

          <div className="grid sm:grid-cols-3 gap-3 mt-4">
            {[0, 1, 2].map((i) => (
              <div key={i} className="bg-white/[0.08] border border-white/15 rounded-2xl px-3.5 py-3">
                <label className="flex items-center text-[10.5px] font-semibold text-white/65">
                  <span className="w-4 h-4 rounded-md mr-2 bg-gold text-navy text-[9px]
                                   font-extrabold flex items-center justify-center">{i + 1}</span>
                  Territoire {i + 1}{i === 2 ? " (facultatif)" : ""}
                </label>
                <div className="mt-1.5">
                  <SelecteurTerritoire
                    sombre
                    valeur={ids[i] || ""}
                    onChange={(v) => changerSlot(i, v)}
                    options={niveau === "prov"
                      ? options
                      : arbre.flatMap((p) => (p.communes || []).map((c) => ({
                          id: c.territoire_id, nom: court(c.nom), groupe: p.nom })))}
                    optionVide={i === 2 ? "Aucun troisième territoire" : null}
                    placeholder="Choisir un territoire"
                  />
                </div>
                {data?.valeurs?.population?.[String(ids[i])] != null && (
                  <div className="text-[10.5px] text-white/60 mt-0.5">
                    {nb(data.valeurs.population[String(ids[i])])} habitants
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {chargement ? (
        <p className="text-t2 mt-6">Chargement…</p>
      ) : erreur ? (
        <p className="text-red-600 mt-6">{erreur}</p>
      ) : !data ? null : (
        <>
          {/* ================= VERDICT ================= */}
          {/* La conclusion AVANT les graphiques : c'est ce qu'un décideur lit
              en premier, et souvent la seule chose qu'il retiendra. */}
          {verdictGlobal && (
            <div className="mt-6 rounded-2xl border-2 p-5"
                 style={{ borderColor: "#f0d9d9", background: "#fdf6f6" }}>
              <div className="flex items-start gap-3.5">
                <span className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
                      style={{ background: "#fdeaea", color: "#b02121" }}>
                  <TriangleAlert size={22} />
                </span>
                <div className="min-w-0">
                  <div className="text-[10.5px] font-bold uppercase tracking-wider text-t3 mb-1">
                    Ce qu'il faut retenir
                  </div>
                  <p className="text-[15px] leading-relaxed text-t1">
                    Parmi les territoires comparés,{" "}
                    <b className="text-navy">{court(nomDe(verdictGlobal.tid))}</b> est le plus en
                    difficulté : il arrive dernier sur{" "}
                    <b>{verdictGlobal.combien} des {verdictGlobal.total} indicateurs</b>.
                    {verdictGlobal.derniersRegion > 0 && (
                      <> Sur <b>{verdictGlobal.derniersRegion}</b> d'entre eux, il est même dernier
                      de toute la région.</>
                    )}
                  </p>
                  {verdictGlobal.principal && (
                    <p className="text-[13px] text-t2 mt-2.5 leading-relaxed">
                      Priorité la plus nette :{" "}
                      <b className="text-t1">{verdictGlobal.principal.label.toLowerCase()}</b> —{" "}
                      {val(verdictGlobal.principal.pire.valeur, verdictGlobal.principal.unite)} contre{" "}
                      {val(verdictGlobal.principal.meilleur.valeur, verdictGlobal.principal.unite)} à{" "}
                      {court(nomDe(verdictGlobal.principal.meilleur.territoire_id))}, soit un écart de{" "}
                      <b className="text-t1">
                        {verdictGlobal.principal.unite === "%"
                          ? `${dec(verdictGlobal.principal.ecart)} points`
                          : nb(verdictGlobal.principal.ecart)}
                      </b>.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ================= POSITION DANS LA RÉGION ================= */}
          <TitreSection Icon={MapPin} titre="Position dans la région"
            note={`${Object.keys(data.reference).length} ${
              data.niveau === "commune" ? "communes" : "provinces"} en référence`} />

          <div className="grid lg:grid-cols-[1.3fr_1fr] gap-4 items-stretch">
            <Carte titre={`${defCarte?.label || ""} — l'ensemble du territoire`}
                   Icon={MapPin} couleurIcone={TEAL}
                   but="Toutes les zones sont coloriées du plus favorable au plus défavorable ; les territoires comparés sont entourés de leur couleur.">
              <select value={defCarte?.cle || ""} onChange={(e) => setIndCarte(e.target.value)}
                className="text-xs border border-line rounded-lg px-3 py-2 bg-bg text-navy
                           font-semibold outline-none focus:border-blue mb-3 self-start">
                {defs.map((d) => <option key={d.cle} value={d.cle}>{d.label}</option>)}
              </select>

              <CarteChoropleth
                geojson={data.niveau === "commune" ? geoComm : geoProv}
                valeurs={valeursCarte}
                couleurDe={couleurZone}
                selection={data.territoires.map((t) => t.territoire_id)}
                couleurBordure={couleurDe}
                libelleDe={(id) => {
                  const nom = data.reference[String(id)];
                  if (!nom) return null;
                  const v = valeursCarte[id];
                  const r = classement.findIndex((c) => c.id === Number(id));
                  return `${court(nom)} : ${val(v, defCarte?.unite)}${
                    r >= 0 ? ` — ${r + 1}${r === 0 ? "er" : "e"}/${classement.length}` : ""}`;
                }}
                /* Seuls les territoires comparés sont nommés sur la carte :
                   écrire les 146 communes la rendrait illisible. */
                etiquetteDe={(id) => {
                  const t = data.territoires.find((x) => x.territoire_id === Number(id));
                  return t ? court(t.nom) : null;
                }}
                hauteur={330}
              />

              <div className="mt-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10.5px] font-semibold text-t1">
                    {classement.length ? val(classement[0].valeur, defCarte?.unite) : "—"}
                  </span>
                  <span className="flex rounded overflow-hidden">
                    {ECHELLE.map((c) => (
                      <span key={c} className="w-9 h-2.5" style={{ background: c }} />
                    ))}
                  </span>
                  <span className="text-[10.5px] font-semibold text-t1">
                    {classement.length ? val(classement[classement.length - 1].valeur, defCarte?.unite) : "—"}
                  </span>
                  <span className="flex items-center gap-1.5 ml-auto text-[10.5px] text-t3">
                    <span className="w-2.5 h-2.5 rounded" style={{ background: NEUTRE }} />
                    non mesuré
                  </span>
                </div>
                <div className="flex justify-between text-[10px] text-t2 mt-1"
                     style={{ maxWidth: 5 * 36 + 90 }}>
                  <span>le plus favorable</span><span>le moins favorable</span>
                </div>
                <p className="text-[11px] text-t2 mt-2 leading-relaxed">
                  {defCarte?.sens === 1
                    ? "Pour cet indicateur, une valeur élevée est favorable."
                    : "Pour cet indicateur, une valeur élevée signale une situation plus difficile."}
                  {" "}Les territoires comparés sont entourés d'un trait sombre et nommés.
                </p>
              </div>
            </Carte>

            <Carte titre="Rang de chaque territoire" Icon={ChartNoAxesColumn} couleurIcone={NAVY}
                   but="Position dans l'ensemble de référence, indicateur par indicateur. Le rang 1 est toujours le plus favorable.">
              <div className="overflow-y-auto -mx-1 px-1" style={{ maxHeight: 380 }}>
                <table className="w-full text-[11.5px]">
                  <thead>
                    <tr className="border-b-2 border-line">
                      <th className="text-left font-bold text-t2 py-2">Indicateur</th>
                      {data.territoires.map((t) => (
                        <th key={t.territoire_id} className="text-right font-bold py-2 pl-2">
                          {court(t.nom)}
                        </th>))}
                    </tr>
                  </thead>
                  <tbody>
                    {defs.map((d) => (
                      <tr key={d.cle} className="border-b border-line last:border-0">
                        <td className="py-2 pr-2 text-t1">{d.label}</td>
                        {data.territoires.map((t) => {
                          const r = data.rangs?.[String(t.territoire_id)]?.[d.cle];
                          return (
                            <td key={t.territoire_id} className="text-right py-2 pl-2">
                              <Rang rang={r?.rang} total={r?.total} />
                            </td>);
                        })}
                      </tr>))}
                  </tbody>
                </table>
              </div>
            </Carte>
          </div>

          {/* ================= ÉCARTS ================= */}
          <TitreSection Icon={TriangleAlert} titre="Écarts les plus marquants"
                        note="triés par ampleur relative" />
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 items-stretch">
            {(data.ecarts || []).slice(0, 6).map((e) => (
              <div key={e.cle} className="bg-surface border border-line rounded-2xl p-4">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[13px] font-bold text-navy">{e.label}</span>
                  <span className="text-[10px] font-semibold text-t3 bg-bg px-2 py-0.5 rounded shrink-0">
                    {e.theme}
                  </span>
                </div>
                <div className="text-[22px] font-extrabold text-violet mt-2">
                  {e.unite === "%" ? `${dec(e.ecart)} pts` : nb(e.ecart)}
                </div>
                <div className="text-[10.5px] text-t2">d'écart</div>
                <div className="mt-3 space-y-1.5">
                  <div className="flex items-center gap-2 text-[11.5px]">
                    <ArrowUp size={13} className="text-[#16a34a] shrink-0" />
                    <span className="flex-1 truncate">{court(nomDe(e.meilleur.territoire_id))}</span>
                    <b>{val(e.meilleur.valeur, e.unite)}</b>
                  </div>
                  <div className="flex items-center gap-2 text-[11.5px]">
                    <ArrowDown size={13} className="text-[#e5484d] shrink-0" />
                    <span className="flex-1 truncate">{court(nomDe(e.pire.territoire_id))}</span>
                    <b>{val(e.pire.valeur, e.unite)}</b>
                  </div>
                </div>
              </div>))}
          </div>

          {/* ================= PROFIL PAR THÈME ================= */}
          <TitreSection Icon={ChartNoAxesColumn} titre="Le détail par thème"
                        note="choisissez un thème" />
          <div className="bg-surface border border-line rounded-2xl p-4">
            <div className="flex flex-wrap items-center gap-2 mb-4">
              {themes.map((t) => (
                <button key={t} onClick={() => setTheme(t)}
                  className={`text-[12px] font-semibold px-3.5 py-2 rounded-lg transition-colors ${
                    themeActif === t ? "bg-navy text-white" : "bg-bg text-t2 hover:text-navy"}`}>
                  {t}
                </button>))}
            </div>

            {verdictTheme && verdictTheme.combien > 0 && (
              <div className="flex gap-3 items-start bg-bg rounded-xl px-4 py-3 mb-4">
                <TriangleAlert size={17} className="text-[#a9670a] shrink-0 mt-0.5" />
                <p className="text-[12.5px] leading-relaxed">
                  Sur ce thème, <b>{court(nomDe(verdictTheme.tid))}</b> est en retrait sur{" "}
                  <b>{verdictTheme.combien} indicateur{verdictTheme.combien > 1 ? "s" : ""} sur{" "}
                  {verdictTheme.total}</b>.
                  {verdictTheme.principal && (
                    <> L'écart le plus fort porte sur <b>{verdictTheme.principal.label.toLowerCase()}</b> :{" "}
                    {val(verdictTheme.principal.pire.valeur, verdictTheme.principal.unite)} contre{" "}
                    {val(verdictTheme.principal.meilleur.valeur, verdictTheme.principal.unite)} à{" "}
                    {court(nomDe(verdictTheme.principal.meilleur.territoire_id))}.</>
                  )}
                </p>
              </div>
            )}

            {(
              <>
                <p className="text-[11.5px] text-t2 mb-3">
                  La flèche indique le sens de lecture :
                  <ArrowDown size={12} className="inline mx-1 text-t3" />une valeur basse est
                  souhaitable, <ArrowUp size={12} className="inline mx-1 text-t3" />une valeur haute
                  l'est. La couleur d'une barre dit sa performance ; la pastille à droite donne le
                  rang parmi les {Object.keys(data.reference).length}{" "}
                  {data.niveau === "commune" ? "communes" : "provinces"} de la région.
                </p>
                <div className="space-y-4">
                  {indicateursTheme.map((d) => {
                    const lignes = data.territoires.map((t) => {
                      const rang = data.rangs?.[String(t.territoire_id)]?.[d.cle];
                      return {
                        nom: court(t.nom),
                        valeur: data.valeurs?.[d.cle]?.[String(t.territoire_id)] ?? null,
                        couleur: couleurRang(rang?.rang, rang?.total),
                        rang,
                      };
                    }).filter((l) => l.valeur != null);
                    if (!lignes.length) return null;
                    const maxi = Math.max(...lignes.map((l) => l.valeur));
                    return (
                      <div key={d.cle}>
                        <div className="flex items-center gap-1.5 mb-1.5">
                          {d.sens === 1
                            ? <ArrowUp size={13} className="text-t3" />
                            : <ArrowDown size={13} className="text-t3" />}
                          <span className="text-[12px] font-bold text-navy">{d.label}</span>
                        </div>
                        <div className="space-y-1.5">
                          {lignes.map((l) => (
                            <div key={l.nom} className="flex items-center gap-2.5">
                              <span className="w-24 text-[11px] text-t2 truncate shrink-0">{l.nom}</span>
                              <span className="flex-1 h-5 bg-bg rounded-md overflow-hidden">
                                <span className="block h-full rounded-md transition-all"
                                      style={{ width: `${maxi ? (l.valeur / maxi) * 100 : 0}%`,
                                               background: l.couleur }} />
                              </span>
                              <span className="w-20 text-right text-[11.5px] font-bold shrink-0">
                                {val(l.valeur, d.unite)}
                              </span>
                              <span className="w-12 text-right shrink-0">
                                <Rang rang={l.rang?.rang} total={l.rang?.total} />
                              </span>
                            </div>))}
                        </div>
                      </div>);
                  })}
                </div>
              </>
            )}
          </div>

          {/* ================= TABLEAU COMPLET ================= */}
          <div className="flex items-center gap-2.5 mt-7 mb-3.5">
            <Table2 size={19} className="text-navy" />
            <h2 className="text-base font-extrabold text-navy">Tableau comparatif</h2>
            <span className="text-[11.5px] text-t2 ml-auto mr-3">
              vert = le mieux placé · rouge = le moins bien
            </span>
            <BoutonExport
              nom={`comparaison_${data.territoires.map((t) => court(t.nom)).join("_")}`}
              donnees={donneesExport} />
          </div>
          <div className="bg-surface border border-line rounded-2xl p-4 overflow-x-auto">
            <table className="w-full text-[12.5px]">
              <thead>
                <tr className="border-b-2 border-line">
                  <th className="text-left font-bold text-t2 py-2.5">Indicateur</th>
                  {data.territoires.map((t) => (
                    <th key={t.territoire_id} className="text-right font-bold py-2.5 px-3">
                      {court(t.nom)}
                    </th>))}
                  <th className="text-right font-bold text-t2 py-2.5">Écart</th>
                </tr>
              </thead>
              <tbody>
                {/* Fragment nommé et non « <> » : une liste a besoin d'une clé,
                    et la syntaxe courte ne peut pas en porter. */}
                {themes.map((th) => (
                  <Fragment key={th}>
                    <tr>
                      <td colSpan={data.territoires.length + 2}
                          className="bg-bg text-[10.5px] uppercase tracking-wider font-bold
                                     text-navy py-1.5 px-2 rounded">
                        {th}
                      </td>
                    </tr>
                    {defs.filter((d) => d.theme === th).map((d) => {
                      const e = (data.ecarts || []).find((x) => x.cle === d.cle);
                      return (
                        <tr key={d.cle} className="border-b border-line last:border-0">
                          <td className="py-2.5 pr-2">{d.label}
                            {d.unite === "" && <span className="text-t3 font-normal"> (hab.)</span>}
                          </td>
                          {data.territoires.map((t) => {
                            const v = data.valeurs?.[d.cle]?.[String(t.territoire_id)];
                            const estMeilleur = e && String(t.territoire_id) === e.meilleur.territoire_id;
                            const estPire = e && String(t.territoire_id) === e.pire.territoire_id;
                            return (
                              <td key={t.territoire_id} className="text-right py-2.5 px-3">
                                <span className={`inline-block px-2 py-1 rounded-md font-bold ${
                                  estMeilleur ? "bg-[#e7f6ec] text-[#0e7a34]"
                                  : estPire ? "bg-[#fdeaea] text-[#b02121]" : ""}`}>
                                  {val(v, d.unite)}
                                </span>
                              </td>);
                          })}
                          <td className="text-right py-2.5 font-bold text-violet">
                            {e ? (d.unite === "%" ? `${dec(e.ecart)} pts` : nb(e.ecart)) : "—"}
                          </td>
                        </tr>);
                    })}
                  </Fragment>))}
              </tbody>
            </table>
          </div>

          {/* ================= SOURCES ================= */}
          {data.sources && (
            <div className="mt-6 bg-surface border border-line rounded-2xl p-4">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-t3 mb-2">
                Sources
              </div>
              <ul className="space-y-1">
                {[...new Map(
                  Object.values(data.sources).flat().map((s) => [s.source, s])
                ).values()].map((s, i) => (
                  <li key={i} className="text-[10.5px] text-t2 leading-relaxed flex gap-1.5">
                    <span className="text-t3 shrink-0">•</span>
                    <span>{s.source}{s.annee && <span className="text-t3"> — {s.annee}</span>}</span>
                  </li>))}
              </ul>
            </div>
          )}

          <p className="text-[11px] text-t3 text-center mt-5 leading-relaxed">
            La comparaison se fait <b>entre pairs de même niveau</b>. Les couleurs du tableau
            désignent le mieux et le moins bien placé <b>parmi les seuls territoires comparés</b> ;
            les rangs, eux, situent chaque territoire dans l'ensemble de la région.
          </p>
        </>
      )}
    </DashboardLayout>
  );
}
