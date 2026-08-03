// Appels liés à la fiche territoriale.
import client from "./client";

// Arborescence province -> communes, pour les sélecteurs.
export async function getArborescence() {
  const response = await client.get("/fiche");
  return response.data;
}

// Toutes les données d'un territoire (province ou commune).
export async function getFiche(territoireId) {
  const response = await client.get(`/fiche/${territoireId}`);
  return response.data;
}
