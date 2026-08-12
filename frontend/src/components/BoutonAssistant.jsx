// La pastille d'accès à l'assistant, présente sur tous les écrans connectés.
//
// POURQUOI UNE PASTILLE QUI OUVRE LA PAGE, ET NON UN PANNEAU DE DISCUSSION
// Une réponse de l'assistant met douze à dix-huit secondes et peut énumérer
// huit territoires classés ou sept indicateurs disponibles, chacun suivi de sa
// source. Un panneau étroit rendrait ces réponses illisibles, et l'attente y
// paraît plus longue que sur une page dédiée. La pastille est donc une porte,
// pas une seconde interface : rien n'est maintenu en double.
//
// CE QU'ELLE FAIT DE PLUS QU'UN LIEN
// Elle emporte le contexte. Depuis la fiche de Tétouan, la saisie de
// l'assistant arrive pré-remplie avec « à Tétouan » : il ne reste qu'à nommer
// l'indicateur. C'est le seul travail que l'utilisateur n'a pas à refaire.

import { useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";

/**
 * Props :
 *   - territoire : nom du territoire consulté, s'il y en a un. Il sert à
 *                  pré-remplir la question, jamais à la poser.
 */
export default function BoutonAssistant({ territoire = null }) {
  const navigate = useNavigate();

  function ouvrir() {
    // Le contexte passe par l'état de navigation plutôt que par l'adresse :
    // un nom de territoire dans une URL serait à échapper, et l'historique du
    // navigateur se remplirait de questions à moitié écrites.
    navigate("/dashboard/assistant",
             territoire ? { state: { amorce: `à ${territoire}` } } : undefined);
  }

  return (
    <button
      onClick={ouvrir}
      title={territoire
        ? `Poser une question sur ${territoire}`
        : "Poser une question à l'assistant"}
      className="ecran-seul fixed bottom-6 right-6 z-50 inline-flex items-center
                 gap-2 rounded-full bg-navy text-white pl-4 pr-5 py-3
                 shadow-[0_10px_30px_rgba(0,31,95,0.28)]
                 hover:bg-navy-2 hover:-translate-y-0.5
                 transition-all duration-200">
      <Sparkles size={16} />
      <span className="text-[12.5px] font-bold hidden sm:inline">
        {territoire ? `Demander · ${territoire}` : "Assistant"}
      </span>
    </button>
  );
}
