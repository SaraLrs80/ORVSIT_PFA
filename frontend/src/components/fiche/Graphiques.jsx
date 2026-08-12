// Les cinq formes de représentation de la fiche — et pas une de plus.
//
// Le choix de la forme n'est pas fait ici : il vient du backend, qui a vérifié
// sur la donnée si les parts composent un tout. Ce fichier ne fait que dessiner
// la forme demandée. Cette séparation compte : la décision « anneau ou barres »
// est une décision statistique, elle doit être prise là où la donnée est lue,
// pas dans le navigateur.
//
//   chiffre   une valeur unique, avec son rang parmi les pairs
//   anneau    2 ou 3 parts qui totalisent 100 %
//   empile    4 parts et plus qui totalisent 100 %
//   barres    des taux indépendants, classés du plus fort au plus faible
//   groupe    le même indicateur selon ses déclinaisons
//   pyramide  l'âge quinquennal, seul graphique à deux côtés

import { QUALI, RAMPE, nb, dec, valeur } from "./outils";

/* -------------------------------------------------------------------- anneau */

export function Anneau({ famille, valeurs, territoire, vent }) {
  const parts = famille.membres
    .map((m, j) => ({
      e: m.etiquette,
      v: valeur(valeurs, m.indicateur_id, territoire, vent) ?? 0,
      c: QUALI[j % QUALI.length],
    }))
    .filter((p) => p.v > 0);

  if (!parts.length) return <Vide />;

  const total = parts.reduce((a, p) => a + p.v, 0) || 1;
  const R = 54, r = 33, cx = 68, cy = 68;
  let angle = -Math.PI / 2;

  const arcs = parts.map((p) => {
    const a0 = angle;
    const a1 = a0 + (2 * Math.PI * p.v) / total;
    angle = a1;
    const grand = a1 - a0 > Math.PI ? 1 : 0;
    const P = (ra, an) => [cx + ra * Math.cos(an), cy + ra * Math.sin(an)];
    const [x1, y1] = P(R, a0), [x2, y2] = P(R, a1);
    const [x3, y3] = P(r, a1), [x4, y4] = P(r, a0);
    return {
      ...p,
      d: `M${x1.toFixed(1)} ${y1.toFixed(1)}A${R} ${R} 0 ${grand} 1 ${x2.toFixed(1)} ${y2.toFixed(1)}` +
         `L${x3.toFixed(1)} ${y3.toFixed(1)}A${r} ${r} 0 ${grand} 0 ${x4.toFixed(1)} ${y4.toFixed(1)}Z`,
    };
  });

  // Le centre porte la part dominante : c'est l'information qu'on retient
  // d'un anneau, autant l'écrire plutôt que de la faire deviner.
  const dominante = [...parts].sort((a, b) => b.v - a.v)[0];

  return (
    <div className="flex gap-4 items-center">
      <svg viewBox="0 0 136 136" className="w-[136px] shrink-0">
        {arcs.map((p) => (
          <path key={p.e} d={p.d} fill={p.c}>
            <title>{`${p.e} : ${nb(p.v)} %`}</title>
          </path>
        ))}
        <text x="68" y="64" textAnchor="middle" fontSize="19" fontWeight="800" fill="#0f2f56">
          {nb(dominante.v, 0)}%
        </text>
        <text x="68" y="79" textAnchor="middle" fontSize="8.5" fill="#64748b">
          {dominante.e.slice(0, 16)}
        </text>
      </svg>
      <div className="flex-1 min-w-0">
        {parts.map((p) => (
          <div key={p.e} className="flex items-center gap-[7px] text-[11.5px] mb-[5px]">
            <i className="w-2.5 h-2.5 rounded-[3px] shrink-0" style={{ background: p.c }} />
            <span className="flex-1 truncate text-[#1a2b47]">{p.e}</span>
            <b className="tabular-nums">{nb(p.v)} %</b>
          </div>
        ))}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------- empilé */

export function Empile({ famille, valeurs, territoire, vent }) {
  const parts = famille.membres
    .map((m, j) => ({
      e: m.etiquette,
      v: valeur(valeurs, m.indicateur_id, territoire, vent) ?? 0,
      c: QUALI[j % QUALI.length],
    }))
    .filter((p) => p.v > 0);

  if (!parts.length) return <Vide />;
  const total = parts.reduce((a, p) => a + p.v, 0) || 1;

  return (
    <div>
      <div className="flex h-[30px] rounded-[7px] overflow-hidden mb-[11px]">
        {parts.map((p) => {
          const largeur = (100 * p.v) / total;
          return (
            <div key={p.e} title={`${p.e} : ${nb(p.v)} %`}
                 className="h-full grid place-items-center text-white text-[10px] font-bold overflow-hidden"
                 style={{ width: `${largeur}%`, background: p.c }}>
              {/* Sous 7 % de large, le chiffre déborde de son segment : on le
                  laisse à l'infobulle plutôt que d'écrire par-dessus le voisin. */}
              {largeur > 7 ? nb(p.v, 0) : ""}
            </div>
          );
        })}
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        {parts.map((p) => (
          <div key={p.e} className="flex items-center gap-1.5 text-[11px]">
            <i className="w-[9px] h-[9px] rounded-[2px] shrink-0" style={{ background: p.c }} />
            <span className="flex-1 truncate text-t2">{p.e}</span>
            <b className="tabular-nums text-[#1a2b47]">{nb(p.v)}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------- barres */

export function Barres({ famille, valeurs, territoire, vent }) {
  const l = famille.membres
    .map((m) => ({ e: m.etiquette, v: valeur(valeurs, m.indicateur_id, territoire, vent) }))
    .filter((p) => p.v != null)
    .sort((a, b) => b.v - a.v);

  if (!l.length) return <Vide />;
  const mx = Math.max(...l.map((p) => p.v));
  const d = dec(l.map((p) => p.v));

  return (
    <div>
      {l.map((p, j) => (
        <div key={p.e} className="flex items-center gap-[9px] mb-[7px]">
          <span className="w-[44%] text-[11.5px] text-[#1a2b47] truncate" title={p.e}>{p.e}</span>
          <div className="flex-1 h-[13px] bg-bg rounded overflow-hidden">
            <i className="block h-full rounded"
               style={{
                 width: `${((100 * p.v) / mx).toFixed(1)}%`,
                 background: RAMPE[Math.max(0, 4 - Math.floor((j * 5) / l.length))],
               }} />
          </div>
          <b className="text-[11.5px] tabular-nums min-w-[52px] text-right">
            {nb(p.v, d)}<span className="text-t3 font-semibold"> {famille.unite || ""}</span>
          </b>
        </div>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------- groupe */

// Ventilations comparées : le territoire face à chacune de ses déclinaisons.
// L'ordre du catalogue est conservé — « ensemble, urbain, rural » se lit dans
// cet ordre, le trier par valeur le rendrait incompréhensible.
export function Groupe({ famille, valeurs, territoire, vent }) {
  const l = famille.membres
    .map((m) => ({ e: m.etiquette, v: valeur(valeurs, m.indicateur_id, territoire, vent) }))
    .filter((p) => p.v != null);

  if (!l.length) return <Vide />;
  const mx = Math.max(...l.map((p) => p.v));
  const d = dec(l.map((p) => p.v));

  return (
    <div>
      {/* L'unité accompagne chaque valeur. Reléguée en légende sous le bloc,
          elle passait pour une ligne orpheline et n'était rattachée à rien. */}
      {l.map((p) => (
        <div key={p.e} className="flex items-center gap-[9px] mb-2">
          <span className="w-[40%] text-[11.5px] text-t2 truncate" title={p.e}>{p.e}</span>
          <div className="flex-1 h-[15px] bg-bg rounded overflow-hidden">
            <i className="block h-full rounded"
               style={{ width: `${((100 * p.v) / mx).toFixed(1)}%`, background: "#001f5f" }} />
          </div>
          <b className="text-[11.5px] tabular-nums min-w-[68px] text-right">
            {nb(p.v, d)}<span className="text-t3 font-semibold"> {famille.unite || ""}</span>
          </b>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ pyramide */

export function Pyramide({ famille, valeurs, territoire }) {
  const tranches = famille.membres
    .map((m) => {
      const series = valeurs?.[m.indicateur_id] || {};
      return {
        e: m.etiquette.replace(" ans", ""),
        h: (series["Masculin"] || {})[String(territoire)] ?? null,
        f: (series["Féminin"] || {})[String(territoire)] ?? null,
      };
    })
    .filter((x) => x.h != null || x.f != null);

  if (!tranches.length)
    return <p className="text-[11.5px] text-t3">Ventilation par sexe non disponible.</p>;

  // Le catalogue rend les tranches dans l'ordre alphabétique : « 5-9 ans »
  // arrive alors après « 45-49 ans ». On retrie sur le nombre de tête, sans
  // quoi la pyramide serait un empilement dans le désordre.
  const rang = (x) => {
    const n = parseInt(x.e, 10);
    return Number.isNaN(n) ? 999 : n;
  };
  tranches.sort((a, b) => rang(b) - rang(a));

  const mx = Math.max(...tranches.flatMap((x) => [x.h || 0, x.f || 0]));
  const L = 520, hL = 15, H = tranches.length * hL + 22, cx = L / 2, demi = (L - 96) / 2;

  // La carte de la pyramide occupe deux colonnes, sinon seize tranches ne
  // tiennent pas. Mais un SVG étiré sur toute cette largeur grossit tout d'un
  // facteur deux : on borne sa largeur et on le centre, les proportions
  // restent celles prévues.
  return (
    <svg viewBox={`0 0 ${L} ${H}`} className="w-full max-w-[640px] mx-auto block">
      {tranches.map((x, i) => {
        const y = i * hL;
        const wh = (demi * (x.h || 0)) / mx;
        const wf = (demi * (x.f || 0)) / mx;
        return (
          <g key={x.e}>
            <rect x={cx - 48 - wh} y={y + 2} width={wh} height={hL - 4} fill="#2563eb" rx="2">
              <title>{`Hommes ${x.e} : ${nb(x.h)} %`}</title>
            </rect>
            <rect x={cx + 48} y={y + 2} width={wf} height={hL - 4} fill="#e0665a" rx="2">
              <title>{`Femmes ${x.e} : ${nb(x.f)} %`}</title>
            </rect>
            <text x={cx} y={y + 11} textAnchor="middle" fontSize="9.5" fill="#64748b">{x.e}</text>
          </g>
        );
      })}
      <text x={cx - 56} y={H - 4} textAnchor="end" fontSize="10" fontWeight="700" fill="#2563eb">Hommes</text>
      <text x={cx + 56} y={H - 4} fontSize="10" fontWeight="700" fill="#e0665a">Femmes</text>
    </svg>
  );
}

/* ------------------------------------------------------------------ aiguillage */

const Vide = () => <p className="text-[11.5px] text-t3">Aucune valeur.</p>;

export function Graphique(props) {
  switch (props.famille.forme) {
    case "anneau":   return <Anneau {...props} />;
    case "empile":   return <Empile {...props} />;
    case "pyramide": return <Pyramide {...props} />;
    case "groupe":   return <Groupe {...props} />;
    default:         return <Barres {...props} />;
  }
}
