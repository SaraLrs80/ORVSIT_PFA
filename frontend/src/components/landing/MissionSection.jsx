// Section « Notre mission » : un en-tête + 3 cartes.
// Les données des cartes sont dans le tableau `items`, puis affichées avec .map().
// Chaque bloc est enveloppé dans <Reveal> pour apparaître au défilement.

import { Radar, MapPinned, Lightbulb } from "lucide-react";
import FeatureCard from "./FeatureCard";
import Reveal from "../Reveal";

const items = [
  {
    Icon: Radar,
    iconClass: "bg-gold-soft text-gold-2",
    title: "Veille stratégique",
    text: "Surveiller en continu les dynamiques démographiques, sociales, économiques et environnementales de la région.",
  },
  {
    Icon: MapPinned,
    iconClass: "bg-blue-soft text-blue",
    title: "Intelligence territoriale",
    text: "Mesurer les disparités entre communes et provinces pour cibler les priorités d'action et d'investissement.",
  },
  {
    Icon: Lightbulb,
    iconClass: "bg-teal-soft text-teal",
    title: "Aide à la décision",
    text: "Des tableaux de bord, fiches territoriales et un assistant IA pour appuyer le Conseil régional et les partenaires.",
  },
];

export default function MissionSection() {
  return (
    // id="mission" = cible du lien « Mission » de la barre de navigation
    <section id="mission" className="px-6 md:px-10 py-14 max-w-6xl mx-auto scroll-mt-24">
      {/* En-tête de section */}
      <Reveal className="text-center max-w-2xl mx-auto mb-10">
        <div className="text-sm font-bold uppercase tracking-wider text-gold-2 mb-3">
          Notre mission
        </div>
        <h2 className="text-4xl font-extrabold text-navy mb-4">
          Veiller, analyser, éclairer la décision
        </h2>
        <p className="text-base text-t2 leading-relaxed">
          L'ORVSIT assure une veille stratégique et une intelligence territoriale
          continues : produire des données et analyses fiables pour suivre les
          stratégies régionales, anticiper les risques et renforcer la résilience du
          territoire.
        </p>
      </Reveal>

      {/* Grille de 3 cartes — chacune apparaît avec un léger décalage (delay) */}
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
