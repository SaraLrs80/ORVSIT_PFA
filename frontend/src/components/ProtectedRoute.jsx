// « Gardien » de route : enveloppe une page pour la réserver aux utilisateurs
// connectés (et, si on précise `requiredRole`, à un rôle donné).
//
// Comment ça marche :
//  - au montage, on demande au backend "qui suis-je ?" (getMe) pour VÉRIFIER que
//    le jeton est encore valide — on ne se contente pas de regarder s'il existe ;
//  - tant qu'on attend la réponse, on affiche "Chargement…" (évite un clignotement
//    de la page protégée avant la vérification) ;
//  - selon le résultat : on affiche la page (ok) ou on redirige vers /login (refusé).

import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { getToken, getMe } from "../api/auth";

export default function ProtectedRoute({ children, requiredRole }) {
  // Trois états possibles : on part de "chargement".
  const [statut, setStatut] = useState("chargement"); // "chargement" | "ok" | "refuse"

  // useEffect = exécute du code APRÈS l'affichage du composant (ici : la vérification).
  useEffect(() => {
    async function verifier() {
      // Pas de jeton du tout -> inutile d'appeler l'API.
      if (!getToken()) {
        setStatut("refuse");
        return;
      }
      try {
        const utilisateur = await getMe(); // le backend valide le jeton et renvoie le profil
        // Connecté mais mauvais rôle -> refusé.
        if (requiredRole && utilisateur.role !== requiredRole) {
          setStatut("refuse");
        } else {
          setStatut("ok");
        }
      } catch {
        // 401 : jeton invalide ou expiré.
        setStatut("refuse");
      }
    }
    verifier();
  }, [requiredRole]);

  if (statut === "chargement") {
    return (
      <div className="min-h-screen flex items-center justify-center text-t2">
        Chargement…
      </div>
    );
  }

  if (statut === "refuse") {
    // <Navigate> = redirection déclarative. `replace` évite d'empiler /admin dans
    // l'historique (sinon le bouton "précédent" te y ramènerait en boucle).
    return <Navigate to="/login" replace />;
  }

  // statut === "ok" : on affiche la page protégée.
  return children;
}
