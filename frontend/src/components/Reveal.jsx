// Composant utilitaire : fait APPARAÎTRE son contenu (fondu + léger glissement
// vers le haut) au moment où il entre dans la zone visible de l'écran.
//
// Concepts React utilisés :
//  - useRef   : garde une référence vers l'élément HTML pour l'observer
//  - useState : mémorise si l'élément est déjà visible (true/false)
//  - useEffect: lance l'observation une fois le composant affiché
//  - IntersectionObserver : outil natif du navigateur qui prévient quand
//    un élément apparaît à l'écran.
//
// `delay` permet de décaler l'apparition (utile pour animer des cartes une par une).

import { useEffect, useRef, useState } from "react";

export default function Reveal({ children, className = "", delay = 0 }) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.unobserve(el); // on n'anime qu'une seule fois
        }
      },
      { threshold: 0.15 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      style={{ transitionDelay: `${delay}ms` }}
      className={`transition-all duration-700 ease-out ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
      } ${className}`}
    >
      {children}
    </div>
  );
}
