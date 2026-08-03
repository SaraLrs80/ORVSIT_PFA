// Page de connexion : formulaire email + mot de passe.
// Au clic sur « Se connecter » : on appelle l'API, on stocke le jeton, on récupère
// le profil, puis on redirige selon le rôle.

import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { login, getMe } from "../api/auth";

export default function LoginPage() {
  const navigate = useNavigate(); // permet de rediriger vers une autre page en JS

  // --- L'état du formulaire ---
  // useState crée une "variable réactive" : quand elle change, React ré-affiche.
  // [valeur, fonctionPourLaChanger] = useState(valeurDeDépart)
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState("");     // message d'erreur à afficher
  const [enCours, setEnCours] = useState(false); // true pendant l'appel à l'API

  // Fonction appelée quand on soumet le formulaire
  async function handleSubmit(e) {
    e.preventDefault();   // empêche le rechargement de page par défaut du navigateur
    setErreur("");        // on efface une éventuelle erreur précédente
    setEnCours(true);     // on passe en "chargement" (désactive le bouton)

    try {
      await login(email, motDePasse);   // 1) envoie les identifiants, stocke le jeton
      await getMe();                    // 2) vérifie que le profil est accessible

      // 3) tout le monde arrive sur la Vue d'ensemble (les admins accèdent
      //    à l'espace d'administration via la barre latérale).
      navigate("/dashboard");
    } catch (err) {
      // Si le backend répond 401 (mauvais identifiants), on tombe ici.
      setErreur("Email ou mot de passe incorrect.");
    } finally {
      setEnCours(false); // dans tous les cas, on sort du "chargement"
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="w-full max-w-md">
        {/* La carte de connexion */}
        <div className="bg-surface border border-line rounded-2xl shadow-[0_10px_30px_rgba(16,37,66,0.10)] p-8">
          {/* Logo + titre */}
          <div className="text-center mb-8">
            <img
              src="/logo-orvsit.png"
              alt="ORVSIT"
              className="h-14 w-auto mx-auto mb-4"
            />
            <h1 className="text-2xl font-extrabold text-navy">Connexion</h1>
            <p className="text-sm text-t2 mt-1">
              Accédez à votre tableau de bord ORVSIT
            </p>
          </div>

          {/* Message d'erreur : affiché SEULEMENT si `erreur` n'est pas vide */}
          {erreur && (
            <div className="mb-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3">
              {erreur}
            </div>
          )}

          {/* Le formulaire ; onSubmit se déclenche au clic sur le bouton (type submit) */}
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

            <div>
              <label className="block text-sm font-medium text-t2 mb-1.5">
                Mot de passe
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

            <div className="text-right -mt-1">
              <Link
                to="/forgot-password"
                className="text-xs text-blue hover:underline"
              >
                Mot de passe oublié ?
              </Link>
            </div>

            <button
              type="submit"
              disabled={enCours}
              className="w-full py-3 rounded-xl font-semibold text-navy bg-gradient-to-br from-gold to-gold-2 shadow-[0_8px_18px_rgba(245,166,35,0.32)] hover:brightness-95 transition disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {enCours ? "Connexion…" : "Se connecter"}
            </button>
          </form>
        </div>

        {/* Liens sous la carte */}
        <p className="text-center mt-6 text-sm text-t2">
          Pas encore de compte ?{" "}
          <Link to="/#acces" className="text-gold-2 font-semibold hover:underline">
            Demander un accès
          </Link>
        </p>
        <p className="text-center mt-2">
          <Link to="/" className="text-sm text-t3 hover:text-navy transition-colors">
            ← Retour à l'accueil
          </Link>
        </p>
      </div>
    </div>
  );
}
