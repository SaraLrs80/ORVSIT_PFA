// Fiche territoriale — toutes les données d'une province ou d'une commune.
//
// Organisation de la page (reprise de la maquette validée) :
//   1. En-tête : identité du territoire + 4 indicateurs d'alerte, avec le RANG
//      du territoire parmi ses pairs (provinces entre elles, communes d'une même
//      province entre elles) — et non face à la moyenne régionale, qui englobe
//      le territoire lui-même.
//   2. Position dans la région : carte choroplèthe + classement des pairs.
//   3. Signaux prioritaires : les indicateurs qui justifient une intervention.
//   4. Détail par thème, en sections dépliables.
//
// Toutes les valeurs viennent de l'API (/fiche/{id}), qui ne renvoie que des
// données officielles lues en base. Aucun calcul n'est fait ici, hormis des
// écarts (soustractions) et des pourcentages de répartition explicites.

import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  BriefcaseBusiness, VenetianMask, BookX, UserSearch, TriangleAlert,
  Users, GraduationCap, Stethoscope, House, Scale, MapPin, ListOrdered,
  ChevronDown, Building2, HeartPulse,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";
import DashboardLayout from "../../components/DashboardLayout";
import CarteChoropleth from "../../components/CarteChoropleth";
import SelecteurTerritoire from "../../components/SelecteurTerritoire";
import BoutonExport from "../../components/BoutonExport";
import { getArborescence, getFiche } from "../../api/fiche";
import { nombrePourExcel } from "../../utils/export";

/* ------------------------------------------------------------------ couleurs */
const NAVY = "#0a2540", GOLD = "#f5a623", TEAL = "#12a594";
const CORAL = "#f26d5b", BLUE = "#2d6cdf", VIOLET = "#7a5cf0";
const OK = "#16a34a", WARN = "#e8961a", BAD = "#e5484d";

/* -------------------------------------------------------------------- seuils */
// Seuils d'alerte ABSOLUS (indépendants de la région) : ils disent si la
// situation est maîtrisée, à surveiller ou critique, quel que soit le voisinage.
// `inverse` = une valeur ÉLEVÉE est favorable (ex. taux d'accès à l'eau).
const SEUILS = {
  chomage: { warn: 15, bad: 22 },
  chomage_femmes: { warn: 18, bad: 25 },
  analphabetisme: { warn: 20, bad: 30 },
  activite_femmes: { warn: 35, bad: 25, inverse: true },
  scolarisation: { warn: 90, bad: 80, inverse: true },
  vulnerabilite: { warn: 10, bad: 20 },
  taux_pauvrete: { warn: 6, bad: 12 },
  eau_courante: { warn: 85, bad: 70, inverse: true },
  assainissement: { warn: 85, bad: 70, inverse: true },
  internet: { warn: 60, bad: 40, inverse: true },
  privation: { warn: 5, bad: 12 },
  hab_par_medecin: { warn: 1000, bad: 2000 },
  hab_par_lit: { warn: 700, bad: 1200 },
};

function niveauAlerte(valeur, seuil) {
  if (valeur == null || !seuil) return null;
  if (seuil.inverse) return valeur >= seuil.warn ? "ok" : valeur >= seuil.bad ? "warn" : "bad";
  return valeur < seuil.warn ? "ok" : valeur < seuil.bad ? "warn" : "bad";
}
const LIBELLE_ALERTE = { ok: "OK", warn: "Vigilance", bad: "Alerte" };
const COULEUR_ALERTE = { ok: OK, warn: WARN, bad: BAD };
const CLASSE_METRIQUE = {
  ok: "border-l-[3px] border-l-[#16a34a] bg-[#e7f6ec]",
  warn: "border-l-[3px] border-l-[#e8961a] bg-[#fdf1dd]",
  bad: "border-l-[3px] border-l-[#e5484d] bg-[#fdeaea]",
  null: "border-l-[3px] border-l-line bg-bg",
};

/* ------------------------------------------------------------------- formats */
const nb = (v) => (v == null ? "—" : Number(v).toLocaleString("fr-FR"));
const pct = (v, d = 1) => (v == null ? "—" : `${Number(v).toFixed(d).replace(".", ",")} %`);
const dec = (v, d = 1) => (v == null ? "—" : Number(v).toFixed(d).replace(".", ","));
const ordinal = (r) => (r === 1 ? "1ᵉʳ" : `${r}ᵉ`);
const sansPrefixe = (nom) => (nom || "").replace(/^Commune (de |d')/, "").replace(/^(Préfecture|Province) (de |d')/, "");

/* ============================================================ petits blocs UI */

function Kpi({ Icon, label, valeur, alerte, complement }) {
  return (
    <div className="bg-white/[0.08] border border-white/15 rounded-2xl px-4 py-3.5">
      <div className="flex items-center gap-1.5 text-[11px] font-medium text-white/70">
        <Icon size={15} />
        {label}
      </div>
      <div className="flex items-baseline gap-2 mt-1.5">
        <span className="text-[25px] font-extrabold leading-none">{valeur}</span>
        {alerte && (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                style={{ background: `${COULEUR_ALERTE[alerte]}22`, color: COULEUR_ALERTE[alerte] }}>
            {LIBELLE_ALERTE[alerte]}
          </span>
        )}
      </div>
      {complement && <div className="text-[10.5px] text-white/60 mt-1.5">{complement}</div>}
    </div>
  );
}

function Metrique({ valeur, label, alerte }) {
  return (
    <div className={`rounded-xl px-3.5 py-3 ${CLASSE_METRIQUE[alerte ?? "null"]}`}>
      <div className="text-[19px] font-extrabold leading-none">{valeur}</div>
      <div className="text-[10.5px] text-t2 mt-1">{label}</div>
    </div>
  );
}

function Carte({ titre, Icon, couleurIcone, but, children, className = "" }) {
  return (
    <div className={`bg-surface border border-line rounded-2xl p-5 ${className}`}>
      {titre && (
        <h3 className="text-sm font-bold text-navy flex items-center gap-2">
          {Icon && <Icon size={17} style={{ color: couleurIcone || NAVY }} />}
          {titre}
        </h3>
      )}
      {but && <p className="text-[11.5px] text-t2 mt-1 mb-3.5 leading-relaxed">{but}</p>}
      {children}
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

function Accordeon({ id, titre, sousTitre, Icon, couleur, ouvert, onToggle, children }) {
  return (
    <div className="bg-surface border border-line rounded-2xl mb-3 overflow-hidden">
      <button onClick={() => onToggle(id)}
        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-bg transition-colors text-left">
        <span className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: `${couleur}1a`, color: couleur }}>
          <Icon size={19} />
        </span>
        <span className="flex-1">
          <span className="block text-sm font-bold text-navy">{titre}</span>
          <span className="block text-[11.5px] text-t2 mt-0.5">{sousTitre}</span>
        </span>
        <ChevronDown size={20}
          className={`text-t3 transition-transform ${ouvert ? "rotate-180" : ""}`} />
      </button>
      {/* Fond gris sous le contenu : les cartes blanches s'en détachent, ce qui
          donne une structure lisible au lieu d'éléments qui flottent. */}
      {ouvert && <div className="bg-bg border-t border-line px-4 py-4">{children}</div>}
    </div>
  );
}

/* Sources d'une section, telles que déclarées dans le catalogue d'indicateurs.
   Affichées sous chaque thème pour que le lecteur sache d'où vient chaque chiffre. */
function Sources({ liste }) {
  if (!liste?.length) return null;
  return (
    <div className="mt-4 pt-3 border-t border-line/70">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-t3 mb-1.5">
        {liste.length > 1 ? "Sources" : "Source"}
      </div>
      <ul className="space-y-1">
        {liste.map((s, i) => (
          <li key={i} className="text-[10.5px] text-t2 leading-relaxed flex gap-1.5">
            <span className="text-t3 shrink-0">•</span>
            <span>
              {s.source}
              {s.annee && <span className="text-t3"> — {s.annee}</span>}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* Enveloppe commune à tous les graphiques. */
function Graphe({ hauteur = 220, children }) {
  return (
    <div style={{ width: "100%", height: hauteur }}>
      <ResponsiveContainer>{children}</ResponsiveContainer>
    </div>
  );
}

const infobulle = {
  contentStyle: { borderRadius: 12, border: "1px solid #e9edf3", fontSize: 12 },
};

/* ================================================================== la page */

export default function FicheTerritorialePage() {
  const { territoireId } = useParams();
  const navigate = useNavigate();

  const [arbre, setArbre] = useState([]);
  const [data, setData] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const [geoProvinces, setGeoProvinces] = useState(null);
  const [geoCommunes, setGeoCommunes] = useState(null);
  const [indicateurCarte, setIndicateurCarte] = useState(null);
  const [ouvert, setOuvert] = useState("demographie");

  const idCourant = territoireId || "2";   // Tanger-Assilah par défaut

  /* --- chargements --- */
  useEffect(() => {
    getArborescence().then(setArbre).catch(() => {});
    fetch("/geo/provinces.geojson").then((r) => r.json()).then(setGeoProvinces).catch(() => {});
    fetch("/geo/communes.geojson").then((r) => r.json()).then(setGeoCommunes).catch(() => {});
  }, []);

  useEffect(() => {
    setChargement(true);
    setErreur("");
    getFiche(idCourant)
      .then((d) => { setData(d); setIndicateurCarte(null); })
      .catch(() => setErreur("Impossible de charger la fiche de ce territoire."))
      .finally(() => setChargement(false));
  }, [idCourant]);

  /* --- dérivés --- */
  const estCommune = data?.territoire?.niveau === "commune";
  const provinceCourante = useMemo(() => {
    if (!data) return null;
    return arbre.find((p) => p.territoire_id === (data.province_id ?? data.territoire.territoire_id));
  }, [arbre, data]);

  const definitions = data?.pairs?.indicateurs || [];
  const defCarte = useMemo(() => {
    if (!definitions.length) return null;
    return definitions.find((d) => d.cle === indicateurCarte) || definitions[0];
  }, [definitions, indicateurCarte]);

  const valeursCarte = data?.pairs?.valeurs?.[defCarte?.cle] || {};

  // Classement des pairs pour l'indicateur affiché (1 = le mieux placé).
  const classementPairs = useMemo(() => {
    if (!defCarte || !data) return [];
    const noms = data.pairs.noms || {};
    return Object.entries(valeursCarte)
      .map(([id, valeur]) => ({ id: Number(id), nom: noms[id] || id, valeur }))
      .sort((a, b) => (defCarte.sens === 1 ? b.valeur - a.valeur : a.valeur - b.valeur));
  }, [defCarte, valeursCarte, data]);

  const maxCarte = Math.max(...classementPairs.map((p) => p.valeur), 0);

  // Couleur d'une zone : position dans le classement (tiers).
  function couleurZone(valeur, id) {
    if (valeur == null) return "#d7dde6";
    const rang = classementPairs.findIndex((p) => p.id === Number(id));
    if (rang < 0) return "#d7dde6";
    const q = rang / classementPairs.length;
    return q < 0.375 ? TEAL : q < 0.625 ? GOLD : CORAL;
  }

  const rangDe = (cle) => data?.pairs?.classements?.[cle] || null;

  // Export : tous les indicateurs affichés, à plat, avec leur rang parmi les
  // pairs. Un fichier doit pouvoir se lire seul, d'où l'en-tête de contexte.
  function donneesExport() {
    if (!data) return null;
    const lignes = [];
    const pousser = (theme, libelle, valeur, unite, cle) => {
      if (valeur == null) return;
      const r = cle ? data.rangs?.[cle] || data.pairs?.classements?.[cle] : null;
      lignes.push([theme, libelle, nombrePourExcel(valeur), unite,
                   r ? `${r.rang}/${r.total}` : ""]);
    };

    const id = data.identite || {};
    pousser("Identité", "Population", id.population, "habitants");
    pousser("Identité", "Ménages", id.menages, "ménages");
    pousser("Identité", "Population urbaine", id.population_urbaine, "habitants");
    pousser("Identité", "Population rurale", id.population_rurale, "habitants");
    pousser("Identité", "Taux d'urbanisation", id.taux_urbanisation, "%");
    pousser("Identité", "Croissance annuelle", id.croissance_annuelle, "%");

    const e = data.emploi || {};
    ["ensemble", "hommes", "femmes"].forEach((k) => {
      const suffixe = k === "ensemble" ? "" : ` (${k})`;
      pousser("Emploi", `Taux d'activité${suffixe}`, e.activite?.[k], "%",
              k === "ensemble" ? "activite" : k === "femmes" ? "activite_femmes" : null);
      pousser("Emploi", `Taux de chômage${suffixe}`, e.chomage?.[k], "%",
              k === "ensemble" ? "chomage" : k === "femmes" ? "chomage_femmes" : null);
    });

    const ed = data.education || {};
    pousser("Éducation", "Scolarisation 6-11 ans", ed.scolarisation_6_11, "%", "scolarisation");
    pousser("Éducation", "Analphabétisme 15 ans et +", ed.analphabetisme_15_plus?.ensemble, "%", "analphabetisme");
    pousser("Éducation", "Analphabétisme femmes", ed.analphabetisme_15_plus?.femmes, "%");
    pousser("Éducation", "Analphabétisme hommes", ed.analphabetisme_15_plus?.hommes, "%");
    Object.entries(ed.niveau_etudes || {}).forEach(([k, v]) =>
      pousser("Éducation", `Niveau d'études : ${k}`, v, "%"));
    Object.entries(ed.etablissements || {}).forEach(([k, v]) => {
      if (typeof v === "number") pousser("Éducation", `Établissements : ${k}`, v, "nombre");
    });

    const sa = data.sante || {};
    Object.entries(sa.offre || {}).forEach(([k, v]) =>
      pousser("Santé", k.replace(/_/g, " "), v, "habitants par unité"));
    Object.entries(sa.privations || {}).forEach(([k, v]) =>
      pousser("Santé", `Privation : ${k}`, v, "%"));

    const cv = data.conditions_vie || {};
    Object.entries(cv.habitat || {}).forEach(([k, v]) =>
      pousser("Conditions de vie", `Accès : ${k}`, v, "%"));
    Object.entries(cv.pauvrete || {}).forEach(([k, v]) =>
      pousser("Conditions de vie", `Pauvreté : ${k}`, v, "%"));
    Object.entries(cv.privations || {}).forEach(([k, v]) =>
      pousser("Conditions de vie", `Privation : ${k}`, v, "%"));
    Object.entries(cv.transport || {}).forEach(([k, v]) =>
      pousser("Conditions de vie", `Transport : ${k}`, v, "%"));
    Object.entries(cv.numerique || {}).forEach(([k, v]) =>
      pousser("Conditions de vie", `Numérique : ${k}`, v, "%"));

    const sources = [...new Map(
      Object.values(data.sources || {}).flat().map((x) => [x.source, x])).values()];

    return {
      colonnes: ["Thème", "Indicateur", "Valeur", "Unité", "Rang parmi les pairs"],
      lignes,
      entete: [
        "ORVSIT — Fiche territoriale",
        `Territoire : ${data.territoire.nom}`,
        `Niveau : ${estCommune ? "commune" : "préfecture / province"}`,
        `Comparé à ${Object.keys(data.pairs?.noms || {}).length} territoires de même niveau`,
        `Exporté le ${new Date().toLocaleDateString("fr-FR")}`,
        ...sources.map((x) => `Source : ${x.source}${x.annee ? ` (${x.annee})` : ""}`),
      ],
    };
  }

  return (
    <DashboardLayout title="Fiche territoriale" active="fiche">
      {/* ---------- sélecteurs ---------- */}
      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div className="w-64">
          <SelecteurTerritoire
            Icone={MapPin}
            valeur={provinceCourante?.territoire_id || ""}
            onChange={(id) => navigate(`/dashboard/fiche/${id}`)}
            options={arbre.map((p) => ({
              id: p.territoire_id,
              nom: p.nom,
              detail: `${(p.communes || []).length} communes`,
            }))}
            placeholder="Choisir une préfecture ou province"
          />
        </div>

        <div className="w-64">
          <SelecteurTerritoire
            valeur={estCommune ? data?.territoire?.territoire_id ?? "" : ""}
            onChange={(id) =>
              navigate(`/dashboard/fiche/${id || provinceCourante?.territoire_id}`)}
            options={(provinceCourante?.communes || []).map((c) => ({
              id: c.territoire_id,
              nom: sansPrefixe(c.nom),
            }))}
            optionVide="Toute la préfecture / province"
            placeholder="Choisir une commune"
          />
        </div>

        {data && (
          <div className="ml-auto">
            <BoutonExport nom={`fiche_${data.territoire.nom}`} donnees={donneesExport}
                          libelle="Exporter la fiche" />
          </div>
        )}
      </div>

      {chargement ? (
        <p className="text-t2">Chargement…</p>
      ) : erreur ? (
        <p className="text-red-600">{erreur}</p>
      ) : !data ? null : (
        <>
          {/* ================= EN-TÊTE ================= */}
          <div className="relative rounded-3xl px-7 py-6 text-white
                          bg-gradient-to-br from-navy via-navy-2 to-navy shadow-xl">
            <div className="absolute inset-0 rounded-3xl overflow-hidden pointer-events-none">
              <div className="absolute -top-24 -right-10 w-72 h-72 rounded-full"
                   style={{ background: "radial-gradient(circle, rgba(245,166,35,.28), transparent 70%)" }} />
              <div className="absolute -bottom-24 left-1/3 w-64 h-64 rounded-full"
                   style={{ background: "radial-gradient(circle, rgba(245,166,35,.12), transparent 70%)" }} />
            </div>
            <div className="relative flex items-start gap-4 flex-wrap">
              <div className="rounded-2xl bg-gold/20 flex items-center justify-center shrink-0"
                   style={{ width: 60, height: 60 }}>
                <MapPin size={28} className="text-gold" />
              </div>
              <div>
                <div className="text-[10.5px] font-semibold tracking-[0.14em] uppercase text-gold">
                  {estCommune ? "Commune" : "Préfecture / Province"}
                </div>
                <h1 className="text-[26px] font-extrabold mt-0.5">{data.territoire.nom}</h1>
                <p className="text-[12.5px] text-white/65 mt-1">
                  {nb(data.identite.population)} habitants
                  {data.identite.menages != null && ` · ${nb(data.identite.menages)} ménages`}
                  {!estCommune && data.identite.nb_communes != null &&
                    ` · ${data.identite.nb_communes} communes`}
                  {data.identite.taux_urbanisation != null &&
                    ` · ${dec(data.identite.taux_urbanisation)} % urbain`}
                  {data.identite.croissance_annuelle != null &&
                    ` · +${dec(data.identite.croissance_annuelle, 2)} %/an`}
                  {estCommune && data.territoire.parent_nom && ` · ${data.territoire.parent_nom}`}
                </p>
              </div>
            </div>

            {/* KPI d'alerte avec le rang parmi les pairs */}
            <div className="relative grid grid-cols-2 lg:grid-cols-4 gap-3 mt-5">
              {(() => {
                const emploi = data.emploi || {};
                const educ = data.education || {};
                const rangTexte = (cle) => {
                  const r = rangDe(cle);
                  if (!r) return null;
                  return `${ordinal(r.rang)} / ${r.total} ${estCommune ? "communes" : "provinces"}`;
                };
                const kpis = [
                  { Icon: BriefcaseBusiness, label: "Taux de chômage",
                    v: emploi.chomage?.ensemble, cle: "chomage" },
                  { Icon: VenetianMask, label: "Chômage des femmes",
                    v: emploi.chomage?.femmes, cle: "chomage_femmes" },
                  { Icon: BookX, label: "Analphabétisme 15+",
                    v: educ.analphabetisme_15_plus?.ensemble, cle: "analphabetisme" },
                  estCommune
                    ? { Icon: TriangleAlert, label: "Vulnérabilité pauvreté",
                        v: data.conditions_vie?.pauvrete?.vulnerabilite, cle: "vulnerabilite" }
                    : { Icon: UserSearch, label: "Activité des femmes",
                        v: emploi.activite?.femmes, cle: "activite_femmes" },
                ];
                return kpis.map((k) => (
                  <Kpi key={k.cle} Icon={k.Icon} label={k.label}
                       valeur={k.v == null ? "—" : pct(k.v)}
                       alerte={niveauAlerte(k.v, SEUILS[k.cle])}
                       complement={rangTexte(k.cle)} />
                ));
              })()}
            </div>
          </div>

          {/* ================= POSITION DANS LA RÉGION ================= */}
          <TitreSection Icon={MapPin} titre="Position dans la région"
            note={estCommune
              ? `parmi les ${Object.keys(data.pairs.noms).length} communes de la province`
              : `parmi les ${Object.keys(data.pairs.noms).length} provinces de la région`} />

          <div className="grid lg:grid-cols-[1.3fr_1fr] gap-4">
            <Carte titre={`${defCarte?.label || ""} — comparaison entre pairs`}
                   Icon={MapPin} couleurIcone={TEAL}
                   but={`Chaque territoire est coloré selon sa position pour cet indicateur ; le territoire affiché est entouré. ${
                     defCarte?.sens === 1
                       ? "Une valeur élevée est favorable."
                       : "Une valeur élevée signale une situation plus difficile."} Cliquez une zone pour ouvrir sa fiche.`}>
              <div className="mb-3">
                <select
                  value={defCarte?.cle || ""}
                  onChange={(e) => setIndicateurCarte(e.target.value)}
                  className="text-xs border border-line rounded-lg px-3 py-2 bg-bg text-navy font-semibold focus:outline-none focus:border-blue"
                >
                  {definitions.map((d) => (
                    <option key={d.cle} value={d.cle}>{d.label}</option>
                  ))}
                </select>
              </div>

              <CarteChoropleth
                geojson={estCommune ? geoCommunes : geoProvinces}
                valeurs={valeursCarte}
                couleurDe={couleurZone}
                selection={data.territoire.territoire_id}
                onSelect={(id) => {
                  if (data.pairs.noms[String(id)]) navigate(`/dashboard/fiche/${id}`);
                }}
                libelleDe={(id) => {
                  const nom = data.pairs.noms[String(id)];
                  if (!nom) return null;
                  const v = valeursCarte[id];
                  return `${sansPrefixe(nom)} : ${v == null ? "n.d." : defCarte?.unite === "%" ? pct(v) : nb(v)}`;
                }}
                hauteur={300}
              />

              <div className="flex gap-3.5 mt-2.5 text-[10.5px] text-t2 flex-wrap">
                {[["Favorable", TEAL], ["Intermédiaire", GOLD], ["Défavorable", CORAL]].map(([l, c]) => (
                  <span key={l} className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded" style={{ background: c }} />{l}
                  </span>
                ))}
              </div>
            </Carte>

            <Carte titre="Classement" Icon={ListOrdered} couleurIcone={NAVY}
                   but={`Du plus favorable au moins favorable pour « ${defCarte?.label || ""} ».`}>
              <div className="max-h-[380px] overflow-y-auto -mx-1 px-1">
                {classementPairs.map((p, i) => {
                  const couleur = couleurZone(p.valeur, p.id);
                  const estMoi = p.id === data.territoire.territoire_id;
                  return (
                    <button key={p.id}
                      onClick={() => navigate(`/dashboard/fiche/${p.id}`)}
                      className={`w-full flex items-center gap-2.5 py-2 px-2 -mx-2 rounded-lg text-left
                                  hover:bg-bg transition-colors ${estMoi ? "bg-blue-soft" : ""}`}>
                      <span className="w-5 h-5 rounded-md text-white text-[10px] font-bold
                                       flex items-center justify-center shrink-0"
                            style={{ background: couleur }}>{i + 1}</span>
                      <span className={`flex-1 text-xs truncate ${estMoi ? "font-bold text-navy" : "font-semibold text-t1"}`}>
                        {sansPrefixe(p.nom)}
                      </span>
                      <span className="flex-1 h-1.5 rounded-full bg-bg overflow-hidden max-w-[80px]">
                        <span className="block h-full rounded-full"
                              style={{ width: `${maxCarte ? (p.valeur / maxCarte) * 100 : 0}%`, background: couleur }} />
                      </span>
                      <span className="w-14 text-right text-xs font-bold" style={{ color: couleur }}>
                        {defCarte?.unite === "%" ? dec(p.valeur) : nb(p.valeur)}
                      </span>
                    </button>
                  );
                })}
              </div>
            </Carte>
          </div>

          {/* ================= SIGNAUX PRIORITAIRES ================= */}
          <TitreSection Icon={TriangleAlert} titre="Signaux prioritaires"
                        note="ce qui justifie — ou non — une intervention" />
          <div className="grid lg:grid-cols-[1.3fr_1fr] gap-4">
            <Carte but="Seuils d'alerte absolus, indépendants du voisinage : vert = maîtrisé, orange = à surveiller, rouge = critique.">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {(() => {
                  const e = data.emploi || {}, ed = data.education || {};
                  const cv = data.conditions_vie || {};
                  const items = [
                    ["Chômage", e.chomage?.ensemble, "chomage"],
                    ["Chômage femmes", e.chomage?.femmes, "chomage_femmes"],
                    ["Analphabétisme 15+", ed.analphabetisme_15_plus?.ensemble, "analphabetisme"],
                    ["Activité femmes", e.activite?.femmes, "activite_femmes"],
                    ["Scolarisation 6-11", ed.scolarisation_6_11, "scolarisation"],
                  ];
                  if (estCommune) {
                    items.push(
                      ["Taux de pauvreté", cv.pauvrete?.taux_pauvrete, "taux_pauvrete"],
                      ["Vulnérabilité", cv.pauvrete?.vulnerabilite, "vulnerabilite"],
                      ["Privation eau", cv.privations?.eau, "privation"],
                      ["Privation assainis.", cv.privations?.assainissement, "privation"],
                    );
                  } else {
                    items.push(
                      ["Eau courante", cv.habitat?.eau_courante, "eau_courante"],
                      ["Assainissement", cv.habitat?.assainissement, "assainissement"],
                      ["Internet", cv.numerique?.internet, "internet"],
                      ["Hab. / lit hosp.", data.sante?.offre?.hab_par_lit_public_prive, "hab_par_lit"],
                    );
                  }
                  return items
                    .filter(([, v]) => v != null)
                    .map(([label, v, cle]) => (
                      <Metrique key={label} label={label}
                        valeur={SEUILS[cle]?.warn > 100 ? nb(v) : pct(v)}
                        alerte={niveauAlerte(v, SEUILS[cle])} />
                    ));
                })()}
              </div>
            </Carte>

            <Carte titre="Écart femmes / hommes" Icon={Scale} couleurIcone={VIOLET}
                   but="L'accès des femmes à l'emploi est le levier d'action le plus fréquent.">
              {data.emploi?.activite && data.emploi?.chomage ? (
                <>
                  <Graphe hauteur={175}>
                    <BarChart data={[
                      { nom: "Activité", Hommes: data.emploi.activite.hommes, Femmes: data.emploi.activite.femmes },
                      { nom: "Chômage", Hommes: data.emploi.chomage.hommes, Femmes: data.emploi.chomage.femmes },
                    ]}>
                      <CartesianGrid stroke="#eef1f6" vertical={false} />
                      <XAxis dataKey="nom" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 10 }} unit="%" />
                      <Tooltip {...infobulle} formatter={(v) => `${dec(v)} %`} />
                      <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                      <Bar dataKey="Hommes" fill={BLUE} radius={[5, 5, 0, 0]} />
                      <Bar dataKey="Femmes" fill={CORAL} radius={[5, 5, 0, 0]} />
                    </BarChart>
                  </Graphe>
                  {data.emploi.activite.hommes != null && data.emploi.activite.femmes != null && (
                    <div className="flex gap-2.5 items-start bg-[#fdf1dd] rounded-xl px-3.5 py-3 mt-3">
                      <Scale size={17} className="text-[#a9670a] shrink-0 mt-0.5" />
                      <p className="text-xs leading-relaxed">
                        <b>{dec(data.emploi.activite.hommes - data.emploi.activite.femmes)} points</b>{" "}
                        d'écart d'activité entre hommes et femmes.
                        {data.emploi.chomage.femmes != null && data.emploi.chomage.hommes != null && (
                          <> Le chômage féminin ({pct(data.emploi.chomage.femmes)}) se compare
                          à {pct(data.emploi.chomage.hommes)} chez les hommes.</>
                        )}
                      </p>
                    </div>
                  )}
                </>
              ) : <p className="text-t3 text-sm">Donnée non disponible.</p>}
            </Carte>
          </div>

          {/* ================= DÉTAIL PAR THÈME ================= */}
          <TitreSection Icon={ListOrdered} titre="Explorer par thème"
                        note="cliquez pour déplier — chaque thème indique ses sources" />
          <SectionsThemes data={data} estCommune={estCommune}
                          ouvert={ouvert} onToggle={(id) => setOuvert(ouvert === id ? null : id)} />

          <p className="text-[11px] text-t3 text-center mt-6 leading-relaxed">
            Sources officielles : RGPH 2024 (HCP) · Carte Sanitaire 2024 (Ministère de la Santé et de
            la Protection Sociale) · Cartographie de la pauvreté multidimensionnelle (HCP, 2025).
            La comparaison se fait <b>entre pairs de même niveau</b> et non contre la moyenne
            régionale, qui englobe le territoire lui-même. Aucune valeur n'est calculée ni estimée,
            hormis les totaux de comptages d'établissements.
          </p>
        </>
      )}
    </DashboardLayout>
  );
}

/* ==================================================== sections thématiques
 *
 * Principe de mise en page, pour éviter l'effet « rapport » :
 *   - le corps d'un thème est posé sur le fond gris de la page, et chaque bloc
 *     est une carte blanche : la structure se voit, rien ne flotte ;
 *   - toutes les cartes d'une même rangée ont la MÊME hauteur (items-stretch
 *     + h-full), donc plus de vide en escalier ;
 *   - les indicateurs chiffrés sont regroupés en une bande unique en haut du
 *     thème, jamais éparpillés entre deux graphiques ;
 *   - un graphique occupe toute la hauteur restante de sa carte (flex-1).
 */

/* Carte blanche d'un bloc, à hauteur pleine. */
function Bloc({ titre, but, children, className = "" }) {
  return (
    <div className={`bg-surface border border-line rounded-2xl p-4 flex flex-col h-full ${className}`}>
      {titre && <h4 className="text-[13.5px] font-bold text-navy">{titre}</h4>}
      {but && <p className="text-[11.5px] text-t2 mt-1 leading-relaxed">{but}</p>}
      <div className="flex-1 flex flex-col justify-center mt-3">{children}</div>
    </div>
  );
}

/* Bande d'indicateurs chiffrés, en tête de thème. */
function Bande({ items }) {
  const visibles = items.filter((i) => i && i.valeur != null);
  if (!visibles.length) return null;
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5 mb-4">
      {visibles.map((i) => (
        <Metrique key={i.label} label={i.label} valeur={i.rendu ?? pct(i.valeur)}
                  alerte={i.seuil ? niveauAlerte(i.valeur, SEUILS[i.seuil]) : null} />
      ))}
    </div>
  );
}

/* Grille de cartes à hauteur égale. */
function Grille({ cols = 2, children }) {
  const c = cols === 3 ? "lg:grid-cols-3" : cols === 21 ? "lg:grid-cols-[1.3fr_1fr]" : "lg:grid-cols-2";
  return <div className={`grid ${c} gap-4 items-stretch`}>{children}</div>;
}

const H_GRAPHE = 250;   // hauteur commune des graphiques d'une rangée

function SectionsThemes({ data, estCommune, ouvert, onToggle }) {
  const sections = [
    { id: "demographie", titre: "Démographie", sous: "Structure de population, âges, ménages",
      Icon: Users, couleur: NAVY, dispo: !!data.demographie },
    { id: "emploi", titre: "Emploi", sous: "Activité, chômage, statut des actifs",
      Icon: BriefcaseBusiness, couleur: BLUE, dispo: !!data.emploi },
    { id: "education", titre: "Éducation", sous: "Niveau d'études, analphabétisme, établissements",
      Icon: GraduationCap, couleur: GOLD, dispo: !!data.education },
    { id: "sante", titre: "Santé",
      sous: estCommune ? "Établissements et privations" : "Offre de soins et établissements",
      Icon: Stethoscope, couleur: TEAL, dispo: !!data.sante },
    { id: "conditions", titre: "Conditions de vie", sous: "Accès aux services, transport, pauvreté",
      Icon: House, couleur: CORAL, dispo: !!data.conditions_vie },
  ].filter((s) => s.dispo);

  const cleSource = { conditions: "conditions_vie" };

  return sections.map((s) => (
    <Accordeon key={s.id} id={s.id} titre={s.titre} sousTitre={s.sous}
               Icon={s.Icon} couleur={s.couleur}
               ouvert={ouvert === s.id} onToggle={onToggle}>
      {s.id === "demographie" && <BlocDemographie d={data.demographie} identite={data.identite} estCommune={estCommune} />}
      {s.id === "emploi" && <BlocEmploi d={data.emploi} />}
      {s.id === "education" && <BlocEducation d={data.education} />}
      {s.id === "sante" && <BlocSante d={data.sante} estCommune={estCommune} />}
      {s.id === "conditions" && <BlocConditions d={data.conditions_vie} estCommune={estCommune} />}
      <Sources liste={data.sources?.[cleSource[s.id] || s.id]} />
    </Accordeon>
  ));
}

/* ------------------------------------------------------------ démographie */
function BlocDemographie({ d, identite, estCommune }) {
  const pyramide = (d.pyramide_ages || [])
    .filter((t) => t.hommes != null || t.femmes != null)
    .map((t) => ({ tranche: t.tranche, Hommes: t.hommes ? -t.hommes : 0, Femmes: t.femmes || 0 }))
    .reverse();

  const repartition = estCommune
    ? (d.sexe ? [{ nom: "Hommes", v: d.sexe.masculin, c: BLUE }, { nom: "Femmes", v: d.sexe.feminin, c: CORAL }] : [])
    : (identite.population_urbaine != null
        ? [{ nom: "Urbain", v: identite.population_urbaine, c: NAVY },
           { nom: "Rural", v: identite.population_rurale, c: GOLD }]
        : []);

  const matri = d.matrimonial
    ? [["Célibataire", d.matrimonial.celibataire, BLUE], ["Marié·e", d.matrimonial.marie, TEAL],
       ["Divorcé·e", d.matrimonial.divorce, GOLD], ["Veuf·ve", d.matrimonial.veuf, CORAL]]
        .filter(([, v]) => v != null).map(([nom, v, c]) => ({ nom, valeur: v, c }))
    : [];

  return (
    <>
      <Bande items={[
        { label: "Population 15 ans et +", valeur: d.population_15_plus, rendu: nb(d.population_15_plus) },
        { label: "Indice de fécondité", valeur: d.fecondite?.indice_conjoncturel,
          rendu: dec(d.fecondite?.indice_conjoncturel, 2) },
        { label: "Âge au 1ᵉʳ mariage", valeur: d.fecondite?.age_moyen_mariage,
          rendu: `${dec(d.fecondite?.age_moyen_mariage)} ans` },
        { label: "Descendance finale", valeur: d.fecondite?.descendance_finale,
          rendu: dec(d.fecondite?.descendance_finale, 1) },
      ]} />

      <Grille cols={21}>
        {pyramide.length > 0 && (
          <Bloc titre="Pyramide des âges"
                but="Une base large signale une population jeune ; un sommet lourd, un vieillissement.">
            <Graphe hauteur={300}>
              <BarChart data={pyramide} layout="vertical" stackOffset="sign" margin={{ left: -8, right: 8 }}>
                <CartesianGrid stroke="#eef1f6" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 9.5 }} tickFormatter={(v) => `${Math.abs(v)}%`} />
                <YAxis type="category" dataKey="tranche" tick={{ fontSize: 9 }} width={46} />
                <Tooltip {...infobulle} formatter={(v) => `${dec(Math.abs(v))} %`} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Hommes" fill={BLUE} stackId="a" />
                <Bar dataKey="Femmes" fill={CORAL} stackId="a" />
              </BarChart>
            </Graphe>
          </Bloc>
        )}

        <div className="grid gap-4 content-start">
          {repartition.length > 0 && (
            <Bloc titre={estCommune ? "Répartition par sexe" : "Population urbaine / rurale"}
                  but={estCommune ? "Équilibre hommes / femmes."
                                  : "Le poids du rural conditionne le type d'intervention."}>
              <Graphe hauteur={150}>
                <PieChart>
                  <Pie data={repartition} dataKey="v" nameKey="nom" innerRadius="58%" outerRadius="86%" paddingAngle={2}>
                    {repartition.map((r) => <Cell key={r.nom} fill={r.c} />)}
                  </Pie>
                  <Tooltip {...infobulle} formatter={(v, n) => [estCommune ? pct(v) : nb(v), n]} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </Graphe>
            </Bloc>
          )}

          {matri.length > 0 && (
            <Bloc titre="État matrimonial (15 ans et plus)"
                  but="Un veuvage ou un divorce élevé peut signaler des ménages fragiles.">
              <Graphe hauteur={135}>
                <BarChart data={matri} layout="vertical" margin={{ left: 8, right: 12 }}>
                  <CartesianGrid stroke="#eef1f6" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10 }} unit="%" />
                  <YAxis type="category" dataKey="nom" tick={{ fontSize: 10 }} width={76} />
                  <Tooltip {...infobulle} formatter={(v) => `${dec(v)} %`} />
                  <Bar dataKey="valeur" radius={[0, 5, 5, 0]}>
                    {matri.map((m) => <Cell key={m.nom} fill={m.c} />)}
                  </Bar>
                </BarChart>
              </Graphe>
            </Bloc>
          )}
        </div>
      </Grille>
    </>
  );
}

/* ----------------------------------------------------------------- emploi */
function BlocEmploi({ d }) {
  const parSexe = ["ensemble", "hommes", "femmes"]
    .map((k) => ({
      nom: k === "ensemble" ? "Ensemble" : k === "hommes" ? "Hommes" : "Femmes",
      "Taux d'activité": d.activite?.[k],
      "Taux de chômage": d.chomage?.[k],
    }))
    .filter((r) => r["Taux d'activité"] != null || r["Taux de chômage"] != null);

  const STATUTS = [
    ["Salarié privé", "salarie_prive", NAVY], ["Indépendant", "independant", GOLD],
    ["Salarié public", "salarie_public", BLUE], ["Employeur", "employeur", TEAL],
    ["Aide familial", "aide_familial", VIOLET], ["Autre", "autre", CORAL],
  ];
  const statut = STATUTS
    .map(([nom, cle, c]) => ({ nom, v: d.statut_professionnel?.[cle], c }))
    .filter((s) => s.v != null);

  return (
    <>
      <Bande items={[
        { label: "Population active", valeur: d.population_active, rendu: nb(d.population_active) },
        { label: "Actifs occupés", valeur: d.population_active_occupee, rendu: nb(d.population_active_occupee) },
        { label: "Population inactive", valeur: d.population_inactive, rendu: nb(d.population_inactive) },
        { label: "Prévalence du handicap", valeur: d.prevalence_handicap },
      ]} />

      <Grille>
        {parSexe.length > 0 && (
          <Bloc titre="Activité et chômage par sexe"
                but="Repérer si le chômage frappe surtout un sexe.">
            <Graphe hauteur={H_GRAPHE}>
              <BarChart data={parSexe}>
                <CartesianGrid stroke="#eef1f6" vertical={false} />
                <XAxis dataKey="nom" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 10 }} unit="%" />
                <Tooltip {...infobulle} formatter={(v) => `${dec(v)} %`} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Taux d'activité" fill={NAVY} radius={[5, 5, 0, 0]} />
                <Bar dataKey="Taux de chômage" fill={CORAL} radius={[5, 5, 0, 0]} />
              </BarChart>
            </Graphe>
          </Bloc>
        )}

        {statut.length > 0 && (
          <Bloc titre="Statut des actifs occupés"
                but="Structure de l'emploi : poids du salariat privé face à l'indépendant.">
            <Graphe hauteur={H_GRAPHE}>
              <PieChart>
                <Pie data={statut} dataKey="v" nameKey="nom" innerRadius="55%" outerRadius="85%" paddingAngle={2}>
                  {statut.map((s) => <Cell key={s.nom} fill={s.c} />)}
                </Pie>
                <Tooltip {...infobulle} formatter={(v, n) => [`${dec(v)} %`, n]} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 10.5 }} />
              </PieChart>
            </Graphe>
          </Bloc>
        )}
      </Grille>
    </>
  );
}

/* -------------------------------------------------------------- éducation */
function BlocEducation({ d }) {
  const NIVEAUX = [
    ["Aucun", "aucun", BAD], ["Préscolaire", "prescolaire", VIOLET], ["Primaire", "primaire", GOLD],
    ["Collégial", "college", BLUE], ["Qualifiant", "qualifiant", TEAL], ["Supérieur", "superieur", NAVY],
  ];
  const niveaux = NIVEAUX
    .map(([nom, cle, c]) => ({ nom, valeur: d.niveau_etudes?.[cle], c }))
    .filter((n) => n.valeur != null);

  const etab = d.etablissements;
  const detaille = etab && etab.primaire_public != null;
  const cycles = etab
    ? [["Primaire", "primaire"], ["Collégial", "collegial"], ["Qualifiant", "qualifiant"]]
        .map(([nom, cle]) => ({
          nom, valeur: etab[cle],
          Public: etab[`${cle}_public`], Privé: etab[`${cle}_prive`],
        }))
        .filter((e) => e.valeur != null)
    : [];

  return (
    <>
      <Bande items={[
        { label: "Analphabétisme femmes", valeur: d.analphabetisme_15_plus?.femmes, seuil: "analphabetisme" },
        { label: "Analphabétisme hommes", valeur: d.analphabetisme_15_plus?.hommes, seuil: "analphabetisme" },
        { label: "Scolarisation 6-11 ans", valeur: d.scolarisation_6_11, seuil: "scolarisation" },
        { label: "Établissements scolaires", valeur: etab?.total, rendu: nb(etab?.total) },
        { label: "Privation scolarisation", valeur: d.privations?.scolarisation, seuil: "privation" },
        { label: "Privation années d'étude", valeur: d.privations?.annees_scolarite, seuil: "privation" },
      ]} />

      <Grille>
        {niveaux.length > 0 && (
          <Bloc titre="Niveau d'études atteint"
                but="La part « aucun niveau » mesure le déficit de capital humain à corriger.">
            <Graphe hauteur={H_GRAPHE}>
              <BarChart data={niveaux} margin={{ left: -6 }}>
                <CartesianGrid stroke="#eef1f6" vertical={false} />
                <XAxis dataKey="nom" tick={{ fontSize: 9.5 }} interval={0} />
                <YAxis tick={{ fontSize: 10 }} unit="%" />
                <Tooltip {...infobulle} formatter={(v) => `${dec(v)} %`} />
                <Bar dataKey="valeur" radius={[5, 5, 0, 0]}>
                  {niveaux.map((n) => <Cell key={n.nom} fill={n.c} />)}
                </Bar>
              </BarChart>
            </Graphe>
          </Bloc>
        )}

        {cycles.length > 0 && (
          <Bloc titre="Établissements par cycle"
                but={detaille
                  ? "Offre scolaire du territoire, secteur public et privé (comptage officiel)."
                  : "Offre scolaire présente sur le territoire (somme de comptages)."}>
            <Graphe hauteur={H_GRAPHE - (etab.primaire_satellites != null ? 46 : 0)}>
              <BarChart data={cycles} layout="vertical" margin={{ left: 8, right: 12 }}>
                <CartesianGrid stroke="#eef1f6" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="nom" tick={{ fontSize: 10.5 }} width={70} />
                <Tooltip {...infobulle} formatter={(v) => nb(v)} />
                {detaille ? (
                  <>
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="Public" stackId="a" fill={NAVY} />
                    <Bar dataKey="Privé" stackId="a" fill={GOLD} radius={[0, 5, 5, 0]} />
                  </>
                ) : (
                  <Bar dataKey="valeur" radius={[0, 5, 5, 0]}>
                    {cycles.map((c, i) => <Cell key={c.nom} fill={[NAVY, BLUE, TEAL][i]} />)}
                  </Bar>
                )}
              </BarChart>
            </Graphe>
            {etab.primaire_satellites != null && (
              <p className="text-[11px] text-t2 mt-2">
                Dont <b>{nb(etab.primaire_satellites)}</b> satellites au primaire — unités scolaires
                rattachées à une école principale, fréquentes en milieu rural.
              </p>
            )}
            {etab.source && (
              <p className="text-[10.5px] text-t3 mt-2 leading-relaxed">Source : {etab.source}</p>
            )}
          </Bloc>
        )}
      </Grille>
    </>
  );
}

/* ------------------------------------------------------------------ santé */
function BlocSante({ d, estCommune }) {
  const RATIOS = [
    ["Médecin (public + privé)", "hab_par_medecin_public_prive", "hab_par_medecin"],
    ["Lit hospitalier", "hab_par_lit_public_prive", "hab_par_lit"],
    ["Infirmier (public)", "hab_par_infirmier_public", null],
    ["Officine", "hab_par_officine_total", null],
    ["ESSP", "hab_par_essp_total", null],
    ["Dentiste", "hab_par_dentiste_public_prive", null],
  ];
  const ratios = d.offre
    ? RATIOS.map(([label, cle, seuil]) => ({ label, v: d.offre[cle], seuil })).filter((r) => r.v != null)
    : [];

  const parCategorie = useMemo(() => {
    const m = new Map();
    (d.etablissements || []).forEach((e) => {
      const c = e.categorie || "Autre";
      m.set(c, (m.get(c) || 0) + 1);
    });
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [d.etablissements]);

  const grapheCat = parCategorie.slice(0, 8).map(([nom, valeur]) => ({ nom, valeur }));
  const liste = d.etablissements || [];

  return (
    <>
      {ratios.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 mb-4">
          {ratios.map((r) => (
            <Metrique key={r.label} label={r.label} valeur={nb(r.v)}
                      alerte={r.seuil ? niveauAlerte(r.v, SEUILS[r.seuil]) : null} />
          ))}
        </div>
      )}

      {d.privations && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
          {d.privations.mortalite_infantile != null &&
            <Metrique label="Priv. mortalité infantile" valeur={pct(d.privations.mortalite_infantile, 2)} />}
          {d.privations.handicap != null &&
            <Metrique label="Privation handicap" valeur={pct(d.privations.handicap)} />}
          {d.privations.contribution_mpi != null &&
            <Metrique label="Contribution santé au MPI" valeur={pct(d.privations.contribution_mpi)} />}
        </div>
      )}

      {liste.length > 0 && (
        <Grille cols={21}>
          <Bloc titre={`Établissements par catégorie (${liste.length} au total)`}
                but={estCommune
                  ? "Structures portées par cette commune dans la Carte Sanitaire."
                  : "Composition du réseau de soins public de la province."}>
            <Graphe hauteur={Math.max(190, grapheCat.length * 26)}>
              <BarChart data={grapheCat} layout="vertical" margin={{ left: 8, right: 14 }}>
                <CartesianGrid stroke="#eef1f6" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} allowDecimals={false} />
                <YAxis type="category" dataKey="nom" tick={{ fontSize: 10 }} width={62} />
                <Tooltip {...infobulle} formatter={(v) => `${nb(v)} établissement(s)`} />
                <Bar dataKey="valeur" fill={TEAL} radius={[0, 5, 5, 0]} />
              </BarChart>
            </Graphe>
          </Bloc>

          <Bloc titre="Liste des établissements" but="Détail nominatif, avec catégorie et réseau.">
            <div className="space-y-2 overflow-y-auto pr-1" style={{ maxHeight: 300 }}>
              {liste.map((e, i) => (
                <div key={`${e.nom}-${i}`} className="flex items-center gap-2.5 bg-bg rounded-xl px-3 py-2.5">
                  <span className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                        style={{ background: `${TEAL}1a`, color: TEAL }}>
                    {/^(CHD|HP|HPr|HR|HIR|HPsy)/.test(e.categorie || "")
                      ? <Building2 size={15} /> : <HeartPulse size={15} />}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-xs font-bold truncate">{e.nom}</span>
                    <span className="block text-[10.5px] text-t2">
                      {[e.categorie, e.reseau, e.milieu, e.service].filter(Boolean).join(" · ")}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </Bloc>
        </Grille>
      )}
    </>
  );
}

/* -------------------------------------------------------- conditions de vie */
function BlocConditions({ d, estCommune }) {
  const acces = d.habitat
    ? [["Eau courante", d.habitat.eau_courante, "eau_courante"],
       ["Électricité", d.habitat.electricite, null],
       ["Assainissement", d.habitat.assainissement, "assainissement"]]
        .filter(([, v]) => v != null)
        .map(([nom, v, cle]) => ({ nom, valeur: v, c: COULEUR_ALERTE[niveauAlerte(v, SEUILS[cle]) || "ok"] }))
    : [];

  const privations = d.privations
    ? [["Eau", d.privations.eau], ["Électricité", d.privations.electricite],
       ["Assainissement", d.privations.assainissement], ["Logement", d.privations.logement],
       ["Cuisson", d.privations.cuisson], ["Communication", d.privations.communication]]
        .filter(([, v]) => v != null)
        .map(([nom, v]) => ({ nom, valeur: v, c: COULEUR_ALERTE[niveauAlerte(v, SEUILS.privation)] }))
    : [];

  const MODES = [
    ["À pieds", "a_pieds", CORAL], ["Transport employeur", "employeur", VIOLET],
    ["Voiture privée", "voiture", BLUE], ["Taxi", "taxi", GOLD], ["Bus", "bus", TEAL],
    ["Moto / vélo", "moto_velo", NAVY], ["Ne se déplace pas", "ne_se_deplace_pas", "#c3ccd8"],
  ];
  const transport = d.transport
    ? MODES.map(([nom, cle, c]) => ({ nom, v: d.transport[cle], c })).filter((m) => m.v != null && m.v > 0)
    : [];

  const p = d.pauvrete;

  return (
    <>
      <Bande items={[
        { label: "Taux de pauvreté", valeur: p?.taux_pauvrete, seuil: "taux_pauvrete" },
        { label: "Vulnérabilité", valeur: p?.vulnerabilite, seuil: "vulnerabilite" },
        { label: "Intensité", valeur: p?.intensite },
        { label: "Indice MPI", valeur: p?.mpi, rendu: dec(p?.mpi, 3) },
        { label: "Utilisation d'Internet", valeur: d.numerique?.internet, seuil: "internet" },
        { label: "Ordinateur personnel", valeur: d.numerique?.ordinateur },
      ]} />

      <Grille>
        {acces.length > 0 && (
          <Bloc titre="Accès des ménages aux services"
                but="Taux d'équipement du logement. Sous 85 %, on parle d'un déficit d'infrastructure de base.">
            <Graphe hauteur={H_GRAPHE}>
              <BarChart data={acces} margin={{ left: -6 }}>
                <CartesianGrid stroke="#eef1f6" vertical={false} />
                <XAxis dataKey="nom" tick={{ fontSize: 10.5 }} />
                <YAxis tick={{ fontSize: 10 }} unit="%" domain={[0, 100]} />
                <Tooltip {...infobulle} formatter={(v) => `${dec(v)} %`} />
                <Bar dataKey="valeur" radius={[5, 5, 0, 0]}>
                  {acces.map((a) => <Cell key={a.nom} fill={a.c} />)}
                </Bar>
              </BarChart>
            </Graphe>
          </Bloc>
        )}

        {privations.length > 0 && (
          <Bloc titre="Privations dans les conditions de vie"
                but="Part des ménages privés de chaque service — cible directe d'investissement.">
            <Graphe hauteur={H_GRAPHE}>
              <BarChart data={privations} layout="vertical" margin={{ left: 8, right: 12 }}>
                <CartesianGrid stroke="#eef1f6" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} unit="%" />
                <YAxis type="category" dataKey="nom" tick={{ fontSize: 10 }} width={92} />
                <Tooltip {...infobulle} formatter={(v) => `${dec(v)} %`} />
                <Bar dataKey="valeur" radius={[0, 5, 5, 0]}>
                  {privations.map((x) => <Cell key={x.nom} fill={x.c} />)}
                </Bar>
              </BarChart>
            </Graphe>
          </Bloc>
        )}

        {transport.length > 0 && (
          <Bloc titre="Déplacement domicile-travail"
                but="Une forte dépendance à la marche ou au transport informel révèle un enclavement."
                className={acces.length > 0 && privations.length > 0 ? "lg:col-span-2" : ""}>
            <Graphe hauteur={H_GRAPHE}>
              <PieChart>
                <Pie data={transport} dataKey="v" nameKey="nom" innerRadius="55%" outerRadius="85%" paddingAngle={2}>
                  {transport.map((t) => <Cell key={t.nom} fill={t.c} />)}
                </Pie>
                <Tooltip {...infobulle} formatter={(v, n) => [`${dec(v)} %`, n]} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 10.5 }} />
              </PieChart>
            </Graphe>
          </Bloc>
        )}
      </Grille>
    </>
  );
}
