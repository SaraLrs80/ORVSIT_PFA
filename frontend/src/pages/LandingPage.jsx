// Page d'accueil (publique).
// Elle assemble toutes les sections, et gère l'ouverture de la modale
// « Demander un accès » (état partagé, transmis aux boutons des sections).

import { useState } from "react";
import LandingNavbar from "../components/landing/LandingNavbar";
import LandingHero from "../components/landing/LandingHero";
import LandingStats from "../components/landing/LandingStats";
import MissionSection from "../components/landing/MissionSection";
import PlateformeSection from "../components/landing/PlateformeSection";
import AxesSection from "../components/landing/AxesSection";
import CtaSection from "../components/landing/CtaSection";
import LandingFooter from "../components/landing/LandingFooter";
import DemandeAccesModal from "../components/landing/DemandeAccesModal";

export default function LandingPage() {
  // Un seul état pour toute la page : la modale est-elle ouverte ?
  const [modaleOuverte, setModaleOuverte] = useState(false);
  const ouvrir = () => setModaleOuverte(true);

  return (
    <div className="min-h-screen scroll-smooth">
      {/* Les trois endroits qui déclenchent l'ouverture reçoivent la même fonction */}
      <LandingNavbar onDemander={ouvrir} />
      <LandingHero onDemander={ouvrir} />
      <LandingStats />
      <MissionSection />
      <PlateformeSection />
      <AxesSection />
      <CtaSection onDemander={ouvrir} />
      <LandingFooter />

      {/* La modale, rendue une seule fois, contrôlée par l'état ci-dessus */}
      <DemandeAccesModal
        open={modaleOuverte}
        onClose={() => setModaleOuverte(false)}
      />
    </div>
  );
}
