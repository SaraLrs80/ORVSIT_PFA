// Section d'appel à l'action (en bas de page), en BANDE PLEINE LARGEUR :
// le fond navy occupe toute la largeur de l'écran, seul le texte est centré.
// id="acces" = cible des boutons « Demander l'accès / un accès ».
// Plus tard, ce bouton ouvrira une fenêtre pop-up (modale) de demande d'accès.

import { UserPlus } from "lucide-react";

export default function CtaSection({ onDemander }) {
  return (
    <section
      id="acces"
      className="bg-gradient-to-br from-navy via-navy-3 to-navy text-white px-6 md:px-10 py-16 scroll-mt-24"
    >
      <div className="max-w-3xl mx-auto text-center">
        <h2 className="text-2xl md:text-3xl font-extrabold mb-3">
          Un accès réservé aux partenaires de l'Observatoire
        </h2>
        <p className="text-white/70 max-w-xl mx-auto mb-8 leading-relaxed">
          Analystes, décideurs régionaux et partenaires institutionnels : demandez
          votre accès à la plateforme.
        </p>
        <button
          type="button"
          onClick={onDemander}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-navy bg-gradient-to-br from-gold to-gold-2 shadow-[0_8px_18px_rgba(245,166,35,0.32)] hover:brightness-95 transition"
        >
          <UserPlus size={17} />
          Demander un accès
        </button>
      </div>
    </section>
  );
}
