// « client » = un axios pré-configuré, réutilisé par tous nos appels API.
//
// axios est la librairie qui envoie les requêtes HTTP (comme fetch, en plus pratique).
// On crée UNE instance avec l'adresse de base de l'API, comme ça on écrit ensuite
// client.post("/auth/login") au lieu de répéter "http://localhost:8000" partout.

import axios from "axios";

const client = axios.create({
  baseURL: "http://localhost:8000", // l'adresse de ton API FastAPI
});

// --- Intercepteur de requête ---
// Un « intercepteur » est une fonction exécutée AVANT chaque requête sortante.
// Ici, on attrape le jeton stocké dans le navigateur et on l'ajoute automatiquement
// dans l'en-tête Authorization. Résultat : toutes nos requêtes protégées
// (comme /auth/me) enverront le jeton SANS qu'on ait à y penser à chaque fois.
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default client;
