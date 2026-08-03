// Section « La plateforme » : même structure que Mission (en-tête + 3 cartes),
// on réutilise le même composant FeatureCard avec d'autres données.

import { LayoutDashboard, ArrowLeftRight, FileText } from "lucide-react";
import FeatureCard from "./FeatureCard";
import Reveal from "../Reveal";

const items = [
  {
    Icon: LayoutDashboard,
    iconClass: "bg-violet-soft text-violet",
    title: "Vue d'ensemble",
    text: "Indice de développement territorial, classements et principales disparités de la région TTA.",
  },
  {
    Icon: ArrowLeftRight,
    iconClass: "bg-coral-soft text-coral",
    title: "Comparaison",
    text: "Confrontez plusieurs territoires sur les 6 axes et repérez les écarts à la moyenne régionale.",
  },
  {
    Icon: FileText,
    iconClass: "bg-gold-soft text-gold-2",
    title: "Fiches & cartes",
    text: "Un profil détaillé par territoire et une cartographie des vulnérabilités.",
  },
];

export default function PlateformeSection() {
  return (
    <section
      id="plateforme"
      className="px-6 md:px-10 py-14 max-w-6xl mx-auto scroll-mt-24"
    >
      <Reveal className="text-center max-w-2xl mx-auto mb-10">
        <div className="text-sm font-bold uppercase tracking-wider text-gold-2 mb-3">
          La plateforme
        </div>
        <h2 className="text-4xl font-extrabold text-navy mb-4">
          Tout le territoire, en un coup d'œil
        </h2>
        <p className="text-base text-t2 leading-relaxed">
          Comparez, explorez et décidez à partir d'une base de données territoriale
          consolidée et fiable.
        </p>
      </Reveal>

      <div className="grid md:grid-cols-3 gap-5">
        {items.map((item, i) => (
          <Reveal key={item.title} delay={i * 120} className="h-full">
            <FeatureCard {...item} />
          </Reveal>
        ))}
      </div>
    </section>
  );
}
