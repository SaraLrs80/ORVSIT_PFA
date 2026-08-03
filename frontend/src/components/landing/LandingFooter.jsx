// Pied de page complet, en trois colonnes :
//  - la marque (logo + courte description)
//  - la navigation (mêmes ancres que la barre du haut)
//  - le contact (rattachement institutionnel)
// Puis une barre de copyright en bas.
//
// NB : l'adresse e-mail est un exemple à remplacer par le vrai contact de l'ORVSIT.

import { Link } from "react-router-dom";
import { Mail, MapPin } from "lucide-react";

export default function LandingFooter() {
  return (
    <footer className="bg-surface border-t border-line">
      {/* Partie haute : 3 colonnes */}
      <div className="max-w-6xl mx-auto grid gap-10 md:grid-cols-3 px-6 md:px-10 py-12">
        {/* Colonne 1 — Marque */}
        <div>
          <img
            src="/logo-orvsit.png"
            alt="ORVSIT"
            className="h-14 w-auto mb-4"
          />
          <p className="text-sm text-t2 leading-relaxed max-w-xs">
            Observatoire Régional de Veille Stratégique et d'Intelligence
            Territoriale du Conseil régional de Tanger-Tétouan-Al Hoceïma.
          </p>
        </div>

        {/* Colonne 2 — Navigation */}
        <div>
          <h4 className="text-sm font-bold text-navy mb-4">Navigation</h4>
          <ul className="space-y-2.5 text-sm text-t2">
            <li>
              <a href="#mission" className="hover:text-navy transition-colors">
                Mission
              </a>
            </li>
            <li>
              <a href="#plateforme" className="hover:text-navy transition-colors">
                La plateforme
              </a>
            </li>
            <li>
              <a href="#axes" className="hover:text-navy transition-colors">
                Axes d'analyse
              </a>
            </li>
            <li>
              <Link to="/login" className="hover:text-navy transition-colors">
                Se connecter
              </Link>
            </li>
          </ul>
        </div>

        {/* Colonne 3 — Contact */}
        <div>
          <h4 className="text-sm font-bold text-navy mb-4">Contact</h4>
          <ul className="space-y-3 text-sm text-t2">
            <li className="flex items-start gap-2.5">
              <MapPin size={17} className="text-gold-2 shrink-0 mt-0.5" />
              <span>
                Conseil régional Tanger-Tétouan-Al Hoceïma
                <br />
                Tanger, Maroc
              </span>
            </li>
            <li className="flex items-center gap-2.5">
              <Mail size={17} className="text-gold-2 shrink-0" />
              <span>contact@orvsit.ma</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Barre de copyright */}
      <div className="border-t border-line py-5 px-6 text-center">
        <p className="text-xs text-t3">
          © 2026 ORVSIT — Conseil régional Tanger-Tétouan-Al Hoceïma. Tous droits
          réservés.
        </p>
      </div>
    </footer>
  );
}
