// Fenêtre modale du formulaire public « Demander un accès ».
// Props :
//   - open    : booléen, la modale s'affiche seulement si true
//   - onClose : fonction à appeler pour fermer la modale
//
// Concepts :
//   - une modale = un calque en position fixe couvrant l'écran (l'overlay sombre),
//     avec une carte centrée par-dessus.
//   - clic sur l'overlay = fermer ; clic sur la carte = stopPropagation() pour NE PAS fermer.

import { useState } from "react";
import { X } from "lucide-react";
import { creerDemande } from "../../api/demandes";

// L'application ne connaît que deux rôles : « administrateur » et « utilisateur ».
// Le rôle d'administrateur ne se demande pas, il s'attribue ; toute demande
// d'accès porte donc le seul profil demandable. Plus de liste déroulante à un
// seul choix : le champ a disparu du formulaire.
const PROFIL_DEMANDE = "utilisateur";

const champClasses =
  "w-full px-4 py-3 rounded-xl border border-line bg-bg focus:bg-surface focus:border-blue focus:outline-none focus:ring-4 focus:ring-blue-soft transition";

export default function DemandeAccesModal({ open, onClose }) {
  const [nomComplet, setNomComplet] = useState("");
  const [email, setEmail] = useState("");
  const [organisation, setOrganisation] = useState("");
  const [motif, setMotif] = useState("");
  const [erreur, setErreur] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [succes, setSucces] = useState(false);

  // Si la modale est fermée, on n'affiche rien du tout.
  if (!open) return null;

  async function handleSubmit(e) {
    e.preventDefault();
    setErreur("");
    setEnCours(true);
    try {
      await creerDemande({
        nom_complet: nomComplet,
        email: email,
        organisation: organisation || null, // vide -> null (champ facultatif)
        profil_souhaite: PROFIL_DEMANDE,
        motif: motif || null,
      });
      setSucces(true);
    } catch {
      setErreur("Une erreur est survenue. Veuillez réessayer.");
    } finally {
      setEnCours(false);
    }
  }

  // Ferme la modale ET réinitialise le formulaire pour la prochaine ouverture.
  function fermer() {
    setSucces(false);
    setErreur("");
    setNomComplet("");
    setEmail("");
    setOrganisation("");
    setMotif("");
    onClose();
  }

  return (
    // Overlay : couvre tout l'écran. Clic dessus = fermer.
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-navy/40 backdrop-blur-sm"
      onClick={fermer}
    >
      {/* La carte. stopPropagation empêche que le clic "traverse" jusqu'à l'overlay. */}
      <div
        className="w-full max-w-lg bg-surface rounded-2xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-1">
          <h2 className="text-xl font-extrabold text-navy">Demander un accès</h2>
          <button
            onClick={fermer}
            className="text-t3 hover:text-navy transition-colors"
            aria-label="Fermer"
          >
            <X size={22} />
          </button>
        </div>

        {succes ? (
          // Vue de confirmation après envoi
          <div className="py-8 text-center">
            <p className="text-navy font-semibold mb-2">Demande envoyée.</p>
            <p className="text-sm text-t2">
              Un administrateur de l'ORVSIT examinera votre demande et vous
              contactera par e-mail.
            </p>
            <button
              onClick={fermer}
              className="mt-6 px-6 py-3 rounded-xl bg-navy text-white font-semibold hover:bg-navy-2 transition-colors"
            >
              Fermer
            </button>
          </div>
        ) : (
          <>
            <p className="text-sm text-t2 mb-5">
              Remplissez ce formulaire : un administrateur examinera votre demande
              et créera votre compte.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              {erreur && (
                <div className="rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3">
                  {erreur}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-t2 mb-1.5">
                  Nom complet
                </label>
                <input
                  value={nomComplet}
                  onChange={(e) => setNomComplet(e.target.value)}
                  required
                  placeholder="Prénom Nom"
                  className={champClasses}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-t2 mb-1.5">
                  Adresse e-mail professionnelle
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="nom@organisation.ma"
                  className={champClasses}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-t2 mb-1.5">
                  Organisation / structure
                </label>
                <input
                  value={organisation}
                  onChange={(e) => setOrganisation(e.target.value)}
                  placeholder="Conseil régional, commune, université…"
                  className={champClasses}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-t2 mb-1.5">
                  Motif de la demande
                </label>
                <textarea
                  value={motif}
                  onChange={(e) => setMotif(e.target.value)}
                  rows={3}
                  placeholder="Décrivez en quelques mots l'usage prévu de la plateforme…"
                  className={champClasses}
                />
              </div>

              <button
                type="submit"
                disabled={enCours}
                className="w-full py-3 rounded-xl font-semibold text-navy bg-gradient-to-br from-gold to-gold-2 shadow-[0_8px_18px_rgba(245,166,35,0.32)] hover:brightness-95 transition disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {enCours ? "Envoi…" : "Envoyer la demande"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
