// Ossature (« shell ») de l'espace connecté, fidèle à la maquette :
//   - une barre latérale navy repliable (logo, navigation, utilisateur + déconnexion)
//   - une barre supérieure (burger pour replier, titre, badge du rôle)
//   - une zone de contenu (children) où chaque page place son contenu.
//
// Props :
//   - title    : le titre affiché dans la topbar
//   - active   : la clé de l'entrée de menu active
//   - children : le contenu de la page

import { useEffect, useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import {
  Menu, LogOut, ChevronRight,
  LayoutDashboard, ArrowLeftRight, FileText, LineChart, Map,
  Inbox, Users, Activity,
} from "lucide-react";
import { getMe, logout } from "../api/auth";
import { getThemes } from "../api/explorer";

// Groupe « Consultation » (écrans analystes/décideurs).
// to = null -> pas encore développé, affiché avec la mention « bientôt ».
//
// « Explorer » porte des sous-entrées : un thème par ligne. Pourquoi ce choix
// plutôt qu'une entrée par thème au premier niveau — Santé, Éducation,
// Démographie… — ou qu'un sélecteur caché dans la page :
//   - une entrée par thème ferait passer le menu de 5 à 11 lignes et mettrait
//     sur le même plan « Comparer », qui est une fonction, et « Santé », qui
//     est un domaine. Ce ne sont pas des choses de même nature ;
//   - un sélecteur à l'intérieur de la page rendrait les thèmes invisibles
//     depuis la navigation : personne ne cherche ce qu'il ne voit pas.
// Le repli garde la hiérarchie lisible et chaque thème garde son adresse.
const NAV_CONSULT = [
  { key: "overview", label: "Vue d'ensemble", Icon: LayoutDashboard, to: "/dashboard" },
  { key: "comparer", label: "Comparer", Icon: ArrowLeftRight, to: "/dashboard/comparer" },
  { key: "fiche", label: "Fiche territoriale", Icon: FileText, to: "/dashboard/fiche" },
  { key: "explorer", label: "Explorer", Icon: LineChart, to: "/dashboard/explorer", pliable: true },
  { key: "carte", label: "Cartographie", Icon: Map, to: null },
];

// Groupe « Administration » (réservé aux administrateurs).
const NAV_ADMIN = [
  { key: "demandes", label: "Demandes d'accès", Icon: Inbox, to: "/admin" },
  { key: "utilisateurs", label: "Utilisateurs", Icon: Users, to: "/admin/utilisateurs" },
  { key: "supervision", label: "Supervision", Icon: Activity, to: "/admin/supervision" },
];

export default function DashboardLayout({ title, active = "overview", children }) {
  const navigate = useNavigate();
  const emplacement = useLocation();
  const [replie, setReplie] = useState(false);
  const [user, setUser] = useState(null);
  const [themes, setThemes] = useState([]);
  // Le sous-menu s'ouvre de lui-même quand on est déjà dans Explorer : arriver
  // sur une page dont l'entrée de menu est repliée est déroutant.
  const [explorerOuvert, setExplorerOuvert] = useState(active === "explorer");

  useEffect(() => {
    getMe().then(setUser).catch(() => {});
    // Les thèmes viennent du backend : le menu se remplit tout seul le jour où
    // un thème est déclaré, sans qu'on revienne éditer ce fichier.
    getThemes().then(setThemes).catch(() => {});
  }, []);

  useEffect(() => {
    if (active === "explorer") setExplorerOuvert(true);
  }, [active]);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const initiales = user
    ? user.nom_complet.split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase()
    : "…";

  // Affiche une entrée de menu (Link si `to`, sinon bloc « bientôt »).
  function itemJsx({ key, label, Icon, to, pliable }) {
    const estActif = key === active;
    const classe = `relative flex items-center gap-3 pl-4 pr-3 py-2.5 rounded-xl text-[13.5px]
                    font-medium transition-colors ${
      estActif ? "bg-white/12 text-white" : "text-white/65 hover:bg-white/6 hover:text-white"
    } ${to ? "" : "opacity-55"}`;

    const contenu = (
      <>
        {/* Repère actif : un liseré doré collé au bord, plus net qu'un dégradé
            qui délavait la couleur du texte par-dessus. */}
        {estActif && <span className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r-full bg-gold" />}
        <Icon size={18} className={`shrink-0 ${estActif ? "text-gold" : ""}`} />
        {!replie && <span className="flex-1 truncate">{label}</span>}
        {!replie && !to && (
          <span className="text-[9px] bg-white/10 text-white/55 px-1.5 py-0.5 rounded">bientôt</span>
        )}
        {!replie && pliable && to && (
          <ChevronRight size={14}
            className={`shrink-0 opacity-55 transition-transform ${explorerOuvert ? "rotate-90" : ""}`}
            onClick={(e) => { e.preventDefault(); setExplorerOuvert((o) => !o); }} />
        )}
      </>
    );

    const entree = to
      ? <Link key={key} to={to} className={classe}>{contenu}</Link>
      : <div key={key} className={classe}>{contenu}</div>;

    if (!pliable || replie || !explorerOuvert || !themes.length) return entree;

    return (
      <div key={key}>
        {entree}
        {/* Sous-entrées : le trait vertical rattache visuellement les thèmes à
            leur parent, sinon la liste semble flotter au même niveau. */}
        <div className="ml-[26px] pl-3 border-l border-white/12 flex flex-col gap-0.5 mt-0.5 mb-1">
          {themes.map((t) => {
            const cible = `/dashboard/explorer/${t.cle}`;
            const actifTheme = emplacement.pathname === cible;
            return (
              <Link key={t.cle} to={cible}
                className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[12.5px]
                            transition-colors ${
                  actifTheme ? "text-white font-semibold bg-white/10"
                             : "text-white/55 hover:text-white hover:bg-white/5"}`}>
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                  actifTheme ? "bg-gold" : "bg-white/25"}`} />
                <span className="flex-1 truncate">{t.nom}</span>
                <span className="text-[10px] text-white/35">{t.angles}</span>
              </Link>
            );
          })}
        </div>
      </div>
    );
  }

  // Affiche un groupe (titre + entrées).
  function groupeJsx(titre, items) {
    return (
      <>
        {!replie && (
          <div className="text-[10px] uppercase tracking-[0.12em] text-white/35 font-bold px-4 mt-5 mb-1.5">
            {titre}
          </div>
        )}
        {items.map(itemJsx)}
      </>
    );
  }

  const estAdmin = user?.role === "administrateur";

  return (
    <div className="min-h-screen bg-bg">
      {/* ---------- BARRE LATÉRALE ---------- */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-30 flex flex-col p-4 text-white bg-gradient-to-b from-navy via-navy-3 to-navy transition-all duration-300 ${
          replie ? "w-20" : "w-64"
        }`}
      >
        {/* Logo */}
        <div className="mb-4">
          {replie ? (
            <div className="w-12 h-12 rounded-xl bg-white flex items-center justify-center mx-auto">
              <img src="/logo-orvsit.png" alt="ORVSIT" className="max-w-[80%] max-h-[80%] object-contain" />
            </div>
          ) : (
            <>
              {/* Le grand aplat blanc écrasait le reste de la colonne : on le
                  réduit à une carte compacte, le menu redevient le sujet. */}
              <div className="bg-white rounded-2xl px-3 py-2.5 flex items-center justify-center">
                <img src="/logo-orvsit.png" alt="ORVSIT" className="h-9 w-auto object-contain" />
              </div>
              <div className="text-[10px] text-white/45 text-center mt-2 tracking-wide">
                Veille territoriale TTA
              </div>
            </>
          )}
        </div>

        {/* Navigation (défilable si besoin) */}
        {/* La barre de défilement native apparaissait en plein milieu de la
            colonne navy et cassait la lecture. On la masque : le contenu reste
            défilable à la molette et au clavier. */}
        <nav className="flex flex-col gap-0.5 flex-1 overflow-y-auto pr-0.5
                        [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {groupeJsx("Consultation", NAV_CONSULT)}
          {estAdmin && groupeJsx("Administration", NAV_ADMIN)}
        </nav>

        {/* Utilisateur + déconnexion */}
        <div className="border-t border-white/10 pt-3 mt-3">
          <div className="flex items-center gap-3 px-1.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue to-navy-3 flex items-center justify-center text-xs font-bold shrink-0">
              {initiales}
            </div>
            {!replie && user && (
              <div className="leading-tight text-sm">
                <div className="font-semibold">{user.nom_complet}</div>
                <div className="text-[10px] text-white/50">{user.role}</div>
              </div>
            )}
          </div>
          <button
            onClick={handleLogout}
            className="mt-2 w-full flex items-center gap-3 pl-4 pr-3 py-2.5 rounded-xl text-[13.5px]
                       font-medium text-white/60 hover:bg-white/8 hover:text-white transition-colors"
          >
            <LogOut size={18} className="shrink-0" />
            {!replie && <span>Déconnexion</span>}
          </button>
        </div>
      </aside>

      {/* ---------- ZONE PRINCIPALE ---------- */}
      <div className={`transition-all duration-300 ${replie ? "ml-20" : "ml-64"}`}>
        <header className="sticky top-0 z-20 h-16 bg-white/80 backdrop-blur-md border-b border-line flex items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setReplie((r) => !r)}
              className="w-9 h-9 rounded-xl flex items-center justify-center text-t2 hover:bg-bg hover:text-navy transition-colors"
              aria-label="Replier / déplier le menu"
            >
              <Menu size={20} />
            </button>
            <h1 className="font-bold text-navy">{title}</h1>
          </div>

          <div className="flex items-center gap-2.5 bg-surface border border-line rounded-full pl-2 pr-3 py-1.5">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-gold to-gold-2 flex items-center justify-center text-navy text-xs font-bold">
              {initiales}
            </div>
            {user && (
              <div className="text-xs leading-tight">
                <div className="font-semibold text-navy">{user.nom_complet}</div>
                <div className="text-t2 text-[10px]">{user.role}</div>
              </div>
            )}
          </div>
        </header>

        {/* max-w-6xl bridait la page à 1152 px : sur un écran large, la carte
            et son panneau se retrouvaient à l'étroit alors qu'il restait de la
            place. On laisse respirer, avec une borne haute pour éviter les
            lignes de texte interminables. */}
        <main className="p-6 max-w-[1600px] mx-auto">{children}</main>
      </div>
    </div>
  );
}
