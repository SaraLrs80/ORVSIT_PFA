// Carte réutilisable : une icône dans un carré coloré, un titre, un texte.
// Les valeurs entre { } (Icon, iconClass, title, text) sont les « props » :
// des paramètres qu'on passe au composant pour l'afficher différemment à chaque fois.
//
// Icon est un composant d'icône (venant de lucide-react) qu'on affiche via <Icon />.

export default function FeatureCard({ Icon, iconClass, title, text }) {
  return (
    <div className="h-full bg-surface border border-line rounded-2xl p-6 shadow-[0_6px_22px_rgba(16,37,66,0.06)] hover:shadow-[0_12px_34px_rgba(16,37,66,0.12)] hover:-translate-y-1 transition-all duration-300">
      {/* Carré d'icône coloré. iconClass contient les couleurs (fond + icône). */}
      <div
        className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${iconClass}`}
      >
        <Icon size={24} />
      </div>
      <h3 className="text-lg font-bold text-navy mb-1.5">{title}</h3>
      <p className="text-[15px] text-t2 leading-relaxed">{text}</p>
    </div>
  );
}
