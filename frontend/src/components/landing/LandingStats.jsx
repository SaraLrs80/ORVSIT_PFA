// Bandeau de chiffres-clés, dans une carte blanche qui « chevauche » le bas du hero
// (grâce à la marge négative -mt-14).
//
// Nouveau concept : au lieu d'écrire 4 fois le même bloc, on met les données dans
// un tableau `stats` et on les parcourt avec .map() pour générer un bloc par entrée.
// C'est la façon standard d'afficher une liste en React.
//
// Chiffres alignés sur ton rapport : 8 préfectures/provinces, 147 communes,
// 6 axes d'analyse, 394 indicateurs catalogués.

const stats = [
  { value: "8", label: "préfectures & provinces" },
  { value: "147", label: "communes couvertes" },
  { value: "6", label: "axes d'analyse" },
  { value: "394", label: "indicateurs" },
];

export default function LandingStats() {
  return (
    <div className="relative z-10 mx-auto -mt-14 max-w-4xl px-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 bg-surface rounded-2xl border border-line shadow-[0_10px_30px_rgba(16,37,66,0.10)] px-6 py-6">
        {stats.map((s) => (
          <div key={s.label} className="text-center">
            <div className="text-2xl md:text-3xl font-extrabold text-navy">
              {s.value}
            </div>
            <div className="text-xs text-t2 mt-1">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
