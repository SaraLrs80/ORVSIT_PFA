// Page de réinitialisation : l'utilisateur arrive ici via le lien de l'e-mail,
// qui contient le jeton dans l'URL (/reset-password?token=XXXX).
// On lit ce jeton, on demande le nouveau mot de passe (+ confirmation), puis on
// appelle le backend.

import { useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { resetPassword } from "../api/auth";

export default function ResetPasswordPage() {
  // useSearchParams lit les paramètres de l'URL (la partie après le ?).
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token"); // récupère la valeur de ?token=...

  const navigate = useNavigate();

  const [motDePasse, setMotDePasse] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [erreur, setErreur] = useState("");
  const [succes, setSucces] = useState(false);
  const [enCours, setEnCours] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setErreur("");

    // Vérifications côté client AVANT d'appeler l'API
    if (motDePasse.length < 8) {
      setErreur("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }
    if (motDePasse !== confirmation) {
      setErreur("Les deux mots de passe ne correspondent pas.");
      return;
    }

    setEnCours(true);
    try {
      await resetPassword(token, motDePasse);
      setSucces(true);
      // Redirection vers la connexion après 2 secondes
      setTimeout(() => navigate("/login"), 2000);
    } catch {
      setErreur("Lien invalide ou expiré. Refaites une demande.");
    } finally {
      setEnCours(false);
    }
  }

  // Cas où l'utilisateur arrive sans jeton dans l'URL
  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg px-4">
        <div className="text-center">
          <p className="text-t2 mb-3">Lien de réinitialisation invalide.</p>
          <Link to="/forgot-password" className="text-gold-2 font-semibold hover:underline">
            Refaire une demande
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="w-full max-w-md">
        <div className="bg-surface border border-line rounded-2xl shadow-[0_10px_30px_rgba(16,37,66,0.10)] p-8">
          <div className="text-center mb-6">
            <img src="/logo-orvsit.png" alt="ORVSIT" className="h-14 w-auto mx-auto mb-4" />
            <h1 className="text-2xl font-extrabold text-navy">Nouveau mot de passe</h1>
            <p className="text-sm text-t2 mt-1">Choisissez un nouveau mot de passe.</p>
          </div>

          {succes ? (
            <div className="rounded-xl bg-teal-soft border border-teal/30 text-teal px-4 py-3 text-sm text-center">
              Mot de passe réinitialisé. Redirection vers la connexion…
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {erreur && (
                <div className="rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3">
                  {erreur}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-t2 mb-1.5">
                  Nouveau mot de passe
                </label>
                <input
                  type="password"
                  value={motDePasse}
                  onChange={(e) => setMotDePasse(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="w-full px-4 py-3 rounded-xl border border-line bg-bg focus:bg-surface focus:border-blue focus:outline-none focus:ring-4 focus:ring-blue-soft transition"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-t2 mb-1.5">
                  Confirmer le mot de passe
                </label>
                <input
                  type="password"
                  value={confirmation}
                  onChange={(e) => setConfirmation(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="w-full px-4 py-3 rounded-xl border border-line bg-bg focus:bg-surface focus:border-blue focus:outline-none focus:ring-4 focus:ring-blue-soft transition"
                />
              </div>

              <button
                type="submit"
                disabled={enCours}
                className="w-full py-3 rounded-xl font-semibold text-navy bg-gradient-to-br from-gold to-gold-2 shadow-[0_8px_18px_rgba(245,166,35,0.32)] hover:brightness-95 transition disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {enCours ? "Enregistrement…" : "Réinitialiser"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
