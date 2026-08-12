// Bandeau de chiffres-clés, dans une carte blanche qui « chevauche » le bas du hero
// (grâce à la marge négative -mt-14).
//
// Nouveau concept : au lieu d'écrire 4 fois le même bloc, on met les données dans
// un tableau `stats` et on les parcourt avec .map() pour générer un bloc par entrée.
// C'est la façon standard d'afficher une liste en React.
//
// Chiffres relevés dans le catalogue et le référentiel territorial, avec le
// MÊME filtre que l'application : secteur servi, et disponible à au moins une
// échelle. C'est celui de recherche._lignes, dont l'assistant se sert, et
// celui de la route /overview. Un chiffre public qui contredirait le tableau
// de bord serait relevé au premier coup d'œil.
//
//   146  communes dans referential.dim_territoire — et non 147, depuis que les
//        quatre arrondissements de Tanger ont été fusionnés en une commune
//   224  indicateurs servis : 221 au niveau province, 136 au niveau commune.
//        Le catalogue en compte 342 lignes au total, mais annoncer ce chiffre
//        promettrait des indicateurs que l'application ne sert pas
//     5  secteurs servis : démographie, emploi, éducation, santé,
//        conditions de vie
//
// À revérifier après chaque passe sur le catalogue : c'est la seule page que
// le public — et le jury — atteint sans compte.
const stats = [
  { value: "8", label: "préfectures & provinces" },
  { value: "146", label: "communes couvertes" },
  { value: "5", label: "secteurs couverts" },
  { value: "224", label: "indicateurs servis" },
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
