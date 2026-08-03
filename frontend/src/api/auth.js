// Fonctions d'authentification, regroupées au même endroit.
// Elles utilisent le « client » axios (qui connaît déjà l'adresse de l'API
// et attache le jeton automatiquement).

import client from "./client";

// Se connecter : envoie email + mot de passe à POST /auth/login.
// En cas de succès, on RANGE le jeton dans le navigateur (localStorage) pour
// qu'il survive à un rafraîchissement de page.
export async function login(email, motDePasse) {
  // Le backend attend un champ nommé "mot_de_passe" (comme dans ton LoginRequest).
  const { data } = await client.post("/auth/login", {
    email: email,
    mot_de_passe: motDePasse,
  });
  localStorage.setItem("token", data.access_token);
  return data;
}

// Récupérer le profil de l'utilisateur connecté (GET /auth/me).
// Le jeton est ajouté tout seul par l'intercepteur du client.
export async function getMe() {
  const { data } = await client.get("/auth/me");
  return data;
}

// Se déconnecter : on efface simplement le jeton.
export function logout() {
  localStorage.removeItem("token");
}

// Petit utilitaire pour savoir si un jeton est présent.
export function getToken() {
  return localStorage.getItem("token");
}

// Demander un lien de réinitialisation (mot de passe oublié).
export async function forgotPassword(email) {
  const { data } = await client.post("/auth/forgot-password", { email });
  return data;
}

// Appliquer un nouveau mot de passe à partir du jeton reçu dans le lien.
export async function resetPassword(token, nouveauMotDePasse) {
  const { data } = await client.post("/auth/reset-password", {
    token: token,
    nouveau_mot_de_passe: nouveauMotDePasse, // nom attendu par le backend
  });
  return data;
}
