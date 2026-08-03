// Le « hero » : le grand bandeau navy en haut de la page.
// - un petit badge (eyebrow) avec une icône
// - le titre, avec le mot « décider » mis en avant en doré
// - un sous-titre
// - deux boutons d'appel à l'action
// Les deux <div> « halo » sont purement décoratifs (taches de lumière floues qui flottent).

import { Link } from "react-router-dom";
import { Radio, LogIn } from "lucide-react";

export default function LandingHero({ onDemander }) {
  return (
    <header className="relative overflow-hidden bg-gradient-to-br from-navy via-navy-3 to-navy text-white px-6 md:px-10 pt-20 pb-28 text-center">
      {/* Halos décoratifs (position absolue = posés par-dessus le fond) */}
      <div
        className="pointer-events-none absolute -top-16 left-[8%] w-72 h-72 rounded-full blur-2xl animate-float"
        style={{
          background: "radial-gradient(circle, rgba(245,166,35,0.22), transparent 70%)",
        }}
      />
      <div
        className="pointer-events-none absolute -bottom-10 right-[10%] w-60 h-60 rounded-full blur-2xl animate-float"
        style={{
          background: "radial-gradient(circle, rgba(45,108,223,0.28), transparent 70%)",
          animationDelay: "1.5s",
        }}
      />

      {/* Badge (eyebrow) */}
      <span className="relative inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-white/80 bg-white/10 border border-white/15 px-4 py-2 rounded-full">
        <Radio size={15} />
        Observatoire régional · Tanger-Tétouan-Al Hoceïma
      </span>

      {/* Titre principal — « décider » en doré grâce à <em class="text-gold"> */}
      <h1 className="relative mx-auto max-w-3xl mt-6 text-4xl md:text-5xl font-extrabold leading-tight tracking-tight">
        Anticiper, comprendre, <em className="not-italic text-gold">décider</em> pour
        un territoire plus équitable
      </h1>

      {/* Sous-titre */}
      <p className="relative mx-auto max-w-xl mt-5 text-base text-white/70 leading-relaxed">
        Une plateforme de veille stratégique qui mesure et visualise les disparités
        territoriales de la région TTA pour éclairer la décision publique.
      </p>

      {/* Boutons d'appel à l'action */}
      <div className="relative mt-8 flex flex-wrap gap-3.5 justify-center">
        <Link
          to="/login"
          className="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold text-navy bg-gradient-to-br from-gold to-gold-2 shadow-[0_8px_18px_rgba(245,166,35,0.32)] hover:brightness-95 transition"
        >
          <LogIn size={17} />
          Accéder au tableau de bord
        </Link>
        <button
          type="button"
          onClick={onDemander}
          className="inline-flex items-center px-5 py-3 rounded-xl text-sm font-semibold text-white border-[1.5px] border-white/30 hover:border-white/60 transition-colors"
        >
          Demander un accès
        </button>
      </div>
    </header>
  );
}
