// Section « Les axes d'analyse » : les 6 dimensions, en cartes horizontales
// (icône à gauche, titre + texte à droite). Apparition au défilement via <Reveal>.

import {
  Users,
  HeartHandshake,
  Building2,
  Route,
  Briefcase,
  Leaf,
} from "lucide-react";
import Reveal from "../Reveal";

const axes = [
  {
    Icon: Users,
    title: "Démographie",
    text: "Densité, croissance, urbain/rural, structure par âge.",
  },
  {
    Icon: HeartHandshake,
    title: "Dimension sociale",
    text: "Pauvreté, chômage, éducation, accès à la santé.",
  },
  {
    Icon: Building2,
    title: "Équipements & services",
    text: "Eau, électricité, écoles, couverture sanitaire.",
  },
  {
    Icon: Route,
    title: "Accessibilité & mobilité",
    text: "Desserte routière, enclavement, accès aux centres.",
  },
  {
    Icon: Briefcase,
    title: "Économie & emploi",
    text: "Tissu productif, emploi, dynamique d'investissement.",
  },
  {
    Icon: Leaf,
    title: "Environnement & résilience",
    text: "Stress hydrique, risques naturels, vulnérabilité climatique.",
  },
];

export default function AxesSection() {
  return (
    <section
      id="axes"
      className="px-6 md:px-10 py-14 max-w-6xl mx-auto scroll-mt-24"
    >
      <Reveal className="text-center max-w-2xl mx-auto mb-10">
        <div className="text-sm font-bold uppercase tracking-wider text-gold-2 mb-3">
          6 dimensions
        </div>
        <h2 className="text-4xl font-extrabold text-navy">Les axes d'analyse</h2>
      </Reveal>

      <div className="grid md:grid-cols-2 gap-5">
        {axes.map(({ Icon, title, text }, i) => (
          <Reveal key={title} delay={i * 100} className="h-full">
            <div className="h-full flex items-start gap-4 bg-surface border border-line rounded-2xl p-5 shadow-[0_6px_22px_rgba(16,37,66,0.06)] hover:shadow-[0_12px_34px_rgba(16,37,66,0.12)] hover:-translate-y-1 transition-all duration-300">
              <div className="w-11 h-11 rounded-xl bg-navy/5 text-navy flex items-center justify-center shrink-0">
                <Icon size={22} />
              </div>
              <div>
                <h4 className="text-lg font-bold text-navy mb-1">{title}</h4>
                <p className="text-[15px] text-t2 leading-relaxed">{text}</p>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
