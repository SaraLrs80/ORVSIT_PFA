// Fenêtre de confirmation, dans la charte ORVSIT.
//
// Elle remplace window.confirm, qui a trois défauts : son apparence dépend du
// navigateur et du système, elle bloque tout l'onglet, et elle ne permet ni de
// nommer précisément l'action ni d'en signaler la gravité.
//
// Trois principes tenus ici :
//   - le bouton d'action porte le VERBE de ce qu'il fait — « Supprimer » — et
//     non « OK », qui n'engage à rien ;
//   - l'annulation est le geste par défaut : Échap ferme, le clic hors de la
//     carte ferme, et c'est le bouton neutre qui reçoit le focus ;
//   - une action irréversible se signale par la couleur, pas par un point
//     d'exclamation.

import { useEffect, useRef } from "react";
import { AlertTriangle, X } from "lucide-react";

/**
 * Props :
 *   - ouvert     booléen
 *   - titre      la question posée, courte
 *   - detail     ce qui va se passer, en une phrase
 *   - action     texte du bouton d'action (impératif : « Supprimer »)
 *   - danger     true si l'action est irréversible
 *   - onConfirme fonction appelée à la confirmation
 *   - onFerme    fonction appelée à l'annulation
 */
export default function Confirmation({
  ouvert, titre, detail = null, action = "Confirmer", danger = false,
  onConfirme, onFerme,
}) {
  const annuler = useRef(null);

  useEffect(() => {
    if (!ouvert) return;
    annuler.current?.focus();
    const auClavier = (e) => { if (e.key === "Escape") onFerme(); };
    window.addEventListener("keydown", auClavier);
    return () => window.removeEventListener("keydown", auClavier);
  }, [ouvert, onFerme]);

  if (!ouvert) return null;

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center p-4
                 bg-navy/40 backdrop-blur-sm"
      onClick={onFerme}
      role="dialog"
      aria-modal="true">
      <div
        className="w-full max-w-md bg-surface rounded-2xl shadow-2xl p-6"
        onClick={(e) => e.stopPropagation()}>

        <div className="flex items-start gap-3">
          {danger && (
            <span className="mt-0.5 shrink-0 w-9 h-9 rounded-xl bg-coral-soft
                             text-coral flex items-center justify-center">
              <AlertTriangle size={17} />
            </span>
          )}
          <div className="flex-1 min-w-0">
            <h2 className="text-[15px] font-extrabold text-navy leading-snug">
              {titre}
            </h2>
            {detail && (
              <p className="text-[12.5px] text-t2 mt-1.5 leading-relaxed">
                {detail}
              </p>
            )}
          </div>
          <button onClick={onFerme} aria-label="Fermer"
            className="text-t3 hover:text-navy transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button ref={annuler} onClick={onFerme}
            className="px-4 py-2.5 rounded-xl border border-line text-t2
                       text-[12.5px] font-bold hover:text-navy
                       hover:border-navy-3 transition-colors">
            Annuler
          </button>
          <button onClick={onConfirme}
            className={`px-4 py-2.5 rounded-xl text-white text-[12.5px]
                        font-bold transition-colors ${
              danger ? "bg-coral hover:brightness-95"
                     : "bg-navy hover:bg-navy-2"}`}>
            {action}
          </button>
        </div>
      </div>
    </div>
  );
}
