// Barre de navigation de la landing page.
// - Logo à gauche
// - Menu au centre (liens qui font défiler vers les sections de la page)
// - Deux boutons à droite : « Demander l'accès » et « Se connecter »

import { Link } from "react-router-dom";

export default function LandingNavbar({ onDemander }) {
  return (
    <nav className="sticky top-0 z-50 flex items-center justify-between px-6 md:px-10 py-1.5 bg-white/85 backdrop-blur-md border-b border-line">
      {/* Logo à gauche */}
      <div className="flex items-center">
        <img
          src="/logo-orvsit.png"
          alt="ORVSIT — Observatoire Régional de Veille Stratégique et d'Intelligence Territoriale"
          className="h-[72px] w-auto"
        />
      </div>

      {/* Menu au centre (masqué sur petit écran pour rester lisible) */}
      <div className="hidden md:flex items-center gap-9">
        <a
          href="#mission"
          className="text-[15px] font-medium text-t2 hover:text-navy transition-colors"
        >
          Mission
        </a>
        <a
          href="#plateforme"
          className="text-[15px] font-medium text-t2 hover:text-navy transition-colors"
        >
          La plateforme
        </a>
        <a
          href="#axes"
          className="text-[15px] font-medium text-t2 hover:text-navy transition-colors"
        >
          Axes d'analyse
        </a>
      </div>

      {/* Boutons à droite */}
      <div className="flex items-center gap-3">
        {/* Bouton « fantôme » (contour seulement) — ouvre la modale de demande d'accès */}
        <button
          type="button"
          onClick={onDemander}
          className="px-6 py-3 rounded-xl text-[15px] font-semibold text-navy border-[1.5px] border-line hover:border-navy transition-colors"
        >
          Demander l'accès
        </button>

        {/* Bouton plein (dégradé or) — mène à la page de connexion */}
        <Link
          to="/login"
          className="px-6 py-3 rounded-xl text-[15px] font-semibold text-navy bg-gradient-to-br from-gold to-gold-2 shadow-[0_8px_18px_rgba(245,166,35,0.32)] hover:brightness-95 transition"
        >
          Se connecter
        </Link>
      </div>
    </nav>
  );
}
