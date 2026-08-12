// Ossature de l'espace connecté — barre de navigation supérieure ORVSIT.
//
// Pourquoi une barre supérieure plutôt que la colonne latérale d'origine :
// l'application a vocation à rejoindre le site de l'observatoire, et le site
// navigue par le haut. Reprendre sa barre — mêmes tailles, même graisse, même
// soulignement doré de 3 px sur l'entrée active — évite qu'on sente la couture
// entre les deux au moment de l'intégration.
//
// La signature du composant est inchangée : title, active, children. Les huit
// écrans existants héritent donc de la nouvelle navigation sans être modifiés.
// C'est tout l'intérêt d'avoir gardé l'ossature dans un seul fichier.

import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { ChevronDown, LogOut, Menu, X } from "lucide-react";
import { getMe, logout } from "../api/auth";
import { getThemes } from "../api/explorer";
import BoutonAssistant from "./BoutonAssistant";

// « Cartographie » a été retirée : la carte n'est pas un écran à part, elle est
// un moyen de lecture présent dans la fiche, dans Comparer et dans Explorer.
// Lui garder une entrée de menu promettait une page qui n'aurait rien apporté
// de plus, et laissait un « bientôt » inutile dans une barre qui doit être tenue.
//
// to = null → écran non encore développé, affiché avec la mention « bientôt ».
const NAV_CONSULT = [
  { key: "overview", label: "Vue d'ensemble", to: "/dashboard" },
  { key: "comparer", label: "Comparer", to: "/dashboard/comparer" },
  { key: "fiche", label: "Fiche territoriale", to: "/dashboard/fiche" },
  { key: "explorer", label: "Explorer", to: "/dashboard/explorer", deroulant: "themes" },
  { key: "assistant", label: "Assistant", to: "/dashboard/assistant" },
];

const NAV_ADMIN = [
  { key: "demandes", label: "Demandes d'accès", to: "/admin" },
  { key: "utilisateurs", label: "Utilisateurs", to: "/admin/utilisateurs" },
  { key: "supervision", label: "Supervision", to: "/admin/supervision" },
];

const CLES_ADMIN = NAV_ADMIN.map((e) => e.key);

/**
 * Props :
 *   - title      surtitre de l'écran
 *   - active     clé de l'entrée de navigation à souligner
 *   - territoire nom du territoire consulté, s'il y en a un. Il n'est utilisé
 *                que par la pastille de l'assistant, pour pré-remplir la
 *                question. Les écrans qui n'en ont pas ne le passent pas.
 */
export default function DashboardLayout({ title, active = "overview",
                                          territoire = null, children }) {
  const navigate = useNavigate();
  const emplacement = useLocation();
  const [user, setUser] = useState(null);
  const [themes, setThemes] = useState([]);
  const [ouvert, setOuvert] = useState(null);     // "themes" | "admin" | "user" | null
  const [menuMobile, setMenuMobile] = useState(false);
  const barre = useRef(null);

  useEffect(() => {
    getMe().then(setUser).catch(() => {});
    // Les thèmes viennent du backend : le menu se remplit tout seul le jour où
    // un thème est déclaré, sans qu'on revienne éditer ce fichier.
    getThemes().then(setThemes).catch(() => {});
  }, []);

  useEffect(() => { if (title) document.title = `${title} — ORVSIT`; }, [title]);

  // Un menu déroulant qui survit au changement de page donne l'impression que
  // le clic n'a pas abouti : on ferme à chaque navigation.
  useEffect(() => { setOuvert(null); setMenuMobile(false); }, [emplacement.pathname]);

  // Fermeture au clic extérieur et à la touche Échap — sans quoi le seul moyen
  // de refermer serait de rouvrir, ce qui est un piège classique.
  useEffect(() => {
    function dehors(e) { if (barre.current && !barre.current.contains(e.target)) setOuvert(null); }
    function echap(e) { if (e.key === "Escape") setOuvert(null); }
    document.addEventListener("mousedown", dehors);
    document.addEventListener("keydown", echap);
    return () => {
      document.removeEventListener("mousedown", dehors);
      document.removeEventListener("keydown", echap);
    };
  }, []);

  function handleLogout() { logout(); navigate("/login"); }

  const initiales = user
    ? user.nom_complet.split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase()
    : "…";
  const estAdmin = user?.role === "administrateur";
  const adminActif = CLES_ADMIN.includes(active);

  /* --------------------------------------------------------------- une entrée */
  // 13 px, graisse 700, et pour l'entrée active un liseré doré de 3 px posé
  // sous le texte : ce sont les valeurs exactes de la barre du site.
  function Entree({ e }) {
    const actif = e.key === active;
    const classe = `relative inline-flex items-center gap-1 text-[13px] font-bold py-[26px]
                    transition-colors border-b-[3px] ${
      actif ? "text-navy border-gold" : "text-t1 border-transparent hover:text-navy"
    } ${e.to ? "" : "opacity-45 cursor-default"}`;

    if (e.deroulant) {
      const deploye = ouvert === e.deroulant;
      return (
        <div className="relative">
          <Link to={e.to} className={classe}
            onClick={(ev) => { if (themes.length) { ev.preventDefault(); setOuvert(deploye ? null : e.deroulant); } }}>
            {e.label}
            <ChevronDown size={13} className={`transition-transform ${deploye ? "rotate-180" : ""}`} />
          </Link>
          {deploye && themes.length > 0 && (
            <div className="absolute left-0 top-full mt-1 w-64 bg-white border border-line rounded-2xl
                            ombre-orvsit-f p-2 z-50">
              <Link to="/dashboard/explorer"
                className="block px-3 py-2 rounded-xl text-[12.5px] font-bold text-navy hover:bg-bg">
                Tous les thèmes
              </Link>
              <div className="h-px bg-line-2 my-1.5" />
              {themes.map((t) => (
                <Link key={t.cle} to={`/dashboard/explorer/${t.cle}`}
                  className="flex items-center gap-2 px-3 py-2 rounded-xl text-[12.5px] text-t2
                             hover:bg-bg hover:text-navy transition-colors">
                  <span className="flex-1 truncate">{t.nom}</span>
                  <span className="text-[10px] text-t3">{t.angles}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      );
    }

    return e.to
      ? <Link to={e.to} className={classe}>{e.label}</Link>
      : <span className={classe}>
          {e.label}
          <span className="text-[9px] bg-bg text-t3 px-1.5 py-0.5 rounded-full ml-1">bientôt</span>
        </span>;
  }

  return (
    <div className="min-h-screen bg-bg">
      {/* ═══════════════════════════ BARRE SUPÉRIEURE ═══════════════════════ */}
      <header ref={barre}
        className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-line">
        <div className="max-w-[1600px] mx-auto px-6 flex items-center gap-8">

          {/* Marque */}
          <Link to="/dashboard" className="flex items-center gap-2.5 py-3 shrink-0">
            <img src="/logo-orvsit.png" alt="" className="h-9 w-auto object-contain" />
            <span className="leading-none">
              <span className="block text-[17px] font-extrabold text-navy tracking-[-0.03em]">ORVSIT</span>
              <span className="block text-[8.5px] font-bold tracking-[0.14em] text-t2 mt-0.5">
                INTELLIGENCE TERRITORIALE
              </span>
            </span>
          </Link>

          {/* Entrées — masquées sous 1024 px, où elles passent dans le tiroir */}
          <nav className="hidden lg:flex items-center gap-6 flex-1">
            {NAV_CONSULT.map((e) => <Entree key={e.key} e={e} />)}

            {estAdmin && (
              <div className="relative">
                <button onClick={() => setOuvert(ouvert === "admin" ? null : "admin")}
                  className={`inline-flex items-center gap-1 text-[13px] font-bold py-[26px]
                              border-b-[3px] transition-colors ${
                    adminActif ? "text-navy border-gold" : "text-t1 border-transparent hover:text-navy"}`}>
                  Administration
                  <ChevronDown size={13} className={`transition-transform ${ouvert === "admin" ? "rotate-180" : ""}`} />
                </button>
                {ouvert === "admin" && (
                  <div className="absolute left-0 top-full mt-1 w-56 bg-white border border-line
                                  rounded-2xl ombre-orvsit-f p-2 z-50">
                    {NAV_ADMIN.map((e) => (
                      <Link key={e.key} to={e.to}
                        className={`block px-3 py-2 rounded-xl text-[12.5px] transition-colors ${
                          e.key === active ? "bg-bg text-navy font-bold"
                                           : "text-t2 hover:bg-bg hover:text-navy"}`}>
                        {e.label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            )}
          </nav>

          {/* Utilisateur */}
          <div className="ml-auto lg:ml-0 flex items-center gap-2">
            <div className="relative">
              <button onClick={() => setOuvert(ouvert === "user" ? null : "user")}
                className="flex items-center gap-2.5 bg-bg border border-line rounded-full
                           pl-1.5 pr-3 py-1.5 hover:border-navy-3 transition-colors">
                <span className="w-7 h-7 rounded-full bg-gradient-to-br from-gold to-gold-2
                                 grid place-items-center text-navy text-[11px] font-extrabold">
                  {initiales}
                </span>
                {user && (
                  <span className="hidden sm:block text-left leading-tight">
                    <span className="block text-[11.5px] font-bold text-navy">{user.nom_complet}</span>
                    <span className="block text-[9.5px] text-t2">{user.role}</span>
                  </span>
                )}
                <ChevronDown size={12} className="text-t3" />
              </button>
              {ouvert === "user" && (
                <div className="absolute right-0 top-full mt-1 w-52 bg-white border border-line
                                rounded-2xl ombre-orvsit-f p-2 z-50">
                  <button onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-[12.5px]
                               text-t2 hover:bg-bg hover:text-navy transition-colors">
                    <LogOut size={14} /> Déconnexion
                  </button>
                </div>
              )}
            </div>

            <button onClick={() => setMenuMobile((m) => !m)}
              className="lg:hidden w-9 h-9 rounded-xl grid place-items-center text-t2 hover:bg-bg"
              aria-label="Menu">
              {menuMobile ? <X size={19} /> : <Menu size={19} />}
            </button>
          </div>
        </div>

        {/* Tiroir des petits écrans */}
        {menuMobile && (
          <div className="lg:hidden border-t border-line px-6 py-3 flex flex-col gap-0.5">
            {[...NAV_CONSULT, ...(estAdmin ? NAV_ADMIN : [])].map((e) =>
              e.to ? (
                <Link key={e.key} to={e.to}
                  className={`px-3 py-2.5 rounded-xl text-[13px] font-bold transition-colors ${
                    e.key === active ? "bg-bg text-navy" : "text-t2 hover:bg-bg"}`}>
                  {e.label}
                </Link>
              ) : (
                <span key={e.key} className="px-3 py-2.5 text-[13px] font-bold text-t3 opacity-60">
                  {e.label} · bientôt
                </span>
              )
            )}
          </div>
        )}
      </header>

      {/* ═══════════════════════════════ CONTENU ════════════════════════════ */}
      {/* Le titre passe en surtitre, comme sur le site où « Le pouls du
          territoire » annonce le grand titre. Il situe l'écran sans lui voler
          sa première ligne. */}
      <main className="max-w-[1600px] mx-auto px-6 py-6">
        {title && (
          <div className="text-[10.5px] font-extrabold uppercase tracking-[0.14em] text-t3 mb-3">
            {title}
          </div>
        )}
        {children}
      </main>

      {/* La pastille d'accès à l'assistant. Elle vit ici plutôt que dans chaque
          écran : les dix pages en héritent sans être modifiées, comme elles ont
          hérité de la barre supérieure. Elle ne s'affiche pas sur la page de
          l'assistant lui-même, où elle ne mènerait nulle part. */}
      {active !== "assistant" && <BoutonAssistant territoire={territoire} />}
    </div>
  );
}
