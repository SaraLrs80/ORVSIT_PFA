// Bouton d'export réutilisable.
//
// Il ne connaît rien aux données : la page lui fournit une fonction qui, au
// moment du clic, construit les colonnes et les lignes. Cette construction est
// donc toujours faite sur l'état courant de la page — filtres et sélection
// compris — et non sur un instantané figé au premier rendu.

import { Download } from "lucide-react";
import { telechargerCSV, nomDeFichier } from "../utils/export";
import { signaler } from "../api/journal";

/**
 * Props :
 *   - nom      : nom du fichier, sans extension ni date
 *   - donnees  : () => ({ colonnes, lignes, entete }) — appelée au clic
 *   - libelle  : texte du bouton
 *   - sombre   : true si posé sur un fond foncé
 */
export default function BoutonExport({ nom, donnees, libelle = "Exporter", sombre = false }) {
  function exporter() {
    const { colonnes, lignes, entete } = donnees() || {};
    if (!colonnes?.length || !lignes?.length) return;
    telechargerCSV(nomDeFichier(nom), colonnes, lignes, entete);
    signaler("export", `csv · ${nom}`);   // après le succès seulement
  }

  const style = sombre
    ? "bg-white/10 border-white/20 text-white hover:bg-white/15"
    : "bg-surface border-line text-t2 hover:text-navy hover:border-navy-3";

  return (
    <button type="button" onClick={exporter} title="Télécharger au format CSV"
      className={`inline-flex items-center gap-1.5 border rounded-lg px-3 py-1.5
                  text-[11.5px] font-semibold transition-colors ${style}`}>
      <Download size={13} />
      {libelle}
    </button>
  );
}
