// Page « mot de passe oublié » : on saisit son e-mail, on reçoit (par e-mail) un lien.
// Le backend renvoie toujours le même message, qu'on affiche tel quel.

import { useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../api/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState(""); // message de confirmation renvoyé par l'API
  const [enCours, setEnCours] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setEnCours(true);
    try {
      const data = await forgotPassword(email);
      setMessage(data.message); // "Si un compte existe pour cet e-mail, un lien a été envoyé."
    } catch {
      // Même en cas d'erreur réseau, on reste discret.
      setMessage("Si un compte existe pour cet e-mail, un lien a été envoyé.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="w-full max-w-md">
        <div className="bg-surface border border-line rounded-2xl shadow-[0_10px_30px_rgba(16,37,66,0.10)] p-8">
          <div className="text-center mb-6">
            <img src="/logo-orvsit.png" alt="ORVSIT" className="h-14 w-auto mx-auto mb-4" />
            <h1 className="text-2xl font-extrabold text-navy">Mot de passe oublié</h1>
            <p className="text-sm text-t2 mt-1">
              Entrez votre e-mail : nous vous enverrons un lien de réinitialisation.
            </p>
          </div>

          {/* Si un message existe, on l'affiche à la place du formulaire */}
          {message ? (
            <div className="rounded-xl bg-teal-soft border border-teal/30 text-teal px-4 py-3 text-sm text-center">
              {message}
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-t2 mb-1.5">
                  Adresse e-mail
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="nom@organisation.ma"
                  className="w-full px-4 py-3 rounded-xl border border-line bg-bg focus:bg-surface focus:border-blue focus:outline-none focus:ring-4 focus:ring-blue-soft transition"
                />
              </div>
              <button
                type="submit"
                disabled={enCours}
                className="w-full py-3 rounded-xl font-semibold text-navy bg-gradient-to-br from-gold to-gold-2 shadow-[0_8px_18px_rgba(245,166,35,0.32)] hover:brightness-95 transition disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {enCours ? "Envoi…" : "Envoyer le lien"}
              </button>
            </form>
          )}
        </div>

        <p className="text-center mt-4">
          <Link to="/login" className="text-sm text-t3 hover:text-navy transition-colors">
            ← Retour à la connexion
          </Link>
        </p>
      </div>
    </div>
  );
}
