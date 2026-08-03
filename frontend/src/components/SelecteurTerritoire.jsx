// Sélecteur de territoire — remplace le <select> natif du navigateur.
//
// Pourquoi ne pas garder un <select> : son apparence est imposée par le système
// d'exploitation, on ne peut y mettre ni icône, ni hiérarchie lisible, ni champ
// de recherche. Or la région compte 146 communes : sans recherche, le choix
// devient vite pénible.
//
// Props :
//   - valeur      : identifiant sélectionné (ou "" pour l'option neutre)
//   - onChange    : (identifiant) => void
//   - options     : [{ id, nom, groupe?, detail? }]
//   - optionVide  : libellé de l'entrée neutre en tête de liste (facultatif)
//   - placeholder : texte affiché quand rien n'est sélectionné
//   - Icone       : icône lucide affichée dans le bouton
//   - sombre      : true si le sélecteur est posé sur un fond foncé
//   - libelleRecherche / libelleVide : textes du champ de recherche et du cas
//                 « aucun résultat ». Paramétrables parce que ce sélecteur ne
//                 sert plus qu'aux territoires : la page Explorer s'en sert
//                 aussi pour choisir un indicateur.
//   - largeurMenu : classe de largeur minimale du menu déroulant. Les noms
//                 d'indicateurs sont longs (« Habitants par médecin dentiste
//                 (public + privé) ») et seraient tronqués dans 240 pixels.

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Search, Check } from "lucide-react";

// Compare deux textes sans tenir compte des accents ni de la casse :
// taper « tetouan » doit trouver « Tétouan ».
function normaliser(texte) {
  return (texte || "")
    // NFD sépare la lettre de son accent ; on retire ensuite les signes
    // diacritiques (plage Unicode 0300-036F) pour comparer « e » et « é ».
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().trim();
}

export default function SelecteurTerritoire({
  valeur,
  onChange,
  options = [],
  optionVide = null,
  placeholder = "Choisir…",
  Icone = null,
  sombre = false,
  libelleRecherche = "Rechercher un territoire…",
  libelleVide = "Aucun territoire ne correspond.",
  largeurMenu = "min-w-[240px]",
}) {
  const [ouvert, setOuvert] = useState(false);
  const [recherche, setRecherche] = useState("");
  const boite = useRef(null);
  const champ = useRef(null);

  // Fermeture au clic extérieur et à la touche Échap : deux comportements que
  // l'utilisateur attend d'un menu, et que le <select> natif offrait seul.
  useEffect(() => {
    if (!ouvert) return;
    function auClic(e) {
      if (boite.current && !boite.current.contains(e.target)) setOuvert(false);
    }
    function auClavier(e) {
      if (e.key === "Escape") setOuvert(false);
    }
    document.addEventListener("mousedown", auClic);
    document.addEventListener("keydown", auClavier);
    champ.current?.focus();
    return () => {
      document.removeEventListener("mousedown", auClic);
      document.removeEventListener("keydown", auClavier);
    };
  }, [ouvert]);

  const selection = options.find((o) => String(o.id) === String(valeur));

  const filtrees = useMemo(() => {
    const q = normaliser(recherche);
    if (!q) return options;
    return options.filter((o) =>
      normaliser(o.nom).includes(q) || normaliser(o.groupe).includes(q));
  }, [options, recherche]);

  // Regroupement par province quand l'information est fournie.
  const groupes = useMemo(() => {
    const m = new Map();
    filtrees.forEach((o) => {
      const g = o.groupe || "";
      if (!m.has(g)) m.set(g, []);
      m.get(g).push(o);
    });
    return [...m.entries()];
  }, [filtrees]);

  function choisir(id) {
    onChange(id);
    setOuvert(false);
    setRecherche("");
  }

  const styleBouton = sombre
    ? "bg-white/10 border-white/20 text-white hover:bg-white/15"
    : "bg-surface border-line text-navy hover:border-navy-3";

  return (
    <div className="relative" ref={boite}>
      <button type="button" onClick={() => setOuvert((o) => !o)}
        className={`w-full flex items-center gap-2.5 border rounded-xl px-3.5 py-2.5
                    text-[13px] font-semibold transition-colors ${styleBouton}`}>
        {Icone && <Icone size={15} className="shrink-0 opacity-70" />}
        <span className="flex-1 text-left truncate">
          {selection ? selection.nom : (valeur === "" && optionVide ? optionVide : placeholder)}
        </span>
        <ChevronDown size={16}
          className={`shrink-0 opacity-60 transition-transform ${ouvert ? "rotate-180" : ""}`} />
      </button>

      {ouvert && (
        <div className={`absolute z-40 mt-1.5 w-full ${largeurMenu} bg-surface border border-line
                        rounded-xl shadow-xl overflow-hidden`}>
          {options.length > 8 && (
            <div className="flex items-center gap-2 px-3 py-2.5 border-b border-line">
              <Search size={14} className="text-t3 shrink-0" />
              <input ref={champ} value={recherche} onChange={(e) => setRecherche(e.target.value)}
                placeholder={libelleRecherche}
                className="w-full text-[12.5px] outline-none bg-transparent text-t1
                           placeholder:text-t3" />
            </div>
          )}

          <div className="max-h-72 overflow-y-auto py-1">
            {optionVide && (
              <button type="button" onClick={() => choisir("")}
                className={`w-full flex items-center gap-2 px-3.5 py-2 text-[12.5px] text-left
                            hover:bg-bg transition-colors ${
                  valeur === "" ? "text-navy font-bold" : "text-t2"}`}>
                <span className="w-3.5 shrink-0">
                  {valeur === "" && <Check size={13} className="text-navy" />}
                </span>
                {optionVide}
              </button>
            )}

            {groupes.map(([groupe, liste]) => (
              <div key={groupe || "_"}>
                {groupe && (
                  <div className="px-3.5 pt-2.5 pb-1 text-[10px] font-bold uppercase
                                  tracking-wider text-t3">
                    {groupe}
                  </div>
                )}
                {liste.map((o) => {
                  const actif = String(o.id) === String(valeur);
                  return (
                    <button key={o.id} type="button" onClick={() => choisir(o.id)}
                      className={`w-full flex items-center gap-2 px-3.5 py-2 text-[12.5px]
                                  text-left hover:bg-bg transition-colors ${
                        actif ? "text-navy font-bold bg-blue-soft" : "text-t1"}`}>
                      <span className="w-3.5 shrink-0">
                        {actif && <Check size={13} className="text-navy" />}
                      </span>
                      <span className="flex-1 truncate">{o.nom}</span>
                      {o.detail && (
                        <span className="text-[10.5px] text-t3 shrink-0">{o.detail}</span>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}

            {!filtrees.length && (
              <div className="px-3.5 py-6 text-center text-[12px] text-t3">
                {libelleVide}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
