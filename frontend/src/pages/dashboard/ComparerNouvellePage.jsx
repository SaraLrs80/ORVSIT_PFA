// Comparer des territoires — version pilotée par le catalogue.
//
// Ce que cette page change par rapport à ComparerPage : elle n'appelle plus
// /comparer, donc plus fiche.py ni sa liste d'indicateurs écrite en dur. Elle
// lit les deux mêmes routes que la fiche — /fiche-nouvelle/familles pour la
// structure, /fiche-nouvelle/valeurs pour les chiffres — et fait le reste ici.
// Aucun endpoint n'a été ajouté : la comparaison n'avait besoin d'aucune
// donnée que la fiche ne demandait déjà.
//
// Trois conséquences :
//   - on passe de douze indicateurs choisis à la main à tout le catalogue ;
//   - au niveau communal, /valeurs ne renvoie que les communes d'UNE province,
//     donc la comparaison ne peut plus mêler deux provinces — c'était la
//     demande de l'encadrante, obtenue par construction et non par un contrôle ;
//   - fiche.py et comparer.py n'ont plus de lecteur et pourront être retirés.
//
// Quatre lectures, dans cet ordre :
//   1. qui compare-t-on — carte cliquable et pastilles
//   2. ce qui les sépare — les écarts les plus marqués
//   3. où chacun se situe parmi TOUS ses pairs, et pas seulement face à l'autre
//   4. le détail secteur par secteur

import { useEffect, useMemo, useState } from "react";
import {
  Users, BriefcaseBusiness, GraduationCap, HeartPulse, House,
  X, ArrowLeftRight, Search,
} from "lucide-react";
import DashboardLayout from "../../components/DashboardLayout";
import BarreExport from "../../components/BarreExport";
import CarteIndicateur from "../../components/fiche/CarteIndicateur";
import { getFamilles, getValeurs } from "../../api/ficheNouvelle";
import {
  SECTEURS, COUL, nb, dec, court, sourceCourte, valeur, cleFamille, ordinal,
} from "../../components/fiche/outils";

const ICONES = {
  "Démographie": Users, "Emploi": BriefcaseBusiness, "Éducation": GraduationCap,
  "Santé": HeartPulse, "Conditions de vie": House,
};

// Quatre couleurs franchement distinctes, prises dans la palette ORVSIT.
// Au-delà de quatre territoires, aucune palette ne reste lisible : c'est la
// vraie raison de la limite, et non une contrainte technique.
const COULEURS = ["#001f5f", "#e8af20", "#2563eb", "#0f9f72"];
const MAX = 4;

// Qui est en tête, et avec quels mots.
// Un taux de chômage bas est un bon résultat ; un effectif élevé n'est ni bon
// ni mauvais. Parler de « meilleur » pour une population serait un jugement
// que la donnée ne porte pas.
function verdict(sens, presents) {
  const tri = [...presents].sort((a, b) => b.v - a.v);
  const haut = tri[0], bas = tri[tri.length - 1];
  if (sens === "haut_mieux") return { tete: haut, queue: bas, juge: true };
  if (sens === "bas_mieux") return { tete: bas, queue: haut, juge: true };
  return { tete: haut, queue: bas, juge: false };
}

export default function ComparerNouvellePage() {
  /* ---------------------------------------------------------------- données */
  const [familles, setFamilles] = useState({ prefecture_province: [], commune: [] });
  const [dProv, setDProv] = useState(null);
  const [dComm, setDComm] = useState(null);
  const [geo, setGeo] = useState({ provinces: null, communes: null });
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  /* -------------------------------------------------------------- affichage */
  const [niveau, setNiveau] = useState("prefecture_province");
  const [provinceId, setProvinceId] = useState(null);
  const [ids, setIds] = useState([]);
  const [secteur, setSecteur] = useState("Démographie");
  const [q, setQ] = useState("");

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
        const tries = Object.keys(vp.territoires).sort((a, b) =>
          vp.territoires[a].localeCompare(vp.territoires[b], "fr"));
        setProvinceId(tries[0]);
        // Deux territoires d'emblée : un écran de comparaison vide n'apprend
        // rien et n'explique pas ce qu'on attend de l'utilisateur.
        setIds(tries.slice(0, 2));
        setChargement(false);
      })
      .catch((e) => { if (vivant) { setErreur(e.message); setChargement(false); } });
    return () => { vivant = false; };
  }, []);

  useEffect(() => {
    if (niveau !== "commune" || !provinceId) return;
    let vivant = true;
    setDComm(null);
    getValeurs("commune", provinceId)
      .then((d) => {
        if (!vivant) return;
        setDComm(d);
        setIds(Object.keys(d.territoires)
          .sort((a, b) => d.territoires[a].localeCompare(d.territoires[b], "fr"))
          .slice(0, 2));
      })
      .catch((e) => vivant && setErreur(e.message));
    return () => { vivant = false; };
  }, [niveau, provinceId]);

  /* ---------------------------------------------------------------- dérivés */
  const donnees = niveau === "commune" ? dComm : dProv;
  const catalogue = familles[niveau] || [];
  const pairs = useMemo(() => (donnees ? Object.keys(donnees.territoires) : []), [donnees]);
  const nomDe = (id) => donnees?.territoires?.[String(id)] || "";
  const val = (indicateurId, territoire, cle) =>
    valeur(donnees?.valeurs, indicateurId, territoire, undefined);

  const couleurDe = (id) => COULEURS[ids.indexOf(String(id))] ?? null;
  const selection = useMemo(() => {
    const s = {};
    ids.forEach((id, i) => { s[String(id)] = COULEURS[i]; });
    return s;
  }, [ids]);

  function basculer(id) {
    const t = String(id);
    setIds((l) => l.includes(t)
      ? (l.length > 2 ? l.filter((x) => x !== t) : l)   // jamais moins de deux
      : (l.length >= MAX ? l : [...l, t]));
  }

  const fc = useMemo(() => {
    const src = niveau === "commune" ? geo.communes : geo.provinces;
    if (!src || !pairs.length) return null;
    const dedans = new Set(pairs.map(String));
    return {
      type: "FeatureCollection",
      features: src.features
        .filter((f) => dedans.has(String(f.properties.territoire_id)))
        .map((f) => ({
          type: "Feature",
          properties: { id: String(f.properties.territoire_id) },
          geometry: f.geometry,
        })),
    };
  }, [geo, niveau, pairs]);

  /* --------------------------------- tous les objets comparables, à plat --- */
  const objets = useMemo(() => catalogue.flatMap((f) => {
    const cle = cleFamille(f);
    return f.membres.map((m) => ({
      f, m, cle,
      nom: f.membres.length > 1 ? `${f.nom} — ${m.etiquette}` : f.nom,
    }));
  }), [catalogue]);

  /* ----------------------------------------------------------- les écarts --- */
  // On classe sur l'écart RELATIF, jamais sur l'écart brut : sinon « 8 500
  // habitants par médecin » écraserait toujours « 12 points de chômage »,
  // alors que le second est le plus parlant pour décider.
  const ecarts = useMemo(() => {
    if (ids.length < 2 || !donnees) return [];
    const out = [];
    objets.forEach((o) => {
      const presents = ids
        .map((t) => ({ t, v: val(o.m.indicateur_id, t, o.cle) }))
        .filter((x) => x.v != null);
      if (presents.length < 2) return;
      const vs = presents.map((x) => x.v);
      const mx = Math.max(...vs), mn = Math.min(...vs);
      const reference = Math.max(...vs.map(Math.abs)) || 1;
      out.push({ ...o, presents, ecart: mx - mn, relatif: (mx - mn) / reference });
    });
    return out.sort((a, b) => b.relatif - a.relatif);
  }, [objets, ids, donnees]);

  // Les écarts les plus marqués, mais DEUX PAR SECTEUR et non les dix premiers
  // toutes rubriques confondues. Un classement à plat peut être occupé en
  // entier par la démographie — non parce que les autres domaines se
  // ressemblent, mais parce que leurs unités varient moins. Le tour d'horizon
  // doit couvrir les cinq secteurs ; les secteurs sont ensuite rangés par
  // l'ampleur de leur plus grand écart.
  const apercu = useMemo(() => {
    const par = {};
    ecarts.forEach((o) => {
      const l = (par[o.f.secteur] ||= []);
      if (l.length < 2) l.push(o);
    });
    return Object.entries(par).sort((a, b) => b[1][0].relatif - a[1][0].relatif);
  }, [ecarts]);

  /* ------------------------------------------------------------ les rangs --- */
  // Le rang se lit sur TOUS les pairs, pas sur les seuls territoires comparés :
  // « 2ᵉ sur 8 » dit quelque chose que « mieux que l'autre » ne dit pas.
  const rangDe = (o, t) => {
    const serie = pairs
      .map((x) => ({ x, v: val(o.m.indicateur_id, x, o.cle) }))
      .filter((y) => y.v != null)
      .sort((a, b) => (o.f.sens === "bas_mieux" ? a.v - b.v : b.v - a.v));
    const i = serie.findIndex((y) => String(y.x) === String(t));
    return i < 0 ? null : { rang: i + 1, total: serie.length };
  };

  /* ------------------------------------------------------------------ export */
  // Valeurs en nombres : le CSV les mettra en forme, Excel les gardera sommables.
  function lignesExport() {
    const colonnes = ["Secteur", "Indicateur", "Unité", "Millésime",
                      ...ids.map((t) => court(nomDe(t))),
                      "Écart", "En tête", "Source"];
    const lignes = [];
    const parSecteur = {};
    objets.forEach((o) => {
      const vals = ids.map((t) => val(o.m.indicateur_id, t, o.cle));
      if (vals.every((v) => v == null)) return;
      const presents = ids.map((t, i) => ({ t, v: vals[i] })).filter((x) => x.v != null);
      const vs = presents.map((x) => x.v);
      const { tete, juge } = verdict(o.f.sens, presents);
      const ligne = [
        o.f.secteur, o.nom, o.f.unite || "", o.f.annee || "",
        ...vals.map((v) => (v == null ? "" : v)),
        presents.length > 1 ? Math.max(...vs) - Math.min(...vs) : "",
        // « En tête » n'a de sens que si le catalogue déclare un sens favorable.
        presents.length > 1 && juge ? court(nomDe(tete.t)) : "",
        o.f.source || "",
      ];
      lignes.push(ligne);
      (parSecteur[o.f.secteur] ||= []).push(ligne);
    });
    return {
      colonnes, lignes,
      feuilles: SECTEURS.filter((s) => parSecteur[s]?.length)
        .map((s) => ({ nom: s, colonnes, lignes: parSecteur[s] })),
      entete: [
        `Comparaison — ${ids.map((t) => court(nomDe(t))).join(" · ")}`,
        `${lignes.length} valeurs · rangs établis sur ${pairs.length} territoires de même niveau`,
        "La colonne « En tête » reste vide pour les indicateurs sans sens favorable.",
      ],
    };
  }

  /* -------------------------------------------------------------------- rendu */
  if (chargement)
    return <DashboardLayout title="Comparer" active="comparer">
      <p className="text-t2 text-sm">Chargement du catalogue…</p></DashboardLayout>;
  if (erreur)
    return <DashboardLayout title="Comparer" active="comparer">
      <p className="text-coral text-sm">{erreur}</p></DashboardLayout>;

  const nomProvince = dProv?.territoires?.[String(provinceId)] || "";
  const dispos = pairs.filter((t) => !ids.includes(String(t)));

  return (
    <DashboardLayout title="Comparer" active="comparer">

      {/* ════════════════════════ 1 · QUI COMPARE-T-ON ═══════════════════════ */}
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <div className="text-[11px] font-extrabold uppercase tracking-[0.12em] text-t3">
            Région Tanger–Tétouan–Al Hoceïma
            {niveau === "commune" && nomProvince ? ` · ${nomProvince}` : ""}
          </div>
          <h1 className="text-[42px] font-extrabold text-navy leading-[1.05] mt-1.5">
            Comparer {ids.length} territoires
          </h1>
          <div className="text-[13px] text-t2 mt-2">
            {catalogue.length} objets d'information · rangs établis sur{" "}
            {pairs.length} {niveau === "commune" ? "communes de la province" : "préfectures et provinces"}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Choix value={niveau} onChange={setNiveau}>
            <option value="prefecture_province">Niveau préfecture / province</option>
            <option value="commune">Niveau commune</option>
          </Choix>
          {/* Au niveau communal, la province se choisit d'abord. Ce n'est pas
              un confort : c'est ce qui garantit qu'on ne compare jamais des
              communes de provinces différentes. */}
          {niveau === "commune" && (
            <Choix value={provinceId || ""} onChange={setProvinceId}>
              {Object.keys(dProv?.territoires || {})
                .sort((a, b) => dProv.territoires[a].localeCompare(dProv.territoires[b], "fr"))
                .map((id) => <option key={id} value={id}>{dProv.territoires[id]}</option>)}
            </Choix>
          )}
          <BarreExport nom="comparaison" donnees={lignesExport} />
        </div>
      </div>

      {/* pastilles des territoires retenus */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        {ids.map((t, i) => (
          <span key={t}
            className="inline-flex items-center gap-2 bg-white border border-line rounded-full
                       pl-2.5 pr-1.5 py-1.5 ombre-orvsit">
            <i className="w-3 h-3 rounded-[4px] shrink-0" style={{ background: COULEURS[i] }} />
            <span className="text-[12.5px] font-bold text-navy max-w-[22ch] truncate">
              {court(nomDe(t))}
            </span>
            <button onClick={() => basculer(t)} disabled={ids.length <= 2}
              title={ids.length <= 2 ? "Il faut au moins deux territoires" : "Retirer"}
              className="w-5 h-5 grid place-items-center rounded-full text-t3
                         hover:text-coral hover:bg-bg disabled:opacity-30 transition-colors">
              <X size={12} />
            </button>
          </span>
        ))}

        {ids.length < MAX && dispos.length > 0 && (
          <Choix value="" onChange={(v) => v && basculer(v)}>
            <option value="">+ Ajouter un territoire…</option>
            {dispos
              .sort((a, b) => nomDe(a).localeCompare(nomDe(b), "fr"))
              .map((t) => <option key={t} value={t}>{court(nomDe(t))}</option>)}
          </Choix>
        )}
        {ids.length >= MAX && (
          <span className="text-[11px] text-t3">
            Quatre territoires au plus — au-delà, aucune palette ne reste lisible.
          </span>
        )}
      </div>

      {/* ═══════════════════ 2 · CARTE ET CE QUI LES SÉPARE ══════════════════ */}
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] gap-4 mb-4">

        <section className="bg-white border border-line rounded-3xl ombre-orvsit p-5 flex flex-col">
          <header className="mb-3">
            <h2 className="text-[15px] font-extrabold text-navy">Territoires comparés</h2>
            <p className="text-[11.5px] text-t3 mt-0.5">
              cliquez un territoire pour l'ajouter ou le retirer
            </p>
          </header>
          <div className="relative h-[380px]">
            <div className="absolute inset-0">
              <CarteIndicateur geojson={fc} serie={{}} selection={selection}
                               nomDe={nomDe} onSelect={basculer} fond="Clair" />
            </div>
          </div>
        </section>

        <section className="bg-white border border-line rounded-3xl ombre-orvsit p-5">
          <header className="flex flex-wrap items-baseline gap-3 mb-4">
            <h2 className="text-[15px] font-extrabold text-navy">Ce qui les sépare</h2>
            <span className="text-[11.5px] text-t3">
              les deux écarts les plus marqués de chaque secteur
            </span>
          </header>
          {apercu.length === 0 ? (
            <p className="text-[12px] text-t3">
              Aucun indicateur n'est renseigné pour au moins deux de ces territoires.
            </p>
          ) : (
            <div className="max-h-[380px] overflow-y-auto defil-fin pr-1">
              {apercu.map(([s, liste]) => {
                const c = COUL[s];
                const Icone = ICONES[s];
                return (
                  <div key={s} className="mb-4 last:mb-0">
                    <button onClick={() => {
                        setSecteur(s);
                        document.getElementById("detail")?.scrollIntoView(
                          { behavior: "smooth", block: "start" });
                      }}
                      className="flex items-center gap-1.5 text-[9.5px] font-extrabold uppercase
                                 tracking-[0.1em] mb-2 hover:underline"
                      style={{ color: c.s }}
                      title={`Voir tout le secteur ${s}`}>
                      <span className="w-5 h-5 rounded-md grid place-items-center"
                            style={{ background: c.f, color: c.t }}><Icone size={11} /></span>
                      {s}
                    </button>
                    <div className="space-y-3">
                      {liste.map((o) => (
                        <LigneEcart key={o.m.indicateur_id}
                                    o={o} ids={ids} nomDe={nomDe} couleurDe={couleurDe} />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>

      {/* ══════════════════════ 3 · DÉTAIL PAR SECTEUR ═══════════════════════ */}
      <section id="detail" className="bg-white border border-line rounded-3xl ombre-orvsit p-6">
        <header className="flex flex-wrap items-baseline gap-3 mb-4">
          <h2 className="text-[17px] font-extrabold text-navy">Détail par secteur</h2>
          <span className="text-[11.5px] text-t3">
            classés du plus discriminant au moins discriminant · le rang situe le territoire
            parmi ses {pairs.length} pairs, pas face aux autres colonnes
          </span>
          <div className="ml-auto relative">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-t3" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher un indicateur…"
              className="bg-bg border border-line rounded-[10px] pl-8 pr-3 py-2 text-[12px]
                         outline-none focus:border-navy-3 transition-colors w-56" />
          </div>
        </header>

        <div className="flex flex-wrap gap-1.5 mb-5">
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
                  ? { background: c.t, borderColor: c.t, color: "#fff", boxShadow: `0 5px 14px ${c.t}33` }
                  : { background: "#fff", borderColor: "#e8ecf3", color: c.s }}>
                <Icone size={14} /> {s}
                <b className={`text-[10px] px-2 py-0.5 rounded-full ${actif ? "bg-white/20" : "bg-bg"}`}>
                  {n}
                </b>
              </button>
            );
          })}
        </div>

        <TableauSecteur objets={objets} secteur={secteur} q={q} ids={ids}
                        val={val} nomDe={nomDe} rangDe={rangDe} niveau={niveau} />
      </section>
    </DashboardLayout>
  );
}

/* ═══════════════════════════════ petits blocs ═══════════════════════════════ */

function Choix({ value, onChange, children }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}
      className="text-[12px] font-bold text-navy bg-white border border-line rounded-[10px]
                 px-3 py-2 outline-none focus:border-navy-3 transition-colors max-w-[240px]">
      {children}
    </select>
  );
}

/* ------------------------------------------------------------- un écart ---- */

function LigneEcart({ o, ids, nomDe, couleurDe }) {
  const vs = o.presents.map((x) => x.v);
  const d = dec(vs);
  const mx = Math.max(...vs.map(Math.abs)) || 1;
  const { tete, juge } = verdict(o.f.sens, o.presents);

  return (
    <div>
      <div className="flex items-baseline gap-2 mb-1.5">
        <span className="text-[12.5px] font-bold text-t1 flex-1 min-w-0 truncate" title={o.nom}>
          {o.nom}
        </span>
        <span className="text-[11px] font-extrabold text-navy tabular-nums shrink-0">
          écart {nb(Math.max(...vs) - Math.min(...vs), d)} {o.f.unite || ""}
        </span>
      </div>

      {/* Une barre par territoire, dans l'ordre de la sélection : c'est cet
          ordre qui fixe les couleurs, il ne doit pas changer d'un bloc à l'autre. */}
      {ids.map((t) => {
        const p = o.presents.find((x) => String(x.t) === String(t));
        return (
          <div key={t} className="flex items-center gap-2 mb-1">
            <span className="w-[26%] text-[10.5px] text-t2 truncate">{court(nomDe(t))}</span>
            <div className="flex-1 h-[10px] bg-[#eef2f8] rounded-full overflow-hidden">
              {p && <i className="block h-full rounded-full"
                       style={{ width: `${Math.max(2, (100 * Math.abs(p.v)) / mx).toFixed(1)}%`,
                                background: couleurDe(t) }} />}
            </div>
            <span className="text-[11px] font-extrabold tabular-nums min-w-[64px] text-right">
              {p ? nb(p.v, d) : "—"}
            </span>
          </div>
        );
      })}

      <div className="text-[10px] text-t3 mt-1 pl-[26%]">
        {juge
          ? <><b className="text-t2">{court(nomDe(tete.t))}</b> est le mieux placé</>
          : <><b className="text-t2">{court(nomDe(tete.t))}</b> a la valeur la plus élevée —
              cet indicateur n'a pas de sens favorable</>}
      </div>
    </div>
  );
}

/* --------------------------------------------------------- tableau secteur -- */

function TableauSecteur({ objets, secteur, q, ids, val, nomDe, rangDe, niveau }) {
  const [tout, setTout] = useState(false);
  const filtre = q.trim().toLowerCase();
  const VISIBLES = 12;

  // On prépare chaque ligne une seule fois, puis on trie par ÉCART RELATIF
  // décroissant. L'ordre du catalogue est arbitraire pour qui compare : il
  // impose de parcourir soixante lignes pour trouver les cinq qui distinguent
  // vraiment les territoires. Trié ainsi, le haut du tableau est la réponse et
  // le bas ne fait que confirmer que le reste se ressemble.
  const lignes = useMemo(() => objets
    .filter((o) => o.f.secteur === secteur && (!filtre || o.nom.toLowerCase().includes(filtre)))
    .map((o) => {
      const cells = ids.map((t) => ({ t, v: val(o.m.indicateur_id, t, o.cle) }));
      const presents = cells.filter((x) => x.v != null);
      const vs = presents.map((x) => x.v);
      const ecart = vs.length > 1 ? Math.max(...vs) - Math.min(...vs) : null;
      const reference = vs.length ? Math.max(...vs.map(Math.abs)) || 1 : 1;
      return {
        o, cells, presents, d: dec(vs),
        ecart, relatif: ecart == null ? -1 : ecart / reference,
        ...(presents.length > 1 ? verdict(o.f.sens, presents) : { tete: null, juge: false }),
      };
    })
    .filter((l) => l.presents.length > 0)
    .sort((a, b) => b.relatif - a.relatif), [objets, secteur, filtre, ids, val]);

  if (!lignes.length)
    return <p className="text-[12px] text-t3">
      Aucun indicateur renseigné pour ces territoires dans ce secteur.
    </p>;

  const montrees = tout ? lignes : lignes.slice(0, VISIBLES);
  const caches = lignes.length - montrees.length;

  return (
    <div className="border border-line rounded-[18px] overflow-hidden">
      <div className="overflow-x-auto max-h-[620px] overflow-y-auto defil-fin">
        <table className="w-full text-[12.5px]">
          {/* En-tête collant : sur un tableau qui défile, perdre le nom des
              colonnes revient à perdre le sens des chiffres. */}
          <thead className="bg-bg sticky top-0 z-10">
            <tr className="text-[9.5px] font-extrabold uppercase tracking-[0.09em] text-t2">
              <th className="text-left px-4 py-3 min-w-[230px]">Indicateur</th>
              {ids.map((t, i) => (
                <th key={t} className="text-right px-4 py-3 whitespace-nowrap">
                  <span className="inline-flex items-center gap-1.5">
                    <i className="w-2 h-2 rounded-[3px]" style={{ background: COULEURS[i] }} />
                    {court(nomDe(t))}
                  </span>
                </th>
              ))}
              <th className="text-right px-4 py-3 whitespace-nowrap w-[160px]">Écart</th>
            </tr>
          </thead>
          <tbody>
            {montrees.map(({ o, cells, presents, d, ecart, relatif, tete, juge }) => (
              <tr key={`${o.f.secteur}-${o.m.indicateur_id}`}
                  className="border-t border-line-2 hover:bg-bg transition-colors">
                <td className="px-4 py-2.5">
                  <div className="font-bold text-t1 leading-snug">{o.nom}</div>
                  <div className="text-[9.5px] text-t3 truncate max-w-[380px]" title={o.f.source}>
                    {o.f.annee} · {o.f.unite || "—"} · {sourceCourte(o.f.source)}
                  </div>
                </td>
                {cells.map(({ t, v }) => {
                  const r = v == null ? null : rangDe(o, t);
                  const enTete = juge && tete && String(tete.t) === String(t);
                  return (
                    <td key={t} className="px-4 py-2.5 text-right whitespace-nowrap">
                      <div className={`tabular-nums ${enTete ? "font-extrabold text-navy" : "font-bold"}`}>
                        {nb(v, d)}
                      </div>
                      {r && (
                        <div className="text-[9.5px] text-t3">
                          {r.rang}<sup>{ordinal(r.rang)}</sup> / {r.total}
                        </div>
                      )}
                    </td>
                  );
                })}
                {/* L'écart porte une barre : c'est elle qui permet de balayer la
                    colonne du regard et de s'arrêter là où les territoires
                    divergent, sans lire chaque nombre. */}
                <td className="px-4 py-2.5">
                  {ecart == null ? (
                    <div className="text-right text-t3">—</div>
                  ) : (
                    <div className="flex items-center gap-2 justify-end">
                      <div className="w-[64px] h-[6px] bg-[#eef2f8] rounded-full overflow-hidden">
                        <i className="block h-full rounded-full"
                           style={{ width: `${Math.max(3, Math.min(100, relatif * 100)).toFixed(0)}%`,
                                    background: COUL[o.f.secteur].t }} />
                      </div>
                      <span className="tabular-nums font-bold text-t2 min-w-[58px] text-right">
                        {nb(ecart, d)}
                      </span>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="px-4 py-2.5 bg-bg border-t border-line flex flex-wrap items-center gap-3">
        <span className="text-[10px] text-t3 flex-1 min-w-[260px]">
          {lignes.length} indicateur{lignes.length > 1 ? "s" : ""}, classés du plus discriminant
          au moins discriminant · rang établi parmi l'ensemble des{" "}
          {niveau === "commune" ? "communes de la province" : "préfectures et provinces"} · une case
          vide signale une absence de donnée, jamais un zéro
        </span>
        {(caches > 0 || tout) && (
          <button onClick={() => setTout((v) => !v)}
            className="text-[11px] font-extrabold text-navy hover:underline shrink-0">
            {tout ? `Ne montrer que les ${VISIBLES} premiers`
                  : `Afficher les ${caches} autres indicateurs`}
          </button>
        )}
      </div>
    </div>
  );
}
