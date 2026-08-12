// Fiche territoriale — version pilotée par le catalogue.
//
// Ce que cette page change par rapport à FicheTerritorialePage : aucun
// indicateur n'y est nommé. Elle demande au backend la STRUCTURE (/familles)
// puis les CHIFFRES (/valeurs), et dessine ce qu'on lui décrit. Ajouter un
// indicateur au catalogue le fait apparaître ici sans toucher à ce fichier.
//
// Organisation :
//   1. Identité du territoire et sélecteurs de niveau
//   2. L'essentiel — quatre repères, avec le rang parmi les PAIRS
//      (provinces entre elles, communes d'une même province entre elles) et
//      jamais face à une moyenne régionale, qui englobe le territoire lui-même
//   3. Explorateur — catalogue à gauche, Carte / Tableau / Synthèse au centre,
//      réglages à droite : la disposition de l'explorateur du site officiel,
//      adaptée au cas d'une fiche, qui suit UN territoire et pas seulement
//      un indicateur
//   4. Détail par secteur — une carte par famille, avec sa source et son millésime
//
// Aucun calcul n'est fait ici : les valeurs sont affichées telles que la base
// les livre. Les seules opérations sont des rangs, des médianes et des parts
// de répartition, toutes explicites à l'écran.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Users, BriefcaseBusiness, GraduationCap, HeartPulse, House,
  Search, Check, Plus, Layers, SlidersHorizontal,
} from "lucide-react";
import DashboardLayout from "../../components/DashboardLayout";
import BarreExport from "../../components/BarreExport";
import CarteIndicateur, { FONDS } from "../../components/fiche/CarteIndicateur";
import { Graphique } from "../../components/fiche/Graphiques";
import { getFamilles, getValeurs } from "../../api/ficheNouvelle";
import {
  SECTEURS, COUL, JUGE, RAMPES, nb, dec, med, court, sourceCourte,
  serieDe, valeur, cleFamille, ordinal, classer, classeDe, teintes,
} from "../../components/fiche/outils";

const ICONES = {
  "Démographie": Users,
  "Emploi": BriefcaseBusiness,
  "Éducation": GraduationCap,
  "Santé": HeartPulse,
  "Conditions de vie": House,
};

// Les quatre repères de « L'essentiel ». C'est la seule liste d'indicateurs
// écrite en dur de toute la page, et elle est assumée : un tableau de bord doit
// ouvrir sur quelque chose, et ce quelque chose relève d'un choix éditorial,
// pas d'une règle automatique. Toute famille absente est simplement omise.
const REPERES = [
  { nom: "Population légale", etiquette: "2024", libelle: "Population légale" },
  { nom: "Taux de chômage", libelle: "Taux de chômage", seuil: [10, 16] },
  { nom: "Taux d'analphabétisme des 15 ans et plus", libelle: "Analphabétisme 15 ans et plus", seuil: [20, 32] },
  { nom: "Taux d'activité des 15 ans et plus", libelle: "Taux d'activité", seuil: [45, 38] },
];

// Rang d'une valeur parmi ses pairs, dans le sens que le catalogue déclare.
// Pour un taux de chômage (bas_mieux), être 1ᵉʳ c'est avoir le taux le plus
// bas. Pour un effectif (neutre), le rang n'est qu'un ordre de grandeur : on
// classe par valeur décroissante et on le dit.
function rangDe(v, liste, sens) {
  if (v == null || !liste.length) return null;
  const tri = [...liste].sort((a, b) => (sens === "bas_mieux" ? a - b : b - a));
  return tri.indexOf(v) + 1;
}

export default function FicheNouvellePage() {
  /* ---------------------------------------------------------------- données */
  const [familles, setFamilles] = useState({ prefecture_province: [], commune: [] });
  const [dProv, setDProv] = useState(null);
  const [dComm, setDComm] = useState(null);
  const [geo, setGeo] = useState({ provinces: null, communes: null });
  const [erreur, setErreur] = useState(null);
  const [chargement, setChargement] = useState(true);

  /* ------------------------------------------------------------- affichage */
  const [niveau, setNiveau] = useState("prefecture_province");
  const [provinceId, setProvinceId] = useState(null);
  const [communeId, setCommuneId] = useState(null);
  const [secteur, setSecteur] = useState("Démographie");
  const [ind, setInd] = useState(null);          // { nom, secteur, mi }
  const [vent, setVent] = useState({});          // { clé de famille : modalité }
  const [q, setQ] = useState("");
  const [vue, setVue] = useState("carte");       // carte | tableau | synthese
  const cadreCarte = useRef(null);               // ce qu'on rastérise à l'export
  const carteLeaflet = useRef(null);             // pour projeter à l'export
  // Opacité par défaut : 0,72 et non 0,88.
  // Le masque recouvre tout ce qui entoure la région — c'est lui qui supprime
  // les frontières nationales des fonds de plan. Mais des aplats presque
  // opaques rendaient du même coup le fond invisible À L'INTÉRIEUR, où il n'y a
  // aucune frontière et où il apporte le littoral, les routes et les villes.
  // À 0,72 les trois fonds redeviennent distincts sans que les classes de
  // couleur cessent d'être comparables ; la réglette permet d'ajuster.
  const [reglages, setReglages] = useState({
    methode: "Quantiles", classes: 5, opacite: 0.72, fond: "Clair", etiquettes: false,
  });

  /* ----------------------------------------------------- premier chargement */
  useEffect(() => {
    let vivant = true;
    Promise.all([
      getFamilles("prefecture_province"),
      getFamilles("commune"),
      getValeurs("prefecture_province"),
      fetch("/geo/provinces.geojson").then((r) => r.json()),
      fetch("/geo/communes.geojson").then((r) => r.json()),
    ])
      .then(([fp, fc, vp, gp, gc]) => {
        if (!vivant) return;
        setFamilles({ prefecture_province: fp, commune: fc });
        setDProv(vp);
        setGeo({ provinces: gp, communes: gc });
        setProvinceId(Object.keys(vp.territoires).sort((a, b) =>
          vp.territoires[a].localeCompare(vp.territoires[b], "fr"))[0]);
        setChargement(false);
      })
      .catch((e) => { if (vivant) { setErreur(e.message || "Chargement impossible."); setChargement(false); } });
    return () => { vivant = false; };
  }, []);

  /* ------------------ valeurs communales : rechargées à chaque province ----- */
  useEffect(() => {
    if (niveau !== "commune" || !provinceId) return;
    let vivant = true;
    setDComm(null);
    getValeurs("commune", provinceId)
      .then((d) => {
        if (!vivant) return;
        setDComm(d);
        setCommuneId(Object.keys(d.territoires).sort((a, b) =>
          d.territoires[a].localeCompare(d.territoires[b], "fr"))[0]);
      })
      .catch((e) => vivant && setErreur(e.message));
    return () => { vivant = false; };
  }, [niveau, provinceId]);

  /* -------------------------------------------------------------- dérivés */
  const donnees = niveau === "commune" ? dComm : dProv;
  const catalogue = familles[niveau] || [];
  const autre = niveau === "commune" ? "prefecture_province" : "commune";

  // Les familles publiées à l'autre niveau seulement. Les nommer est une
  // exigence : une absence de donnée doit se voir, sinon elle se lit comme un
  // zéro. C'est la même règle que celle appliquée dans l'entrepôt.
  const absentes = useMemo(() => {
    const ici = new Set(catalogue.map(cleFamille));
    return (familles[autre] || []).filter((f) => !ici.has(cleFamille(f)));
  }, [catalogue, familles, autre]);

  const moi = niveau === "commune" ? communeId : provinceId;
  const pairs = useMemo(() => (donnees ? Object.keys(donnees.territoires) : []), [donnees]);
  const nomDe = (id) => donnees?.territoires?.[String(id)] || "";
  const val = (indicateurId, territoire, cle) =>
    valeur(donnees?.valeurs, indicateurId, territoire, vent[cle]);

  useEffect(() => {
    if (!catalogue.length || ind) return;
    const d = catalogue.find((f) => f.nom === "Taux de chômage") || catalogue[0];
    setInd({ nom: d.nom, secteur: d.secteur, mi: 0 });
  }, [catalogue, ind]);

  const famCarte = useMemo(
    () => (ind ? catalogue.find((f) => f.nom === ind.nom && f.secteur === ind.secteur) : null),
    [ind, catalogue]);
  const membreCarte = famCarte
    ? famCarte.membres[Math.min(ind.mi, famCarte.membres.length - 1)] : null;

  const serieCarte = useMemo(() => {
    if (!membreCarte || !donnees) return {};
    const out = {};
    pairs.forEach((t) => {
      const v = val(membreCarte.indicateur_id, t, famCarte && cleFamille(famCarte));
      if (v != null) out[t] = v;
    });
    return out;
  }, [membreCarte, donnees, pairs, vent]);

  const fc = useMemo(() => {
    const src = niveau === "commune" ? geo.communes : geo.provinces;
    if (!src || !pairs.length) return null;
    const ids = new Set(pairs.map(String));
    return {
      type: "FeatureCollection",
      features: src.features
        .filter((f) => ids.has(String(f.properties.territoire_id)))
        .map((f) => ({
          type: "Feature",
          properties: { id: String(f.properties.territoire_id) },
          geometry: f.geometry,
        })),
    };
  }, [geo, niveau, pairs]);

  /* ----------------------------------------------------------------- actions */
  const ouvrirTerritoire = (id) =>
    niveau === "commune" ? setCommuneId(String(id)) : setProvinceId(String(id));
  const choisirIndicateur = (f) => setInd({ nom: f.nom, secteur: f.secteur, mi: 0 });
  function porterSurCarte(f) {
    choisirIndicateur(f);
    setVue("carte");
    document.getElementById("explorateur")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /* ------------------------------------------------------------------ export */
  // Ce que l'image de la carte doit emporter avec elle. Une carte sortie nue
  // de l'écran ne dit ni ce qu'elle représente, ni de quand elle date, ni d'où
  // viennent ses chiffres : elle devient invérifiable dès qu'elle est collée
  // dans une note ou une présentation.
  function infosCarte() {
    if (vue !== "carte" || !famCarte || !carteLeaflet.current) return null;
    const vs = Object.values(serieCarte);
    if (!vs.length) return null;
    const bornes = classer(vs, reglages.classes, reglages.methode);
    const palette = teintes(bornes.length + 1, famCarte.secteur);
    const d = dec(vs);
    return {
      titre: famCarte.membres.length > 1
        ? `${famCarte.nom} — ${membreCarte.etiquette}` : famCarte.nom,
      sousTitre: `${niveau === "commune"
        ? `Communes de ${dProv?.territoires?.[String(provinceId)] || ""}`
        : "Préfectures et provinces"} · ${famCarte.annee} · ${famCarte.unite || "—"}`,
      palette,
      bornes: { min: nb(Math.min(...vs), d), max: nb(Math.max(...vs), d) },
      titreLegende: famCarte.membres.length > 1 ? membreCarte.etiquette : famCarte.nom,
      note: `Classification par ${reglages.methode.toLowerCase()} · ${bornes.length + 1} classes`,
      sousNote: `${famCarte.annee} · ${vs.length} territoires · ${famCarte.unite || "—"}`,
      source: famCarte.source,
      attribution: (FONDS[reglages.fond] || FONDS.Clair)[1],
      // De quoi redessiner la carte à l'identique, sans capture d'écran.
      // Le satellite ne trace pas de frontières : il n'est pas masqué ici non plus.
      carteLeaflet: carteLeaflet.current,
      geojson: fc,
      masque: reglages.fond === "Satellite" ? null
            : reglages.fond === "Sombre" ? "#12192b" : "#f4f6fa",
      styleDe: (id) => {
        const v = serieCarte[String(id)];
        const ouvert = String(id) === String(moi);
        return {
          // Une absence de donnée reste grise : ce n'est pas un zéro.
          fond: v == null ? "#dde3ec" : palette[classeDe(v, bornes)],
          opacite: reglages.opacite,
          trait: ouvert ? "#f0a92c" : "#ffffff",
          epaisseur: ouvert ? 3 : 1,
        };
      },
      etiquetteDe: reglages.etiquettes
        ? (id) => (serieCarte[String(id)] == null ? null : nb(serieCarte[String(id)], d))
        : null,
      echelle: 2,
    };
  }

  // Les valeurs partent en NOMBRES, pas en texte déjà mis en forme : le CSV les
  // écrira avec une virgule, le classeur Excel les gardera sommables.
  function lignesExport() {
    const colonnes = ["Secteur", "Indicateur", "Modalité", "Unité", "Millésime",
                      "Valeur", "Rang", "Pairs", "Source"];
    const lignes = [];
    const parSecteur = {};
    catalogue.forEach((f) => {
      const cle = cleFamille(f);
      f.membres.forEach((m) => {
        const v = val(m.indicateur_id, moi, cle);
        if (v == null) return;
        const l = pairs.map((t) => val(m.indicateur_id, t, cle)).filter((x) => x != null);
        const ligne = [f.secteur, f.nom, f.membres.length > 1 ? m.etiquette : "",
                       f.unite || "", f.annee || "", v,
                       rangDe(v, l, f.sens) ?? "", l.length, f.source || ""];
        lignes.push(ligne);
        (parSecteur[f.secteur] ||= []).push(ligne);
      });
    });
    return {
      colonnes, lignes,
      // Un onglet par secteur : deux cents lignes d'un bloc ne se lisent pas,
      // et c'est par secteur qu'on travaille.
      feuilles: SECTEURS.filter((s) => parSecteur[s]?.length)
        .map((s) => ({ nom: s, colonnes, lignes: parSecteur[s] })),
      entete: [
        `Fiche territoriale — ${nomDe(moi)}`,
        `${lignes.length} valeurs · comparaison avec ${Math.max(0, pairs.length - 1)} `
        + `territoires de même niveau`,
        "Le rang suit le sens déclaré au catalogue. Une valeur absente n'est jamais un zéro.",
      ],
    };
  }

  /* ------------------------------------------------------------------- rendu */
  if (chargement)
    return <DashboardLayout title="Fiche territoriale" active="fiche">
      <p className="text-t2 text-sm">Chargement du catalogue…</p></DashboardLayout>;
  if (erreur)
    return <DashboardLayout title="Fiche territoriale" active="fiche">
      <p className="text-coral text-sm">{erreur}</p></DashboardLayout>;

  const nomProvince = dProv?.territoires?.[String(provinceId)] || "";
  const accentCarte = famCarte ? COUL[famCarte.secteur].t : "#001f5f";

  return (
    <DashboardLayout title="Fiche territoriale" active="fiche"
                     territoire={court(nomDe(moi)) || null}>

      {/* ═══════════════════════════ 1 · IDENTITÉ ═══════════════════════════ */}
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <div className="text-[11px] font-extrabold uppercase tracking-[0.12em] text-t3">
            Région Tanger–Tétouan–Al Hoceïma
            {niveau === "commune" && nomProvince ? ` · ${nomProvince}` : ""}
          </div>
          <h1 className="text-[42px] font-extrabold text-navy leading-[1.05] mt-1.5">
            {court(nomDe(moi)) || "—"}
          </h1>
          <div className="text-[13px] text-t2 mt-2">
            {catalogue.length} objets d'information · comparé à {Math.max(0, pairs.length - 1)}{" "}
            {niveau === "commune" ? "communes de la même province" : "préfectures et provinces"}
          </div>
        </div>

        {/* Sélecteurs et boutons : outils de pilotage, sans objet sur le papier. */}
        <div className="flex flex-wrap items-center gap-2 ecran-seul">
          <Choix value={niveau} onChange={(v) => { setNiveau(v); setInd(null); }}>
            <option value="prefecture_province">Niveau préfecture / province</option>
            <option value="commune">Niveau commune</option>
          </Choix>

          <Choix value={provinceId || ""} onChange={setProvinceId}>
            {Object.keys(dProv?.territoires || {})
              .sort((a, b) => dProv.territoires[a].localeCompare(dProv.territoires[b], "fr"))
              .map((id) => <option key={id} value={id}>{dProv.territoires[id]}</option>)}
          </Choix>

          {/* Au niveau communal on choisit d'abord la province, puis la commune :
              c'est ce qui garantit que la comparaison ne mêle jamais deux
              provinces. */}
          {niveau === "commune" && (
            <Choix value={communeId || ""} onChange={setCommuneId} disabled={!dComm}>
              {Object.keys(dComm?.territoires || {})
                .sort((a, b) => dComm.territoires[a].localeCompare(dComm.territoires[b], "fr"))
                .map((id) => <option key={id} value={id}>{court(dComm.territoires[id])}</option>)}
            </Choix>
          )}

          {/* En-tête de page : les données. L'export d'image vit au-dessus de
              la carte, puisqu'il ne saisit qu'elle. */}
          <BarreExport nom={`fiche_${court(nomDe(moi))}`} donnees={lignesExport}
                       carte={infosCarte} formats={["csv", "xlsx", "imprimer"]}
                       titreImpression={`Fiche territoriale — ${court(nomDe(moi))}`} />
        </div>
      </div>

      {/* ═══════════════════════════ 2 · L'ESSENTIEL ════════════════════════ */}
      <Bloc titre="L'essentiel" note="rang parmi les territoires de même niveau">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-[18px]">
          {REPERES.map((r, i) => {
            const f = catalogue.find((x) => x.nom === r.nom);
            if (!f) return null;
            const cle = cleFamille(f);
            // On demande un millésime précis, mais on ne s'y enferme pas : si ce
            // membre n'a pas de valeur ici — parce qu'il a été renommé, masqué,
            // ou qu'il ne descend pas à ce niveau — on prend le premier membre
            // de la famille qui en a une. Un repère de tête ne doit pas afficher
            // « non disponible » quand la donnée existe à côté.
            const souhaite = r.etiquette && f.membres.find((x) => x.etiquette === r.etiquette);
            const m = [souhaite, ...f.membres].find(
              (x) => x && val(x.indicateur_id, moi, cle) != null) || f.membres[0];
            const v = val(m.indicateur_id, moi, cle);
            const l = pairs.map((t) => val(m.indicateur_id, t, cle)).filter((x) => x != null);
            const rang = rangDe(v, l, f.sens);

            // Le voyant n'apparaît que si le catalogue déclare un sens : un
            // effectif n'est ni bon ni mauvais, le colorer serait un jugement.
            let signal = null;
            if (v != null && r.seuil && f.sens !== "neutre") {
              const [bon, moyen] = r.seuil;
              signal = f.sens === "haut_mieux"
                ? (v >= bon ? "bon" : v >= moyen ? "moyen" : "mauvais")
                : (v <= bon ? "bon" : v <= moyen ? "moyen" : "mauvais");
            }

            return (
              <button key={r.nom} onClick={() => porterSurCarte(f)}
                className="card-orvsit survolable monter text-left px-6 py-5"
                style={{ "--accent": signal ? JUGE[signal] : COUL[f.secteur].t,
                         "--retard": `${i * 0.05}s` }}>
                <div className="text-[10px] font-extrabold uppercase tracking-[0.09em] text-t2">
                  {r.libelle}
                </div>
                <div className="text-[36px] font-extrabold text-navy mt-3 leading-none
                                tracking-[-0.05em] tabular-nums">
                  {nb(v, dec(l.length ? l : [v]))}
                  <small className="text-[16px] font-bold ml-1.5">{f.unite || ""}</small>
                </div>
                <div className="text-[12px] text-t2 mt-2.5">
                  {rang
                    ? <>{rang}<sup>{ordinal(rang)}</sup> sur {l.length}{" "}
                        {niveau === "commune" ? "communes" : "territoires"}
                        {f.sens === "neutre" && <span className="text-t3"> · par valeur décroissante</span>}</>
                    : "non disponible"}
                </div>
              </button>
            );
          })}
        </div>
      </Bloc>

      {/* ══════════════════════════ 3 · EXPLORATEUR ═════════════════════════ */}
      <section id="explorateur" className="card-orvsit p-5 mb-4" style={{ "--accent": accentCarte }}>
        <div className="flex flex-wrap items-center gap-3 mb-4 pl-2">
          <div>
            <h2 className="text-[17px] font-extrabold text-navy">Explorateur territorial</h2>
            <p className="text-[11.5px] text-t2 mt-0.5">
              choisissez un indicateur à gauche · cliquez un territoire pour ouvrir sa fiche
            </p>
          </div>

          {/* Contrôle segmenté du site officiel : fond #eef2f8, rayon 13, et
              pour l'onglet actif un aplat navy porté par une ombre basse. */}
          <div className="ml-auto flex gap-[5px] p-1 bg-[#eef2f8] rounded-[13px] ecran-seul">
            {[["carte", "Carte"], ["tableau", "Tableau"], ["synthese", "Synthèse"]].map(([k, l]) => (
              <button key={k} onClick={() => setVue(k)}
                className={`text-[12px] font-extrabold px-4 py-2.5 rounded-[10px] transition-all ${
                  vue === k ? "bg-navy text-white shadow-[0_5px_14px_rgba(0,31,95,.18)]"
                            : "text-[#56627a] hover:text-navy"}`}>
                {l}
              </button>
            ))}
          </div>
        </div>

        {/* Les trois colonnes partagent une hauteur unique : sans elle, la carte
            s'arrêtait au-dessus du bas du panneau voisin et laissait une bande
            blanche dans la carte-conteneur. */}
        {/* minmax(0,…) et non 1fr : une colonne 1fr ne descend pas sous la
            largeur minimale de son contenu. Le tableau, plus large que la
            place disponible, poussait donc la colonne des réglages hors de
            l'écran au lieu de défiler dans son cadre. */}
        <div className="grid grid-cols-1 xl:grid-cols-[260px_minmax(0,1fr)_270px] gap-3 xl:h-[620px]">

          {/* ---------------------------- catalogue --------------------------- */}
          <div className="bg-bg rounded-[18px] overflow-hidden flex flex-col max-h-[620px]
                          xl:h-full ecran-seul">
            <div className="px-3.5 py-3 border-b border-line">
              <div className="flex items-center gap-1.5 text-[10px] font-extrabold uppercase
                              tracking-[0.11em] text-t2 mb-2.5">
                <Layers size={12} /> Catalogue des indicateurs
                <span className="ml-auto text-navy">{catalogue.length}</span>
              </div>
              <div className="relative">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-t3" />
                <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher…"
                  className="w-full bg-white border border-line rounded-[10px] pl-8 pr-2 py-2
                             text-[12px] outline-none focus:border-navy-3 transition-colors" />
              </div>
            </div>
            <div className="overflow-y-auto flex-1 px-2 py-2 defil-fin">
              {SECTEURS.map((s) => {
                const garde = (f) => !q || f.nom.toLowerCase().includes(q.trim().toLowerCase());
                const l = catalogue.filter((f) => f.secteur === s && garde(f));
                const abs = absentes.filter((f) => f.secteur === s && garde(f));
                if (!l.length && !abs.length) return null;
                const c = COUL[s];
                const Icone = ICONES[s];
                const contientActif = l.some((f) => ind?.nom === f.nom && ind?.secteur === f.secteur);
                return (
                  <details key={s} open={contientActif || !!q} className="mb-1">
                    <summary className="flex items-center gap-2 text-[12px] font-extrabold cursor-pointer
                                        py-2 px-1.5 rounded-[10px] hover:bg-white transition-colors"
                             style={{ color: c.s }}>
                      <span className="w-6 h-6 rounded-lg grid place-items-center shrink-0"
                            style={{ background: c.f, color: c.t }}><Icone size={13} /></span>
                      {s}
                      <span className="ml-auto text-[10px] text-t3">{l.length}</span>
                    </summary>
                    {l.map((f) => {
                      const actif = ind?.nom === f.nom && ind?.secteur === f.secteur;
                      return (
                        <div key={cleFamille(f)} onClick={() => choisirIndicateur(f)}
                          className={`flex items-center gap-2 px-2 py-2 rounded-[10px] cursor-pointer
                                      transition-colors ${actif ? "bg-white ombre-orvsit" : "hover:bg-white/70"}`}>
                          <div className="flex-1 min-w-0">
                            <div className="text-[11.5px] font-bold text-t1 truncate">{f.nom}</div>
                            <div className="text-[9.5px] text-t3">
                              {f.annee} · {f.unite || "—"}
                              {f.membres.length > 1 && ` · ${f.membres.length} mod.`}
                            </div>
                          </div>
                          <span className="w-[18px] h-[18px] rounded-md grid place-items-center shrink-0"
                                style={{ background: actif ? c.t : "#dde4ee",
                                         color: actif ? "#fff" : "#7a8499" }}>
                            {actif ? <Check size={11} strokeWidth={3.2} /> : <Plus size={11} />}
                          </span>
                        </div>
                      );
                    })}
                    {/* Les objets publiés à l'autre niveau, montrés seulement en
                        recherche : les citer en permanence noierait la liste. */}
                    {q && abs.slice(0, 12).map((f) => (
                      <div key={`abs-${cleFamille(f)}`} className="px-2 py-1.5 opacity-55">
                        <div className="text-[11.5px] text-t2 truncate">{f.nom}</div>
                        <span className="text-[9px] bg-white text-t3 rounded-full px-2 py-0.5">
                          {niveau === "commune" ? "province uniquement" : "commune uniquement"}
                        </span>
                      </div>
                    ))}
                  </details>
                );
              })}
            </div>
          </div>

          {/* ------------------------ carte / tableau / synthèse --------------- */}
          <div className="min-w-0 flex flex-col xl:h-full">
            {/* Bandeau d'identification de l'indicateur actif, commun aux trois vues */}
            <div className="flex flex-wrap items-center gap-2 mb-2.5">
              <div className="min-w-0">
                <div className="text-[15px] font-extrabold text-navy truncate flex items-center gap-2">
                  {famCarte ? famCarte.nom : "Choisissez un indicateur"}
                  {famCarte && famCarte.membres.length > 1 && (
                    <span className="text-[10px] font-extrabold uppercase tracking-[0.08em]
                                     px-2.5 py-[5px] rounded-full"
                          style={{ background: COUL[famCarte.secteur].f,
                                   color: COUL[famCarte.secteur].t }}>
                      {membreCarte.etiquette}
                    </span>
                  )}
                </div>
                {famCarte && (
                  <div className="text-[10.5px] text-t3 truncate">
                    {famCarte.secteur} · {famCarte.annee} · {famCarte.unite || "—"} ·{" "}
                    {sourceCourte(famCarte.source)}
                  </div>
                )}
              </div>
              <div className="ml-auto flex items-center gap-2">
                {famCarte && famCarte.membres.length > 1 && (
                  <Choix value={ind.mi} onChange={(v) => setInd({ ...ind, mi: +v })}>
                    {famCarte.membres.map((m, j) => (
                      <option key={m.indicateur_id} value={j}>{m.etiquette}</option>
                    ))}
                  </Choix>
                )}
                {/* L'export d'image est posé ici, contre la carte : c'est elle
                    seule qu'il saisit. Placé dans l'en-tête de page, il aurait
                    laissé croire qu'il capturait l'écran entier. */}
                {vue === "carte" && famCarte && (
                  <BarreExport nom={`fiche_${court(nomDe(moi))}`}
                               carte={infosCarte} formats={["png", "pdf"]} compact />
                )}
              </div>
            </div>

            {/* Le contenu est posé en absolu dans un cadre positionné. C'est ce
                qui rend le défilement fiable : « hauteur 100 % » ne s'applique
                qu'à un parent de hauteur définie, et le parent ici tient la
                sienne de la grille — d'où un tableau et une synthèse tronqués,
                sans ascenseur, dès que la liste dépassait le cadre. */}
            <div className="relative h-[440px] xl:h-auto xl:flex-1 xl:min-h-0">
              {vue === "carte" && (
                <div ref={cadreCarte} className="absolute inset-0">
                  <CarteIndicateur
                    geojson={fc} serie={serieCarte} secteur={famCarte?.secteur}
                    unite={famCarte?.unite}
                    territoireOuvert={moi} nomDe={nomDe} onSelect={ouvrirTerritoire}
                    surPret={(c) => { carteLeaflet.current = c; }}
                    {...reglages} />
                </div>
              )}
              {vue === "tableau" && (
                <div className="absolute inset-0 overflow-y-auto defil-fin">
                  <Tableau serie={serieCarte} nomDe={nomDe} moi={moi} famille={famCarte}
                           onSelect={ouvrirTerritoire} niveau={niveau} />
                </div>
              )}
              {vue === "synthese" && (
                <div className="absolute inset-0 overflow-y-auto defil-fin pr-1">
                  <Synthese serie={serieCarte} nomDe={nomDe} moi={moi} famille={famCarte}
                            onSelect={ouvrirTerritoire} niveau={niveau} reglages={reglages} />
                </div>
              )}
            </div>
          </div>

          {/* ----------------------------- réglages --------------------------- */}
          <div className="bg-bg rounded-[18px] p-4 max-h-[620px] xl:h-full overflow-y-auto
                          defil-fin ecran-seul">
            <Rubrique titre="Fonds de carte">
              <div className="grid grid-cols-3 gap-1">
                {Object.keys(FONDS).map((f) => (
                  <button key={f} onClick={() => setReglages({ ...reglages, fond: f })}
                    className={`text-[10.5px] font-extrabold py-2 rounded-[9px] transition-all ${
                      reglages.fond === f
                        ? "bg-navy text-white shadow-[0_5px_14px_rgba(0,31,95,.18)]"
                        : "bg-white text-t2 hover:text-navy"}`}>
                    {f}
                  </button>
                ))}
              </div>
            </Rubrique>

            <Rubrique titre="Carte thématique" icone={SlidersHorizontal}>
              <Champ label="Classification">
                <Choix pleine value={reglages.methode}
                       onChange={(v) => setReglages({ ...reglages, methode: v })}>
                  <option>Quantiles</option>
                  <option>Intervalles égaux</option>
                </Choix>
              </Champ>
              <Champ label="Nombre de classes">
                <Choix pleine value={reglages.classes}
                       onChange={(v) => setReglages({ ...reglages, classes: +v })}>
                  {[3, 4, 5, 6, 7].map((k) => <option key={k} value={k}>{k}</option>)}
                </Choix>
              </Champ>
              <Champ label="Opacité">
                <input type="range" min="0.4" max="1" step="0.02" value={reglages.opacite}
                  onChange={(e) => setReglages({ ...reglages, opacite: +e.target.value })}
                  className="w-full accent-navy" />
              </Champ>
              <label className="flex items-center gap-2 text-[11px] font-bold text-t2 cursor-pointer mt-3">
                <input type="checkbox" checked={reglages.etiquettes}
                  onChange={(e) => setReglages({ ...reglages, etiquettes: e.target.checked })}
                  className="accent-navy w-3.5 h-3.5" />
                Afficher les valeurs sur les territoires
              </label>
            </Rubrique>

            {/* Légende. Elle n'est écrite qu'ici : posée sur la carte, elle
                répétait la rampe et mangeait un coin du territoire.
                La palette n'est pas un réglage, elle est celle du secteur de
                l'indicateur — la couleur dit le domaine, jamais un jugement. */}
            {famCarte && <Legende famille={famCarte} membre={membreCarte} serie={serieCarte}
                                  pairs={pairs.length} reglages={reglages} />}
          </div>
        </div>
      </section>

      {/* ═══════════════════════ 4 · DÉTAIL PAR SECTEUR ═════════════════════ */}
      <Bloc titre="Détail par secteur" note="chaque carte porte sa source et son millésime">
        {/* Les onglets sont un moyen de navigation ; sur le papier, seul le
            secteur affiché part à l'impression, et son nom est déjà porté par
            les tags de chaque carte. */}
        <div className="flex flex-wrap gap-1.5 mb-5 ecran-seul">
          {SECTEURS.map((s) => {
            const n = catalogue.filter((f) => f.secteur === s).length;
            const c = COUL[s];
            const actif = s === secteur;
            const Icone = ICONES[s];
            return (
              <button key={s} onClick={() => setSecteur(s)}
                className="flex items-center gap-2 text-[12px] font-extrabold border rounded-full
                           px-4 py-2.5 transition-all"
                style={actif
                  ? { background: c.t, borderColor: c.t, color: "#fff",
                      boxShadow: `0 5px 14px ${c.t}33` }
                  : { background: "#fff", borderColor: "#e8ecf3", color: c.s }}>
                <Icone size={14} /> {s}
                <b className={`text-[10px] px-2 py-0.5 rounded-full ${actif ? "bg-white/20" : "bg-bg"}`}>
                  {n}
                </b>
              </button>
            );
          })}
        </div>
        <DetailSecteur
          catalogue={catalogue} absentes={absentes} secteur={secteur} niveau={niveau}
          donnees={donnees} pairs={pairs} moi={moi} vent={vent} setVent={setVent}
          onPorter={porterSurCarte} />
      </Bloc>
    </DashboardLayout>
  );
}

/* ═══════════════════════════════ petits blocs ═══════════════════════════════ */

function Bloc({ titre, note, children }) {
  return (
    <section className="bg-white border border-line rounded-3xl ombre-orvsit p-6 mb-4">
      <header className="flex flex-wrap items-baseline gap-3 mb-5">
        <h2 className="text-[17px] font-extrabold text-navy">{titre}</h2>
        {note && <span className="text-[11.5px] text-t3">{note}</span>}
      </header>
      {children}
    </section>
  );
}

function Choix({ value, onChange, children, disabled, pleine, className = "" }) {
  return (
    <select value={value} disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      className={`text-[12px] font-bold text-navy bg-white border border-line rounded-[10px]
                  px-3 py-2 outline-none focus:border-navy-3 transition-colors
                  disabled:opacity-50 ${pleine ? "w-full" : "max-w-[230px]"} ${className}`}>
      {children}
    </select>
  );
}

const Rubrique = ({ titre, icone: Icone, children }) => (
  <div className="mb-5 last:mb-0">
    <div className="flex items-center gap-1.5 text-[10px] font-extrabold uppercase
                    tracking-[0.11em] text-t2 mb-2.5">
      {Icone && <Icone size={11} />} {titre}
    </div>
    {children}
  </div>
);

const Champ = ({ label, children }) => (
  <div className="mb-2.5">
    <div className="text-[9.5px] font-bold uppercase tracking-[0.08em] text-t3 mb-1">{label}</div>
    {children}
  </div>
);

const Rien = ({ children }) => (
  <div className="bg-bg rounded-[18px] px-5 py-10 text-center text-[12px] text-t3">{children}</div>
);

/* ═══════════════════════════════════ légende ════════════════════════════════ */

function Legende({ famille, membre, serie, pairs, reglages }) {
  const vs = Object.values(serie);
  const bornes = classer(vs, reglages.classes, reglages.methode);
  const palette = teintes(bornes.length + 1, famille.secteur);
  const d = dec(vs);
  const manquants = pairs - vs.length;

  return (
    <Rubrique titre="Légende">
      {!vs.length ? (
        <p className="text-[11px] text-t3">Aucune valeur à ce niveau.</p>
      ) : (
        <>
          <div className="text-[11px] font-bold text-navy leading-snug mb-2">
            {famille.membres.length > 1 ? membre.etiquette : famille.nom}
          </div>
          <div className="flex h-2.5 rounded-full overflow-hidden">
            {palette.map((c, i) => <i key={i} className="flex-1" style={{ background: c }} />)}
          </div>
          <div className="flex justify-between text-[10px] font-bold text-t2 mt-1.5 tabular-nums">
            <span>{nb(Math.min(...vs), d)}</span>
            <span>{nb(Math.max(...vs), d)}</span>
          </div>
          <p className="text-[10px] text-t3 mt-2.5 leading-relaxed">
            {reglages.methode} · {bornes.length + 1} classes · {famille.unite || "—"} ·{" "}
            {vs.length} territoires
            {manquants > 0 && <><br />{manquants} sans donnée, affiché{manquants > 1 ? "s" : ""} en gris —
              une absence n'est pas un zéro.</>}
          </p>
        </>
      )}
    </Rubrique>
  );
}

/* ═══════════════════════════════════ tableau ════════════════════════════════ */

// Le tableau du site officiel affiche l'écart à la moyenne. On lui préfère la
// médiane : sur huit territoires très inégaux, la moyenne est tirée vers le
// haut par Tanger-Assilah et ne décrit pas le groupe. Les deux repères sont
// donnés dans la synthèse, l'écart affiché ici est nommé sans ambiguïté.
function Tableau({ serie, nomDe, moi, famille, onSelect, niveau }) {
  if (!famille) return <Rien>Choisissez un indicateur dans le catalogue.</Rien>;
  const l = Object.keys(serie).map((x) => ({ id: x, nom: court(nomDe(x)), v: serie[x] }))
                              .sort((a, b) => b.v - a.v);
  if (!l.length) return <Rien>Aucune valeur à ce niveau pour cet indicateur.</Rien>;

  const d = dec(l.map((x) => x.v));
  const mediane = med(l.map((x) => x.v));

  return (
    <div className="bg-white border border-line rounded-[18px] overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-[12.5px]">
          <thead className="sticky top-0 bg-bg z-10">
            <tr className="text-[9.5px] font-extrabold uppercase tracking-[0.09em] text-t2">
              <th className="text-left px-4 py-3 w-16">Rang</th>
              <th className="text-left px-4 py-3">Territoire</th>
              <th className="text-right px-4 py-3">Valeur</th>
              <th className="text-right px-4 py-3">Écart à la médiane</th>
              <th className="text-right px-4 py-3 hidden sm:table-cell">Millésime</th>
            </tr>
          </thead>
          <tbody>
            {l.map((x, n) => {
              const ecart = x.v - mediane;
              const cest = String(x.id) === String(moi);
              return (
                <tr key={x.id} onClick={() => onSelect(x.id)}
                  className={`border-t border-line-2 cursor-pointer transition-colors ${
                    cest ? "bg-gold-soft" : "hover:bg-bg"}`}>
                  <td className="px-4 py-3 font-extrabold text-t3 tabular-nums">{n + 1}</td>
                  <td className={`px-4 py-3 font-bold ${cest ? "text-navy" : "text-navy-3"}`}>
                    {x.nom}
                    {cest && <span className="ml-2 text-[9px] font-extrabold uppercase
                                              tracking-[0.08em] text-t2">fiche ouverte</span>}
                  </td>
                  <td className="px-4 py-3 text-right font-extrabold tabular-nums">
                    {nb(x.v, d)} <span className="text-t3 font-bold">{famille.unite || ""}</span>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums font-bold"
                      style={{ color: Math.abs(ecart) < 1e-9 ? "#7a8499" : ecart > 0 ? "#0f9f72" : "#d6455c" }}>
                    {ecart > 0 ? "+" : ""}{nb(ecart, d)}
                  </td>
                  <td className="px-4 py-3 text-right text-t3 hidden sm:table-cell">{famille.annee}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="px-4 py-2.5 bg-bg text-[10px] text-t3 border-t border-line">
        {l.length} {niveau === "commune" ? "communes" : "territoires"} · médiane{" "}
        {nb(mediane, d)} {famille.unite || ""} · cliquez une ligne pour ouvrir sa fiche
      </div>
    </div>
  );
}

/* ═══════════════════════════════════ synthèse ═══════════════════════════════ */

// La synthèse du site officiel décrit un indicateur. Ici la page décrit un
// TERRITOIRE : on garde donc les repères de distribution, mais on y ajoute la
// position du territoire ouvert — sa valeur, son rang et l'endroit où il tombe
// dans l'étendue des pairs. C'est ce qui distingue une fiche d'un explorateur.
function Synthese({ serie, nomDe, moi, famille, onSelect, niveau, reglages }) {
  if (!famille) return <Rien>Choisissez un indicateur dans le catalogue.</Rien>;
  const l = Object.keys(serie).map((x) => ({ id: x, nom: court(nomDe(x)), v: serie[x] }))
                              .sort((a, b) => b.v - a.v);
  if (!l.length) return <Rien>Aucune valeur à ce niveau pour cet indicateur.</Rien>;

  const vs = l.map((x) => x.v);
  const d = dec(vs);
  const mn = Math.min(...vs), mx = Math.max(...vs);
  const mediane = med(vs);
  const moyenne = vs.reduce((a, b) => a + b, 0) / vs.length;
  const u = famille.unite || "";

  const bornes = classer(vs, reglages.classes, reglages.methode);
  const palette = teintes(bornes.length + 1, famille.secteur);
  const clair = RAMPES[famille.secteur]?.[1] || "#c3d3f8";

  const v = serie[String(moi)];
  const rang = rangDe(v, vs, famille.sens);
  // Position dans l'étendue : 0 % au minimum observé, 100 % au maximum.
  const position = v != null && mx > mn ? ((v - mn) / (mx - mn)) * 100 : null;

  const Repere = ({ label, valeur, unite }) => (
    <div className="bg-white border border-line rounded-[16px] px-5 py-4">
      <div className="text-[9.5px] font-extrabold uppercase tracking-[0.1em] text-t2">{label}</div>
      <div className="text-[27px] font-extrabold text-navy mt-2 leading-none
                      tracking-[-0.045em] tabular-nums">
        {valeur}{unite && <small className="text-[14px] font-bold ml-1">{unite}</small>}
      </div>
    </div>
  );

  return (
    <div>
      {/* --- repères de distribution, dans l'esprit de l'écran officiel --- */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Repere label="Minimum" valeur={nb(mn, d)} unite={u} />
        <Repere label="Médiane" valeur={nb(mediane, d)} unite={u} />
        <Repere label="Maximum" valeur={nb(mx, d)} unite={u} />
        <Repere label={niveau === "commune" ? "Communes" : "Territoires"} valeur={l.length} />
      </div>

      {/* --- position du territoire ouvert ---
          C'est ce que l'explorateur du site ne peut pas montrer : il décrit un
          indicateur, la fiche décrit un territoire. */}
      {v != null && (
        <div className="mt-3 bg-white border border-line rounded-[16px] px-5 py-4">
          <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
            <div>
              <div className="text-[9.5px] font-extrabold uppercase tracking-[0.1em]"
                   style={{ color: COUL[famille.secteur].s }}>
                Position de {court(nomDe(moi))}
              </div>
              <div className="text-[27px] font-extrabold text-navy mt-2 leading-none
                              tracking-[-0.045em] tabular-nums">
                {nb(v, d)}<small className="text-[14px] font-bold ml-1">{u}</small>
              </div>
            </div>
            <div className="text-[11.5px] text-t2 leading-relaxed text-right">
              <b className="text-navy">{rang}<sup>{ordinal(rang)}</sup></b> sur {l.length} ·
              écart à la médiane{" "}
              <b style={{ color: v - mediane >= 0 ? "#0f9f72" : "#d6455c" }}>
                {v - mediane > 0 ? "+" : ""}{nb(v - mediane, d)} {u}
              </b>
              <br />
              <span className="text-t3">
                {famille.sens === "neutre" ? "rang par valeur décroissante"
                  : famille.sens === "bas_mieux" ? "1ᵉʳ = la valeur la plus basse"
                  : "1ᵉʳ = la valeur la plus haute"}
              </span>
            </div>
          </div>

          {/* Réglette d'étendue : où tombe le territoire entre le minimum et le
              maximum observés. Les classes en fond rattachent la position à ce
              que montre la carte. */}
          {position != null && (
            <div className="mt-5">
              <div className="flex h-3 rounded-full overflow-hidden">
                {palette.map((c, i) => <i key={i} className="flex-1" style={{ background: c }} />)}
              </div>
              <div className="relative h-6 mt-1">
                <span className="absolute -translate-x-1/2 -top-[19px] w-[3px] h-[22px]
                                 rounded-full bg-navy ring-[3px] ring-white"
                      style={{ left: `${position}%` }} />
                <span className="absolute -translate-x-1/2 top-0 text-[9.5px] font-extrabold
                                 text-navy whitespace-nowrap uppercase tracking-[0.05em]"
                      style={{ left: `${Math.min(92, Math.max(8, position))}%` }}>
                  {court(nomDe(moi))}
                </span>
              </div>
              <div className="flex justify-between text-[10px] text-t3 tabular-nums">
                <span>{nb(mn, d)}</span><span>{nb(mx, d)}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* --- classement, en barres pleine largeur --- */}
      <div className="mt-3 bg-white border border-line rounded-[16px] px-5 py-4">
        <div className="text-[9.5px] font-extrabold uppercase tracking-[0.1em] text-t2 mb-3.5">
          Classement des {niveau === "commune" ? "communes" : "territoires"}
        </div>
        {l.map((x) => {
          const cest = String(x.id) === String(moi);
          return (
            <div key={x.id} onClick={() => onSelect(x.id)}
              title={`Ouvrir la fiche de ${x.nom}`}
              className={`grid grid-cols-[minmax(84px,150px)_1fr_auto] items-center gap-3
                          px-2 -mx-2 py-[7px] rounded-[10px] cursor-pointer transition-colors ${
                cest ? "bg-gold-soft" : "hover:bg-bg"}`}>
              <span className={`text-[10.5px] uppercase tracking-[0.04em] truncate ${
                cest ? "font-extrabold text-navy" : "font-bold text-t2"}`}>
                {x.nom}
              </span>
              <div className="h-[14px] bg-[#eef2f8] rounded-full overflow-hidden">
                <i className="block h-full rounded-full transition-[width] duration-500"
                   style={{
                     width: `${Math.max(2, (100 * x.v) / mx).toFixed(1)}%`,
                     background: `linear-gradient(90deg, ${clair}, ${palette[classeDe(x.v, bornes)]})`,
                   }} />
              </div>
              <span className="text-[11.5px] font-extrabold tabular-nums text-navy min-w-[62px] text-right">
                {nb(x.v, d)} <span className="text-t3 font-bold">{u}</span>
              </span>
            </div>
          );
        })}
        <p className="text-[10px] text-t3 mt-3 pt-3 border-t border-line-2">
          Moyenne {nb(moyenne, d)} {u} — donnée pour mémoire. Les écarts sont rapportés à la
          médiane, que les valeurs extrêmes ne déplacent pas.
        </p>
      </div>
    </div>
  );
}

/* ═════════════════════════════ détail par secteur ═══════════════════════════ */

function DetailSecteur({ catalogue, absentes, secteur, niveau, donnees, pairs, moi,
                         vent, setVent, onPorter }) {
  const val = (id, t, cle) => valeur(donnees?.valeurs, id, t, vent[cle]);

  const brut = catalogue.filter((f) => f.secteur === secteur
    && f.membres.some((m) => val(m.indicateur_id, moi, cleFamille(f)) != null));
  const abs = absentes.filter((f) => f.secteur === secteur).length;

  // Le site officiel range ses cartes en grille régulière de trois colonnes.
  // Une maçonnerie en colonnes CSS, essayée d'abord, creusait de grands vides
  // dès qu'une carte était haute.
  //
  // La grille corrige le désordre mais pas les trous : dans une grille, la
  // hauteur d'une RANGÉE est celle de sa carte la plus haute, si bien qu'un
  // graphique posé à côté de deux chiffres laisse deux vides sous eux.
  // On ne peut ni raccourcir le graphique ni allonger les chiffres sans perdre
  // du contenu. La seule issue est de ne pas les mettre côte à côte : on
  // ordonne les objets par hauteur croissante — d'abord les chiffres, tous de
  // même taille, puis les graphiques du plus court au plus long. Les rangées
  // deviennent homogènes et les trous disparaissent presque tous.
  const HAUTEUR = { chiffre: 0, anneau: 1, groupe: 2, barres: 2, empile: 3, pyramide: 9 };
  const l = [...brut].sort((a, b) =>
    (HAUTEUR[a.forme] ?? 4) - (HAUTEUR[b.forme] ?? 4)
    || a.membres.length - b.membres.length
    || a.nom.localeCompare(b.nom, "fr"));

  return (
    <>
      {l.length > 0 && (
        // items-stretch (par défaut) : le reliquat de vide se loge DANS la
        // carte, où le pied de source vient se poser en bas, plutôt qu'entre
        // les cartes où il ne signifierait rien.
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-[18px] flux-impression">
          {l.map((f, i) => (
            <div key={cleFamille(f)}
                 className={f.forme === "pyramide" ? "md:col-span-2" : ""}>
              <ObjetFamille famille={f} donnees={donnees} pairs={pairs} moi={moi}
                            vent={vent} setVent={setVent} onPorter={onPorter} retard={i} />
            </div>
          ))}
        </div>
      )}
      {abs > 0 && (
        <p className="text-[12px] text-t3 leading-relaxed mt-5 bg-bg border border-dashed
                      border-line rounded-[14px] px-5 py-4">
          <b className="text-t2">{abs}</b> objet{abs > 1 ? "s" : ""} de ce secteur{" "}
          {abs > 1 ? "ne sont publiés" : "n'est publié"} qu'au niveau{" "}
          {niveau === "commune" ? "des préfectures et provinces" : "communal"}.
        </p>
      )}
      {!l.length && !abs && (
        <p className="text-[12px] text-t3 mt-4">Aucune donnée pour ce secteur à ce niveau.</p>
      )}
    </>
  );
}

function ObjetFamille({ famille: f, donnees, pairs, moi, vent, setVent, onPorter, retard = 0 }) {
  const cle = cleFamille(f);
  const c = COUL[f.secteur];
  const val = (id, t) => valeur(donnees?.valeurs, id, t, vent[cle]);

  // Sélecteur de ventilation : n'apparaît que si la table porte vraiment
  // plusieurs modalités (Ensemble / Masculin / Féminin, urbain / rural…).
  const modalites = serieDe(donnees?.valeurs, f.membres[0]?.indicateur_id, vent[cle]).cles;

  const Haut = (
    <div className="flex items-start justify-between gap-2.5">
      <span className="text-[10px] font-extrabold uppercase tracking-[0.08em] px-2.5 py-[7px]
                       rounded-full whitespace-nowrap"
            style={{ background: c.f, color: c.t }}>
        {f.secteur}
      </span>
      {/* L'année seule, comme sur le site officiel. Le mot « millésime » alourdit
          la carte ; la distinction avec la date de publication tient dans
          l'infobulle, où elle ne coûte rien à la lecture. */}
      <span className="text-[11px] text-t3 font-bold shrink-0 pt-1 whitespace-nowrap"
            title="Millésime : année à laquelle la donnée se rapporte, distincte de sa date de publication">
        {f.annee}
      </span>
    </div>
  );

  // mt-auto : dans une rangée, les cartes s'alignent sur la plus haute.
  // Le pied descend au bas de la carte, le vide se loge au-dessus de lui
  // plutôt que de flotter au milieu du contenu.
  const Pied = (
    <div className="mt-auto">
      <div className="flex items-center gap-2 text-[11px] text-t2 pt-4">
        <i className="w-2.5 h-2.5 rounded-[4px] bg-env" />
        Donnée officielle disponible
      </div>
      <div className="border-t border-line-2 mt-[18px] pt-[13px] text-[10px] text-t3 leading-snug"
           title={f.source}>
        <span className="font-extrabold tracking-[0.06em]">SOURCE ·</span>{" "}
        <span className="line-clamp-2">{sourceCourte(f.source)}</span>
      </div>
    </div>
  );

  /* --- une seule valeur : la carte-chiffre, cliquable vers la carte --- */
  if (f.forme === "chiffre") {
    const m = f.membres[0];
    const v = val(m.indicateur_id, moi);
    const l = pairs.map((t) => val(m.indicateur_id, t)).filter((x) => x != null);
    const d = dec(l.length ? l : [v]);
    const mediane = l.length > 1 ? med(l) : null;
    const rang = rangDe(v, l, f.sens);

    return (
      <article onClick={() => onPorter(f)}
        className="card-orvsit survolable monter cursor-pointer px-6 py-5 h-full flex flex-col"
        style={{ "--accent": c.t, "--retard": `${Math.min(retard, 12) * 0.04}s` }}>
        {Haut}
        <h3 className="text-[15px] font-extrabold text-t1 mt-4 mb-3 leading-snug">{f.nom}</h3>
        <div className="text-[36px] font-extrabold text-navy leading-none tracking-[-0.05em] tabular-nums">
          {nb(v, d)}<small className="text-[16px] font-bold ml-1.5">{f.unite || ""}</small>
        </div>
        <div className="text-[11.5px] text-t2 mt-2.5">
          {mediane == null
            ? "Valeur unique à ce niveau."
            : <>{rang}<sup>{ordinal(rang)}</sup> sur {l.length} · médiane des pairs{" "}
               {nb(mediane, d)} {f.unite || ""}</>}
        </div>
        {Pied}
      </article>
    );
  }

  /* --- plusieurs membres : le graphique décidé par le backend --- */
  // La pyramide consomme elle-même l'axe des sexes : elle lit Masculin d'un
  // côté et Féminin de l'autre. Lui proposer de choisir une modalité n'a pas
  // de sens — le choix serait sans effet — et laissait croire que le graphique
  // n'affichait qu'un sexe. Le sélecteur ne s'affiche donc que pour les formes
  // qui, elles, ne lisent qu'une série à la fois.
  const axeConsomme = f.forme === "pyramide";
  // Une ligne de légende n'a sa place que si elle apprend quelque chose.
  // « Les parts totalisent 100 % » justifie l'anneau ; « valeurs indépendantes »
  // prévient qu'on ne peut pas les additionner. En revanche, annoncer qu'une
  // famille montre « le même indicateur selon ses déclinaisons » ne fait que
  // nommer en jargon ce que les étiquettes disent déjà — 2014, 2024, urbain,
  // rural se lisent seuls. On ne l'écrit plus.
  const legende =
    f.forme === "pyramide" ? "Répartition par âge et par sexe, en part de la population."
    : f.forme === "anneau" || f.forme === "empile" ? "Les parts totalisent 100 %."
    : f.type === "ventilation" ? null
    : "Valeurs indépendantes, classées de la plus forte à la plus faible.";

  return (
    <article className="card-orvsit monter px-6 py-5 h-full flex flex-col"
             style={{ "--accent": c.t, "--retard": `${Math.min(retard, 12) * 0.04}s` }}>
      {Haut}
      <h3 className="text-[15px] font-extrabold text-t1 mt-4 mb-1.5 leading-snug">{f.nom}</h3>

      <div className={`flex items-center gap-2 flex-wrap ${legende ? "mb-3" : "mb-2"}`}>
        {legende && <span className="text-[10.5px] text-t2">{legende}</span>}
        {modalites.length > 1 && !axeConsomme && (
          <select value={serieDe(donnees?.valeurs, f.membres[0].indicateur_id, vent[cle]).cle}
            onChange={(e) => setVent({ ...vent, [cle]: e.target.value })}
            className="ml-auto text-[10px] font-bold text-navy bg-bg border border-line
                       rounded-lg px-2 py-1 max-w-[120px] outline-none">
            {modalites.map((m) => <option key={m}>{m}</option>)}
          </select>
        )}
      </div>

      <Graphique famille={f} valeurs={donnees?.valeurs} territoire={moi} vent={vent[cle]} />
      {Pied}
    </article>
  );
}
